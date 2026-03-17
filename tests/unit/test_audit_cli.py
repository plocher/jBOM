"""Unit tests for jbom.cli.audit — argument parsing and exit code behaviour.

These tests invoke the handler directly rather than through subprocess to keep
them fast and independent of the installed entry point.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from jbom.cli.audit import _build_project_couplet_rows, handle_audit
from jbom.cli.main import create_parser
from jbom.services.audit_service import AuditReport, AuditRow, CheckType, Severity


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------


def test_audit_command_registered_in_parser() -> None:
    parser = create_parser()
    # --help raises SystemExit(0); that confirms 'audit' is a known subcommand.
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["audit", "--help"])
    assert exc_info.value.code == 0


def test_audit_command_registered() -> None:
    """audit subcommand should be parseable without error."""
    parser = create_parser()
    # Using a non-existent path is fine for parser-level validation
    args = parser.parse_args(["audit", "."])
    assert args.command == "audit"
    assert args.inputs == ["."]


def test_audit_defaults_to_current_directory_input() -> None:
    parser = create_parser()
    args = parser.parse_args(["audit"])
    assert args.command == "audit"
    assert args.inputs == ["."]


def test_audit_strict_flag_parsed() -> None:
    parser = create_parser()
    args = parser.parse_args(["audit", ".", "--strict"])
    assert args.strict is True


def test_audit_inventory_flag_parsed() -> None:
    parser = create_parser()
    args = parser.parse_args(["audit", ".", "--inventory", "cat.csv"])
    assert args.inventory == Path("cat.csv")


def test_audit_requirements_flag_parsed() -> None:
    parser = create_parser()
    args = parser.parse_args(["audit", "cat.csv", "--requirements", "req.csv"])
    assert args.requirements == Path("req.csv")


def test_audit_output_flag_parsed() -> None:
    parser = create_parser()
    args = parser.parse_args(["audit", ".", "-o", "report.csv"])
    assert args.output == "report.csv"


# ---------------------------------------------------------------------------
# Helpers to build a mock AuditReport and a fake args namespace
# ---------------------------------------------------------------------------


def _make_args(**kwargs):
    """Build a minimal argparse.Namespace for handle_audit."""
    import argparse

    defaults = {
        "inputs": ["."],
        "inventory": None,
        "requirements": None,
        "output": None,
        "strict": False,
        "verbose": 0,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_audit_verbose_flag_parsed() -> None:
    parser = create_parser()
    args = parser.parse_args(["audit", ".", "-vv"])
    assert args.verbose == 2


def _mock_report(*, error_count=0, warn_count=0, info_count=0, rows=None):
    report = AuditReport(
        rows=rows or [],
        error_count=error_count,
        warn_count=warn_count,
        info_count=info_count,
    )
    return report


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------


def test_audit_csv_input_triggers_inventory_mode(tmp_path: Path) -> None:
    """All-CSV inputs should call audit_inventory, not audit_project."""
    cat = tmp_path / "catalog.csv"
    cat.write_text("RowType,IPN,Category\nITEM,R001,RES\n", encoding="utf-8")

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_inventory.return_value = _mock_report()

        args = _make_args(inputs=[str(cat)])
        handle_audit(args)

        instance.audit_inventory.assert_called_once()
        instance.audit_project.assert_not_called()


def test_audit_directory_input_triggers_project_mode(tmp_path: Path) -> None:
    """Non-CSV inputs should call audit_project, not audit_inventory."""
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        args = _make_args(inputs=[str(tmp_path)])
        handle_audit(args)

        instance.audit_project.assert_called_once()
        instance.audit_inventory.assert_not_called()


def test_audit_mixed_inputs_treated_as_project_mode(tmp_path: Path) -> None:
    """If any input is not .csv the command must use project mode."""
    csv_file = tmp_path / "catalog.csv"
    csv_file.write_text("RowType,IPN,Category\n", encoding="utf-8")

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        # Mix: one .csv and one directory
        args = _make_args(inputs=[str(tmp_path), str(csv_file)])
        handle_audit(args)

        instance.audit_project.assert_called_once()


# ---------------------------------------------------------------------------
# --requirements in project mode is an error
# ---------------------------------------------------------------------------


def test_requirements_flag_in_project_mode_returns_1(tmp_path: Path) -> None:
    args = _make_args(inputs=[str(tmp_path)], requirements=Path("req.csv"))
    result = handle_audit(args)
    assert result == 1


# ---------------------------------------------------------------------------
# --inventory in inventory mode is an error
# ---------------------------------------------------------------------------


def test_inventory_flag_in_inventory_mode_returns_1(tmp_path: Path) -> None:
    cat = tmp_path / "catalog.csv"
    cat.write_text("RowType,IPN,Category\n", encoding="utf-8")

    args = _make_args(inputs=[str(cat)], inventory=Path("cat.csv"))
    result = handle_audit(args)
    assert result == 1


# ---------------------------------------------------------------------------
# Exit code behaviour
# ---------------------------------------------------------------------------


def test_exit_code_0_when_no_errors(tmp_path: Path) -> None:
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(warn_count=2)

        args = _make_args(inputs=[str(tmp_path)])
        result = handle_audit(args)

    assert result == 0


def test_exit_code_1_when_errors(tmp_path: Path) -> None:
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(error_count=1)

        args = _make_args(inputs=[str(tmp_path)])
        result = handle_audit(args)

    assert result == 1


def test_strict_exit_code_1_when_only_warnings(tmp_path: Path) -> None:
    """With --strict, warnings should raise exit code to 1."""
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(warn_count=3)

        args = _make_args(inputs=[str(tmp_path)], strict=True)
        result = handle_audit(args)

    assert result == 1


def test_strict_exit_code_0_when_no_issues(tmp_path: Path) -> None:
    """With --strict and no issues, exit code should still be 0."""
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        args = _make_args(inputs=[str(tmp_path)], strict=True)
        result = handle_audit(args)

    assert result == 0


# ---------------------------------------------------------------------------
# -o output file writing
# ---------------------------------------------------------------------------


def test_output_file_is_written(tmp_path: Path) -> None:
    report_path = tmp_path / "report.csv"

    error_row = AuditRow(
        check_type=CheckType.QUALITY_ISSUE,
        severity=Severity.ERROR,
        project_path=str(tmp_path),
        ref_des="R1",
        uuid="uuid-r1",
        field="Value",
        description="R1: required field 'Value' is missing",
    )

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(
            error_count=1, rows=[error_row]
        )

        args = _make_args(inputs=[str(tmp_path)], output=report_path)
        handle_audit(args)

    assert report_path.exists(), "Report file should be created at -o path"
    content = report_path.read_text(encoding="utf-8")
    assert "RowType" in content
    assert "MISSING" in content
    assert "R1" in content


def test_output_file_has_all_csv_columns(tmp_path: Path) -> None:
    from jbom.services.audit_service import REPORT_CSV_COLUMNS

    report_path = tmp_path / "report.csv"
    catalog = tmp_path / "catalog.csv"
    catalog.write_text("RowType,IPN,Category\nITEM,R001,RES\n", encoding="utf-8")

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_inventory.return_value = _mock_report()

        args = _make_args(inputs=[str(catalog)], output=report_path)
        handle_audit(args)

    assert report_path.exists()
    with report_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames or []) == set(REPORT_CSV_COLUMNS)


def test_output_to_stdout_contains_csv_header(tmp_path: Path, capsys) -> None:
    """When -o is not specified in project mode, couplet CSV should be written to stdout."""
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        args = _make_args(inputs=[str(tmp_path)])
        handle_audit(args)

    captured = capsys.readouterr()
    assert (
        "RowType" in captured.out
    ), "Project couplet CSV header should appear in stdout"


def test_output_dash_writes_csv_to_stdout_in_project_mode(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        monkeypatch.chdir(tmp_path)
        args = _make_args(inputs=[str(tmp_path)], output="-")
        handle_audit(args)

    captured = capsys.readouterr()
    assert "RowType" in captured.out
    assert not (tmp_path / "-").exists()


def test_output_console_prints_table_in_project_mode(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.ERROR,
            project_path=str(tmp_path),
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Value",
            current_value="",
            suggested_value="",
            description="missing Value",
        )
    ]
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(error_count=1, rows=rows)

        monkeypatch.chdir(tmp_path)
        args = _make_args(inputs=[str(tmp_path)], output="console")
        handle_audit(args)

    captured = capsys.readouterr()
    assert "Audit report (project mode)" in captured.out
    assert "CURRENT" in captured.out
    assert not (tmp_path / "console").exists()


def test_output_console_simplifies_project_path_to_home_directory(
    capsys, monkeypatch
) -> None:
    project_file = (
        Path.home()
        / "Dropbox/KiCad/projects/Signal-ColorLight-Single/SignalMast-ColorLight-SingleHead.kicad_pro"
    )
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.ERROR,
            project_path=str(project_file),
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="missing Wavelength",
        )
    ]
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(error_count=1, rows=rows)

        monkeypatch.chdir(Path.home())
        args = _make_args(inputs=["."], output="console")
        handle_audit(args)

    captured = capsys.readouterr()
    assert "~/" in captured.out
    assert "ColorLight-" in captured.out
    assert "Single" in captured.out
    assert "SignalMast-ColorLight-SingleHead.kicad_pro" not in captured.out


def test_project_summary_counts_only_visible_quality_fields(
    tmp_path: Path, capsys
) -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path=str(tmp_path),
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="Manufacturer",
            current_value="",
            suggested_value="",
            description="D1: best-practice field 'Manufacturer' is missing",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path=str(tmp_path),
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="MFGPN",
            current_value="",
            suggested_value="",
            description="D1: best-practice field 'MFGPN' is missing",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path=str(tmp_path),
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="D1: best-practice field 'Wavelength' is missing",
        ),
    ]

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(warn_count=3, rows=rows)

        args = _make_args(inputs=[str(tmp_path)], output="-")
        handle_audit(args)

    captured = capsys.readouterr()
    assert "Audit complete: 1 info(s)." in captured.err


def test_inventory_output_dash_writes_csv_to_stdout(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    catalog = tmp_path / "catalog.csv"
    catalog.write_text("RowType,IPN,Category\nITEM,R001,RES\n", encoding="utf-8")
    rows = [
        AuditRow(
            check_type=CheckType.COVERAGE_GAP,
            severity=Severity.ERROR,
            catalog_file=str(catalog),
            ipn="R001",
            category="RES",
            description="no match",
        )
    ]
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_inventory.return_value = _mock_report(error_count=1, rows=rows)

        monkeypatch.chdir(tmp_path)
        args = _make_args(inputs=[str(catalog)], output="-")
        handle_audit(args)

    captured = capsys.readouterr()
    assert "CheckType" in captured.out
    assert "COVERAGE_GAP" in captured.out
    assert not (tmp_path / "-").exists()


def test_inventory_output_console_prints_table(
    tmp_path: Path, capsys, monkeypatch
) -> None:
    catalog = tmp_path / "catalog.csv"
    catalog.write_text("RowType,IPN,Category\nITEM,R001,RES\n", encoding="utf-8")
    rows = [
        AuditRow(
            check_type=CheckType.COVERAGE_GAP,
            severity=Severity.ERROR,
            catalog_file=str(catalog),
            ipn="R001",
            category="RES",
            description="no match",
        )
    ]
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_inventory.return_value = _mock_report(error_count=1, rows=rows)

        monkeypatch.chdir(tmp_path)
        args = _make_args(inputs=[str(catalog)], output="console")
        handle_audit(args)

    captured = capsys.readouterr()
    assert "Audit report (inventory mode)" in captured.out
    assert "COVERAGE_GAP" in captured.out
    assert not (tmp_path / "console").exists()


def test_project_mode_output_is_couplet_rows(tmp_path: Path) -> None:
    report_path = tmp_path / "report.csv"
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path=str(tmp_path),
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Tolerance",
            current_value="",
            suggested_value="e.g. 1%, 5%, 10%",
            description="R1: best-practice field 'Tolerance' is missing",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path=str(tmp_path),
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Power",
            current_value="",
            suggested_value="e.g. 0.1W",
            description="R1: best-practice field 'Power' is missing",
        ),
    ]

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report(warn_count=2, rows=rows)

        args = _make_args(inputs=[str(tmp_path)], output=report_path)
        handle_audit(args)

    with report_path.open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))

    assert len(written) == 2
    assert {r["RowType"] for r in written} == {"CURRENT", "SUGGESTED"}
    current = next(r for r in written if r["RowType"] == "CURRENT")
    suggested = next(r for r in written if r["RowType"] == "SUGGESTED")
    assert current["Notes"] == "R1: heuristics are sufficient"
    assert current["Action"] == ""
    assert suggested["Action"] == "SKIP/SET"
    assert suggested["Notes"] == ""
    assert suggested["Tolerance"] == "MISSING\n(5%)"
    assert suggested["Power"] == "MISSING"


def test_project_mode_suggests_package_and_domain_defaults() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Tolerance",
            current_value="",
            suggested_value="",
            description="R1 missing tolerance",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Power",
            current_value="",
            suggested_value="",
            description="R1 missing power",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="C1",
            uuid="uuid-c1",
            category="CAP",
            field="Voltage",
            current_value="",
            suggested_value="",
            description="C1 missing voltage",
        ),
    ]

    context = {
        ("/proj/example.kicad_pro", "R1", "uuid-r1", "RES"): {
            "Value": "10K",
            "Footprint": "SPCoast:0603-RES",
            "Package": "603",
            "Description": "Resistor",
        },
        ("/proj/example.kicad_pro", "C1", "uuid-c1", "CAP"): {
            "Value": "100nF",
            "Footprint": "SPCoast:0603-CAP",
            "Package": "603",
            "Description": "Capacitor",
        },
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    suggested_rows = [row for row in written if row["RowType"] == "SUGGESTED"]

    r1_suggested = next(row for row in suggested_rows if row["RefDes"] == "R1")
    assert r1_suggested["Tolerance"] == "MISSING\n(5%)"
    assert r1_suggested["Power"] == "MISSING\n(100mW)"

    c1_suggested = next(row for row in suggested_rows if row["RefDes"] == "C1")
    assert c1_suggested["Voltage"] == "MISSING\n(25V)"


def test_project_mode_includes_merge_mismatch_diagnostics_in_notes() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Tolerance",
            current_value="",
            suggested_value="",
            description="R1 missing tolerance",
        ),
        AuditRow(
            check_type=CheckType.MERGE_MISMATCH,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="footprint",
            current_value="s:SCH:0603, p:PCB:0402",
            suggested_value="PCB:0402",
            description="R1 footprint mismatch",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "R1", "uuid-r1", "RES"): {
            "Value": "10K",
            "Footprint": "SCH:0603",
            "Package": "0603",
            "Description": "Resistor",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    current = next(row for row in written if row["RowType"] == "CURRENT")
    assert "Merge mismatch diagnostics:" in current["Notes"]
    assert "footprint (s:SCH:0603, p:PCB:0402)" in current["Notes"]


def test_project_mode_matchability_exact_for_supplier_identifier_and_led_color() -> (
    None
):
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="D1 missing wavelength",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "D1", "uuid-d1", "LED"): {
            "Value": "Red",
            "Footprint": "LED_SMD:LED_0603_1608Metric",
            "Package": "0603",
            "Description": "Status LED",
            "LCSC": "C2286",
        }
    }

    fieldnames, written = _build_project_couplet_rows(
        rows,
        component_context=context,
        supplier_id="lcsc",
    )
    current = next(row for row in written if row["RowType"] == "CURRENT")
    suggested = next(row for row in written if row["RowType"] == "SUGGESTED")
    assert "LCSC" in fieldnames
    assert current["LCSC"] == "C2286"
    assert suggested["LCSC"] == "C2286"
    assert "EMMatchability" not in fieldnames
    assert "EMBasis" not in fieldnames
    assert "SupplierMatchability" not in fieldnames
    assert "SupplierBasis" not in fieldnames
    assert "D1: LCSC part number used" in current["Notes"]
    assert suggested["Action"] == "SKIP/SET"
    assert suggested["Notes"] == ""
    assert suggested["Wavelength"] == "MISSING\n(620-750nm)"
    assert "Debug" not in current


def test_project_mode_no_supplier_pass_does_not_emit_lcsc_specific_note() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="D1 missing wavelength",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "D1", "uuid-d1", "LED"): {
            "Value": "Red",
            "Footprint": "LED_SMD:LED_0603_1608Metric",
            "Package": "0603",
            "Description": "Status LED",
            "LCSC": "C2286",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    current = next(row for row in written if row["RowType"] == "CURRENT")
    assert "LCSC part number used" not in current["Notes"]
    assert current["Notes"] == "D1: heuristics are sufficient"


def test_project_mode_supplier_mouser_does_not_accept_lcsc_anchor() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="D1",
            uuid="uuid-d1",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="D1 missing wavelength",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "D1", "uuid-d1", "LED"): {
            "Value": "Red",
            "Footprint": "LED_SMD:LED_0603_1608Metric",
            "Package": "0603",
            "Description": "Status LED",
            "LCSC": "C2286",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(
        rows,
        component_context=context,
        supplier_id="mouser",
    )
    current = next(row for row in written if row["RowType"] == "CURRENT")
    assert "Supplier anchor missing (need SPN or MPN)" in current["Notes"]
    assert (
        "part number present; uniquely identifies this component"
        not in current["Notes"]
    )


def test_project_mode_matchability_exact_when_current_attrs_meet_matcher_threshold() -> (
    None
):
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Tolerance",
            current_value="",
            suggested_value="",
            description="R1 missing tolerance",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R1",
            uuid="uuid-r1",
            category="RES",
            field="Power",
            current_value="",
            suggested_value="",
            description="R1 missing power",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "R1", "uuid-r1", "RES"): {
            "Value": "10K",
            "Footprint": "Resistor_SMD:R_0603_1608Metric",
            "Package": "0603",
            "Description": "Resistor",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    current = next(row for row in written if row["RowType"] == "CURRENT")
    assert current["Notes"] == "R1: heuristics are sufficient"


def test_project_mode_matchability_heuristic_when_defaults_lift_score() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R2",
            uuid="uuid-r2",
            category="RES",
            field="Tolerance",
            current_value="",
            suggested_value="",
            description="R2 missing tolerance",
        ),
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R2",
            uuid="uuid-r2",
            category="RES",
            field="Power",
            current_value="",
            suggested_value="",
            description="R2 missing power",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "R2", "uuid-r2", "RES"): {
            "Value": "",
            "Footprint": "Resistor_SMD:R_0603_1608Metric",
            "Package": "0603",
            "Description": "Resistor",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    current = next(row for row in written if row["RowType"] == "CURRENT")
    assert current["Notes"] == "R2: heuristics are sufficient"


def test_project_mode_matchability_exact_when_led_color_unknown() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="D2",
            uuid="uuid-d2",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="D2 missing wavelength",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "D2", "uuid-d2", "LED"): {
            "Value": "Pink",
            "Footprint": "LED_SMD:LED_0603_1608Metric",
            "Package": "0603",
            "Description": "Indicator LED",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    current = next(row for row in written if row["RowType"] == "CURRENT")
    suggested = next(row for row in written if row["RowType"] == "SUGGESTED")
    assert current["Notes"] == "D2: heuristics are sufficient"
    assert suggested["Wavelength"] == "MISSING"


def test_project_mode_matchability_needs_clue_when_no_match_clues() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="U1",
            uuid="uuid-u1",
            category="",
            field="Voltage",
            current_value="",
            suggested_value="",
            description="U1 missing voltage",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "U1", "uuid-u1", ""): {
            "Value": "",
            "Footprint": "",
            "Package": "",
            "Description": "Unknown part",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    current = next(row for row in written if row["RowType"] == "CURRENT")
    assert "EM matching needs stronger clues" in current["Notes"]
    assert (
        "For other suppliers, required fields and heuristics should be sufficient"
        in current["Notes"]
    )


def test_project_mode_verbose_includes_debug_column() -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="R2",
            uuid="uuid-r2",
            category="RES",
            field="Tolerance",
            current_value="",
            suggested_value="",
            description="R2 missing tolerance",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "R2", "uuid-r2", "RES"): {
            "Value": "",
            "Footprint": "Resistor_SMD:R_0603_1608Metric",
            "Package": "0603",
            "Description": "Resistor",
        }
    }
    fieldnames, written = _build_project_couplet_rows(
        rows,
        component_context=context,
        verbose_level=1,
    )
    current = next(row for row in written if row["RowType"] == "CURRENT")

    assert "Debug" in fieldnames
    assert "em_debug:" in current["Debug"]
    assert "supplier_debug:" in current["Debug"]


@pytest.mark.parametrize(
    "value, expected_wavelength",
    [
        ("railroad-green", "505-508nm"),
        ("railroad red", "627-635nm"),
        ("railroad-yellow", "589-599nm"),
        ("lunar-white", "400-700nm (cool white, CCT 3250-5600K)"),
    ],
)
def test_project_mode_led_named_color_aliases_map_to_expected_ranges(
    value: str, expected_wavelength: str
) -> None:
    rows = [
        AuditRow(
            check_type=CheckType.QUALITY_ISSUE,
            severity=Severity.WARN,
            project_path="/proj/example.kicad_pro",
            ref_des="D3",
            uuid="uuid-d3",
            category="LED",
            field="Wavelength",
            current_value="",
            suggested_value="",
            description="D3 missing wavelength",
        ),
    ]
    context = {
        ("/proj/example.kicad_pro", "D3", "uuid-d3", "LED"): {
            "Value": value,
            "Footprint": "LED_SMD:LED_0603_1608Metric",
            "Package": "0603",
            "Description": "Signal LED",
        }
    }

    _fieldnames, written = _build_project_couplet_rows(rows, component_context=context)
    suggested = next(row for row in written if row["RowType"] == "SUGGESTED")
    assert suggested["Wavelength"] == f"MISSING\n({expected_wavelength})"


# ---------------------------------------------------------------------------
# Error handling: FileNotFoundError
# ---------------------------------------------------------------------------


def test_handle_audit_returns_1_on_file_not_found(tmp_path: Path) -> None:
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.side_effect = FileNotFoundError("not found")

        args = _make_args(inputs=[str(tmp_path)])
        result = handle_audit(args)

    assert result == 1
