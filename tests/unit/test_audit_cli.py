"""Unit tests for jbom.cli.audit — argument parsing and exit code behaviour.

These tests invoke the handler directly rather than through subprocess to keep
them fast and independent of the installed entry point.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from jbom.cli.audit import handle_audit
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
    assert args.output == Path("report.csv")


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
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


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
    assert "QUALITY_ISSUE" in content
    assert "R1" in content


def test_output_file_has_all_csv_columns(tmp_path: Path) -> None:
    from jbom.services.audit_service import REPORT_CSV_COLUMNS

    report_path = tmp_path / "report.csv"

    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        args = _make_args(inputs=[str(tmp_path)], output=report_path)
        handle_audit(args)

    assert report_path.exists()
    with report_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames or []) == set(REPORT_CSV_COLUMNS)


def test_output_to_stdout_contains_csv_header(tmp_path: Path, capsys) -> None:
    """When -o is not specified, CSV should be written to stdout."""
    with patch("jbom.cli.audit.AuditService") as MockService:
        instance = MockService.return_value
        instance.audit_project.return_value = _mock_report()

        args = _make_args(inputs=[str(tmp_path)])
        handle_audit(args)

    captured = capsys.readouterr()
    assert "CheckType" in captured.out, "CSV header should appear in stdout"


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
