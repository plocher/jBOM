"""Unit tests for jbom.services.audit_service.

These tests use minimal in-memory fixtures (synthetic schematics and CSVs
written to tmp_path) to avoid touching real KiCad project structures.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from jbom.services.audit_service import (
    AuditReport,
    AuditRow,
    AuditService,
    CheckType,
    REPORT_CSV_COLUMNS,
    Severity,
    _is_blank,
)


# ---------------------------------------------------------------------------
# Helpers for writing minimal fixtures
# ---------------------------------------------------------------------------


def _write_schematic(
    path: Path,
    components: list[dict],
) -> None:
    """Write a minimal .kicad_sch with one or more symbol nodes."""
    symbols_sexp = ""
    for comp in components:
        ref = comp.get("reference", "R1")
        value = comp.get("value", "10K")
        footprint = comp.get("footprint", "Resistor_SMD:R_0603_1608Metric")
        lib_id = comp.get("lib_id", "Device:R")
        uuid = comp.get("uuid", f"uuid-{ref.lower()}")
        props = comp.get("extra_props", {})

        # Build extra property s-expressions
        extra_sexp = ""
        for i, (key, val) in enumerate(props.items(), start=10):
            extra_sexp += f'    (property "{key}" "{val}" (id {i}) (at 0 0 0))\n'

        symbols_sexp += f"""  (symbol (lib_id "{lib_id}") (at 50 50 0)
    (uuid "{uuid}")
    (in_bom yes) (on_board yes) (dnp no)
    (property "Reference" "{ref}" (id 0) (at 50 48 0))
    (property "Value" "{value}" (id 1) (at 50 52 0))
    (property "Footprint" "{footprint}" (id 2) (at 50 54 0))
{extra_sexp}  )
"""

    content = f"""(kicad_sch (version 20211123) (generator eeschema)
{symbols_sexp})
"""
    path.write_text(content, encoding="utf-8")


def _write_kicad_pro(path: Path) -> None:
    """Write a minimal .kicad_pro file."""
    path.write_text("{}", encoding="utf-8")


def _write_inventory_csv(path: Path, rows: list[dict]) -> None:
    """Write a minimal inventory CSV with RowType, IPN, Category, Value, Package columns."""
    fieldnames = [
        "RowType",
        "IPN",
        "Category",
        "Value",
        "Package",
        "Manufacturer",
        "MFGPN",
        "Tolerance",
        "Voltage",
        "Current",
        "Power",
        "Description",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: "" for k in fieldnames}, **row})


def _write_requirements_csv(path: Path, rows: list[dict]) -> None:
    """Write a COMPONENT-type requirements CSV."""
    fieldnames = [
        "RowType",
        "ComponentID",
        "Category",
        "Value",
        "Package",
        "Tolerance",
        "Voltage",
        "Current",
        "Power",
        "IPN",
        "UUID",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {**{k: "" for k in fieldnames}, "RowType": "COMPONENT", **row}
            )


# ---------------------------------------------------------------------------
# Helper: create a minimal KiCad project dir
# ---------------------------------------------------------------------------


def _make_project(
    tmp_path: Path,
    components: list[dict],
    name: str = "proj",
) -> Path:
    """Create a minimal KiCad project directory and return its path."""
    proj_dir = tmp_path / name
    proj_dir.mkdir(parents=True, exist_ok=True)
    _write_kicad_pro(proj_dir / f"{name}.kicad_pro")
    _write_schematic(proj_dir / f"{name}.kicad_sch", components)
    return proj_dir


# ---------------------------------------------------------------------------
# _is_blank helper
# ---------------------------------------------------------------------------


def test_is_blank_empty_string() -> None:
    assert _is_blank("") is True


def test_is_blank_whitespace() -> None:
    assert _is_blank("   ") is True


def test_is_blank_tilde() -> None:
    assert _is_blank("~") is True


def test_is_blank_tilde_with_spaces() -> None:
    assert _is_blank("  ~  ") is True


def test_is_blank_non_empty() -> None:
    assert _is_blank("10K") is False


# ---------------------------------------------------------------------------
# AuditReport.write_csv
# ---------------------------------------------------------------------------


def test_audit_report_write_csv_has_all_columns() -> None:
    report = AuditReport()
    buf = io.StringIO()
    report.write_csv(buf)
    buf.seek(0)
    reader = csv.DictReader(buf)
    assert set(reader.fieldnames or []) == set(REPORT_CSV_COLUMNS)


def test_audit_report_write_csv_with_rows() -> None:
    row = AuditRow(
        check_type=CheckType.QUALITY_ISSUE,
        severity=Severity.ERROR,
        project_path="/proj",
        ref_des="R1",
        uuid="uuid-r1",
        category="RES",
        field="Value",
        description="R1: required field 'Value' is missing",
    )
    report = AuditReport(rows=[row], error_count=1)
    buf = io.StringIO()
    report.write_csv(buf)
    buf.seek(0)
    rows = list(csv.DictReader(buf))
    assert len(rows) == 1
    assert rows[0]["CheckType"] == "QUALITY_ISSUE"
    assert rows[0]["Severity"] == "ERROR"
    assert rows[0]["RefDes"] == "R1"


# ---------------------------------------------------------------------------
# AuditReport.exit_code
# ---------------------------------------------------------------------------


def test_exit_code_zero_when_no_errors() -> None:
    report = AuditReport(warn_count=2, info_count=3)
    assert report.exit_code == 0


def test_exit_code_one_when_errors() -> None:
    report = AuditReport(error_count=1)
    assert report.exit_code == 1


def test_exit_code_strict_zero_when_no_issues() -> None:
    report = AuditReport()
    assert report.exit_code_strict() == 0


def test_exit_code_strict_one_when_only_warnings() -> None:
    report = AuditReport(warn_count=1)
    assert report.exit_code_strict() == 1


# ---------------------------------------------------------------------------
# audit_project — local heuristics: REQUIRED field checks
# ---------------------------------------------------------------------------


def test_audit_project_required_value_missing(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    quality_errors = [
        r
        for r in report.rows
        if r.check_type == CheckType.QUALITY_ISSUE
        and r.severity == Severity.ERROR
        and r.field == "Value"
    ]
    assert quality_errors, "Expected QUALITY_ISSUE/ERROR for missing Value"
    assert quality_errors[0].ref_des == "R1"


def test_audit_project_required_footprint_missing(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [{"reference": "R1", "value": "10K", "footprint": "", "lib_id": "Device:R"}],
    )
    service = AuditService()
    report = service.audit_project([proj])

    quality_errors = [
        r
        for r in report.rows
        if r.check_type == CheckType.QUALITY_ISSUE
        and r.severity == Severity.ERROR
        and r.field == "Footprint"
    ]
    assert quality_errors, "Expected QUALITY_ISSUE/ERROR for missing Footprint"


def test_audit_project_required_tilde_treated_as_missing(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "~",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    quality_errors = [
        r
        for r in report.rows
        if r.check_type == CheckType.QUALITY_ISSUE
        and r.severity == Severity.ERROR
        and r.field == "Value"
    ]
    assert quality_errors, "Tilde value should be treated as missing (ERROR)"


# ---------------------------------------------------------------------------
# audit_project — local heuristics: BEST_PRACTICE field checks
# ---------------------------------------------------------------------------


def test_audit_project_resistor_missing_tolerance_is_warn(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    tolerance_warns = [
        r
        for r in report.rows
        if r.check_type == CheckType.QUALITY_ISSUE
        and r.severity == Severity.WARN
        and r.field == "Tolerance"
    ]
    assert (
        tolerance_warns
    ), "Expected QUALITY_ISSUE/WARN for missing Tolerance on resistor"


def test_audit_project_capacitor_missing_voltage_is_warn(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "C1",
                "value": "100nF",
                "footprint": "Capacitor_SMD:C_0603_1608Metric",
                "lib_id": "Device:C",
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    voltage_warns = [
        r
        for r in report.rows
        if r.check_type == CheckType.QUALITY_ISSUE
        and r.severity == Severity.WARN
        and r.field == "Voltage"
    ]
    assert voltage_warns, "Expected QUALITY_ISSUE/WARN for missing Voltage on capacitor"


def test_audit_project_component_with_all_fields_no_required_errors(
    tmp_path: Path,
) -> None:
    """A component with Value, Footprint, and all universal best-practice fields set should
    produce no REQUIRED-severity errors."""
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
                "extra_props": {
                    "Manufacturer": "Vishay",
                    "MFGPN": "CRCW060310K0FKEA",
                    "Tolerance": "1%",
                    "Power": "0.1W",
                },
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    errors = [r for r in report.rows if r.severity == Severity.ERROR]
    assert not errors, f"Unexpected errors for well-specified component: {errors}"


def test_audit_project_warns_do_not_affect_exit_code_default(tmp_path: Path) -> None:
    """WARN rows alone should not set exit_code to 1 (only ERRORs do by default)."""
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    assert report.warn_count > 0, "Expected at least one WARN (missing Tolerance etc.)"
    assert report.exit_code == 0, "WARNs alone should not trigger exit_code=1"


# ---------------------------------------------------------------------------
# audit_project — suggested values populated
# ---------------------------------------------------------------------------


def test_audit_project_quality_issue_has_suggested_value(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    service = AuditService()
    report = service.audit_project([proj])

    tolerance_row = next((r for r in report.rows if r.field == "Tolerance"), None)
    assert tolerance_row is not None
    assert (
        tolerance_row.suggested_value.strip() != ""
    ), "SuggestedValue should be populated for BEST_PRACTICE rows"


# ---------------------------------------------------------------------------
# audit_project — coverage dry-run: COVERAGE_GAP
# ---------------------------------------------------------------------------


def test_audit_project_coverage_gap_when_no_inventory_match(tmp_path: Path) -> None:
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "100K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    # Inventory has a totally different component (capacitor, not matching R1)
    inv = tmp_path / "catalog.csv"
    _write_inventory_csv(
        inv,
        [
            {
                "RowType": "ITEM",
                "IPN": "CAP001",
                "Category": "CAP",
                "Value": "100nF",
                "Package": "0603",
                "Manufacturer": "Murata",
                "MFGPN": "GRM188R71C104KA01D",
            }
        ],
    )

    service = AuditService()
    report = service.audit_project([proj], inventory_path=inv)

    gap_rows = [r for r in report.rows if r.check_type == CheckType.COVERAGE_GAP]
    assert gap_rows, "Expected COVERAGE_GAP for unmatched resistor"
    assert gap_rows[0].severity == Severity.ERROR
    assert gap_rows[0].ref_des == "R1"


# ---------------------------------------------------------------------------
# audit_project — coverage dry-run: silent exact match
# ---------------------------------------------------------------------------


def test_audit_project_no_coverage_row_for_exact_match(tmp_path: Path) -> None:
    """When inventory has an exact match, no COVERAGE_* row should appear."""
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    inv = tmp_path / "catalog.csv"
    _write_inventory_csv(
        inv,
        [
            {
                "RowType": "ITEM",
                "IPN": "RES001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
                "Manufacturer": "Vishay",
                "MFGPN": "CRCW060310K0FKEA",
            }
        ],
    )

    service = AuditService()
    report = service.audit_project([proj], inventory_path=inv)

    coverage_rows = [
        r
        for r in report.rows
        if r.check_type
        in (
            CheckType.COVERAGE_GAP,
            CheckType.MATCH_HEURISTIC,
            CheckType.MATCH_AMBIGUOUS,
        )
    ]
    assert (
        not coverage_rows
    ), f"Expected no coverage rows for exact match, got: {coverage_rows}"


# ---------------------------------------------------------------------------
# audit_project — coverage dry-run: IPN exact exclusive match (silent)
# ---------------------------------------------------------------------------


def test_audit_project_ipn_match_is_silent(tmp_path: Path) -> None:
    """A component with a matching IPN should produce no coverage rows."""
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
                "extra_props": {"IPN": "RES001"},
            }
        ],
    )
    inv = tmp_path / "catalog.csv"
    _write_inventory_csv(
        inv,
        [
            {
                "RowType": "ITEM",
                "IPN": "RES001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
            }
        ],
    )

    service = AuditService()
    report = service.audit_project([proj], inventory_path=inv)

    coverage_rows = [
        r
        for r in report.rows
        if r.check_type
        in (
            CheckType.COVERAGE_GAP,
            CheckType.MATCH_HEURISTIC,
            CheckType.MATCH_AMBIGUOUS,
        )
    ]
    assert not coverage_rows, "IPN exact match should be silent (no coverage rows)"


# ---------------------------------------------------------------------------
# audit_project — coverage dry-run: MATCH_AMBIGUOUS
# ---------------------------------------------------------------------------


def test_audit_project_match_ambiguous_multiple_exact_candidates(
    tmp_path: Path,
) -> None:
    """Multiple high-score catalog items should produce MATCH_AMBIGUOUS."""
    proj = _make_project(
        tmp_path,
        [
            {
                "reference": "R1",
                "value": "10K",
                "footprint": "Resistor_SMD:R_0603_1608Metric",
                "lib_id": "Device:R",
            }
        ],
    )
    inv = tmp_path / "catalog.csv"
    # Two identical-scoring 10K 0603 resistors from different manufacturers
    _write_inventory_csv(
        inv,
        [
            {
                "RowType": "ITEM",
                "IPN": "RES001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
                "Manufacturer": "Vishay",
                "MFGPN": "CRCW060310K0FKEA",
            },
            {
                "RowType": "ITEM",
                "IPN": "RES002",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
                "Manufacturer": "Yageo",
                "MFGPN": "RC0603FR-0710KL",
            },
        ],
    )

    service = AuditService()
    report = service.audit_project([proj], inventory_path=inv)

    ambiguous = [r for r in report.rows if r.check_type == CheckType.MATCH_AMBIGUOUS]
    assert ambiguous, "Expected MATCH_AMBIGUOUS for multiple equally-scored candidates"
    assert ambiguous[0].severity == Severity.INFO


# ---------------------------------------------------------------------------
# audit_inventory — UNUSED_ITEM
# ---------------------------------------------------------------------------


def test_audit_inventory_unused_item(tmp_path: Path) -> None:
    """Catalog items not matched by any requirement should be UNUSED_ITEM."""
    catalog = tmp_path / "catalog.csv"
    _write_inventory_csv(
        catalog,
        [
            {
                "RowType": "ITEM",
                "IPN": "RES001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
            },
            {
                "RowType": "ITEM",
                "IPN": "CAP001",
                "Category": "CAP",
                "Value": "100nF",
                "Package": "0402",
            },
        ],
    )

    req = tmp_path / "requirements.csv"
    _write_requirements_csv(
        req,
        [
            # Only asks for the resistor
            {"Category": "RES", "Value": "10K", "Package": "0603"},
        ],
    )

    service = AuditService()
    report = service.audit_inventory([catalog], requirements_path=req)

    unused = [r for r in report.rows if r.check_type == CheckType.UNUSED_ITEM]
    unused_ipns = {r.ipn for r in unused}
    assert "CAP001" in unused_ipns, "CAP001 should be UNUSED_ITEM"
    assert "RES001" not in unused_ipns, "RES001 was matched and should not be UNUSED"


# ---------------------------------------------------------------------------
# audit_inventory — COVERAGE_GAP
# ---------------------------------------------------------------------------


def test_audit_inventory_coverage_gap_for_unmatched_requirement(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    _write_inventory_csv(
        catalog,
        [
            {
                "RowType": "ITEM",
                "IPN": "CAP001",
                "Category": "CAP",
                "Value": "100nF",
                "Package": "0603",
            }
        ],
    )

    req = tmp_path / "requirements.csv"
    _write_requirements_csv(
        req,
        [
            {"Category": "RES", "Value": "100K", "Package": "0603"},  # not in catalog
        ],
    )

    service = AuditService()
    report = service.audit_inventory([catalog], requirements_path=req)

    gaps = [r for r in report.rows if r.check_type == CheckType.COVERAGE_GAP]
    assert gaps, "Expected COVERAGE_GAP for unmatched requirement"
    assert gaps[0].severity == Severity.ERROR


# ---------------------------------------------------------------------------
# audit_inventory — no requirements returns empty report
# ---------------------------------------------------------------------------


def test_audit_inventory_no_requirements_returns_empty(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.csv"
    _write_inventory_csv(
        catalog,
        [
            {
                "RowType": "ITEM",
                "IPN": "RES001",
                "Category": "RES",
                "Value": "10K",
                "Package": "0603",
            }
        ],
    )

    service = AuditService()
    report = service.audit_inventory([catalog], requirements_path=None)

    assert not report.rows, "Without requirements, no rows should be generated"
    assert report.exit_code == 0
