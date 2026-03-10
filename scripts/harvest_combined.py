#!/usr/bin/env python3
"""Harvest COMPONENT rows from all KiCad projects and merge with SPCoast ITEM rows.

Produces examples/combined.csv with:
  - COMPONENT rows (deduplicated on ComponentID) from all KiCad projects,
    including Phase 4 context fields (footprint_full, symbol_lib, symbol_name)
  - ITEM rows from examples/SPCoast-INVENTORY.csv

The Phase 4 context fields are needed by jlcpcb_phase4_heuristics to route
CAP/IND/CON searches to the correct JLCPCB parametric category rather than
falling back to keyword-only queries.

Then optionally runs jbom inventory for multi-project batch coverage preview.

Usage:
    python scripts/harvest_combined.py
    python scripts/harvest_combined.py --dry-run-search
    python scripts/harvest_combined.py --projects-dir /path/to/projects
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

from jbom.common.component_id import (
    COLUMN_NORMALISE,
    COMPONENT_ROW_COLUMNS,
    is_null_value,
)


# ---------------------------------------------------------------------------
# Defaults (relative to jBOM project root)
# ---------------------------------------------------------------------------
JBOM_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = Path("/Users/jplocher/Dropbox/KiCad/projects")
SPCOAST_INVENTORY = JBOM_ROOT / "examples" / "SPCoast-INVENTORY.csv"
OUTPUT_FILE = JBOM_ROOT / "examples" / "combined.csv"

# ITEM columns always included (in this explicit order) after COMPONENT canonical
# columns, even when some values are empty.
_ITEM_ALWAYS_COLS: list[str] = [
    "IPN",
    "Description",
    "Keywords",
    "Manufacturer",
    "MPN",
    "LCSC",
    "Priority",
    "Status",
]

# Phase 4 heuristic context fields harvested from KiCad projects.
# Present only in COMPONENT rows; always included so the reader can exercise
# footprint/symbol-based routing (CAP electrolytic, IND subtype, CON series).
_COMPONENT_CONTEXT_COLS: list[str] = [
    "footprint_full",  # Full KiCad footprint ID, e.g. "Capacitor_SMD:CP_Elec_10x10"
    "symbol_lib",  # KiCad symbol library nickname, e.g. "Device"
    "symbol_name",  # KiCad symbol entry name, e.g. "C_Polarized"
]

# ITEM columns included only when at least one ITEM row carries a non-empty value.
_ITEM_CONDITIONAL_COLS: list[str] = [
    "ComponentName",
    "SMD",
    "Name",
    "Form",
    "Pins",
    "Pitch",
    "V",
    "A",
    "W",
    "Angle",
    "Wavelength",
    "mcd",
    "Frequency",
    "Mouser",
    "Mouser Link",
    "LCSC Link",
    "Symbol",
    "Footprint",
    "Datasheet",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_project_dirs(projects_dir: Path) -> list[Path]:
    """Return subdirectories of *projects_dir* that contain a .kicad_sch file."""
    dirs = []
    for d in sorted(projects_dir.iterdir()):
        if d.is_dir() and any(d.glob("*.kicad_sch")):
            dirs.append(d)
    return dirs


def _harvest_project(project_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Run ``jbom inventory`` (aggregated) on *project_dir* and return
    (component_rows, fieldnames).  The aggregated output already emits
    ``RowType=COMPONENT`` and ``ComponentID`` without per-instance fields.
    """
    result = subprocess.run(
        ["jbom", "inventory", str(project_dir), "-o", "-"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        print(
            f"  WARNING [{project_dir.name}]: {stderr or 'non-zero exit'}",
            file=sys.stderr,
        )
        return [], []

    reader = csv.DictReader(io.StringIO(result.stdout))
    # Strip blank/None field names (defensive: guards against schematic data issues)
    fieldnames: list[str] = [f for f in (reader.fieldnames or []) if f]

    rows = []
    for row in reader:
        cid = row.get("ComponentID", "")
        # Only keep real COMPONENT rows (non-empty ComponentID, RowType=COMPONENT)
        if row.get("RowType") == "COMPONENT" and cid:
            rows.append({k: v for k, v in row.items() if k})

    return rows, fieldnames


def _load_item_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Load all rows from an existing inventory CSV (e.g. SPCoast-INVENTORY.csv)."""
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return rows, fieldnames


def _normalise_component_row(row: dict[str, str]) -> dict[str, str]:
    """Rename legacy short column names and retain canonical + context columns.

    Step 1: apply COLUMN_NORMALISE (``W``→``Power``, ``A``→``Current``,
    ``V``→``Voltage``).  Long-form value wins if both old and new keys exist.
    Step 2: keep columns listed in COMPONENT_ROW_COLUMNS (identity) plus
    _COMPONENT_CONTEXT_COLS (Phase 4 heuristic inputs).
    """
    normalised: dict[str, str] = {}
    for k, v in row.items():
        canonical = COLUMN_NORMALISE.get(k, k)
        # Real value wins over blank or KiCad null (~); first real value wins.
        if canonical not in normalised or is_null_value(normalised[canonical]):
            normalised[canonical] = v
    keep = list(COMPONENT_ROW_COLUMNS) + _COMPONENT_CONTEXT_COLS
    return {col: normalised.get(col, "") for col in keep}


def _ordered_union(
    item_fields: list[str],
    item_rows: list[dict[str, str]],
) -> list[str]:
    """Return a deterministic union of column names.

    Column order (mirrors the ALWAYS/CONDITIONAL triage in inventory.py):
    1.  COMPONENT canonical columns (COMPONENT_ROW_COLUMNS) — always, in fixed order.
    1b. COMPONENT context columns (_COMPONENT_CONTEXT_COLS) — Phase 4 heuristic
        inputs; always included (blank for ITEM rows).
    2.  _ITEM_ALWAYS_COLS — important ITEM fields, always included if present.
    3.  _ITEM_CONDITIONAL_COLS — secondary ITEM fields, only when at least one row
        carries a non-empty value.
    4.  Any remaining item_fields not covered by the above lists.
    """
    item_field_set = set(item_fields)
    seen: set[str] = set()
    ordered: list[str] = []

    def _add_if_present(col: str) -> None:
        if col not in seen and col in item_field_set:
            seen.add(col)
            ordered.append(col)

    def _has_data(col: str) -> bool:
        return any(row.get(col) for row in item_rows)

    # 1. Canonical COMPONENT columns (always)
    for col in COMPONENT_ROW_COLUMNS:
        seen.add(col)
        ordered.append(col)

    # 1b. Phase 4 context columns from KiCad harvest (always; blank for ITEM rows)
    for col in _COMPONENT_CONTEXT_COLS:
        if col not in seen:
            seen.add(col)
            ordered.append(col)

    # 2. Important ITEM columns (always, if present in the source file)
    for col in _ITEM_ALWAYS_COLS:
        _add_if_present(col)

    # 3. Secondary ITEM columns (only when at least one row has data)
    for col in _ITEM_CONDITIONAL_COLS:
        if _has_data(col):
            _add_if_present(col)

    # 4. Any remaining item_fields not covered above (only when they carry data)
    for col in item_fields:
        if col not in seen and _has_data(col):
            seen.add(col)
            ordered.append(col)

    return ordered


def _write_combined(
    component_rows: list[dict[str, str]],
    item_rows: list[dict[str, str]],
    all_fields: list[str],
    output: Path,
) -> None:
    """Write the combined CSV to *output*."""
    with output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        for row in component_rows:
            writer.writerow({k: row.get(k, "") for k in all_fields})
        for row in item_rows:
            writer.writerow({k: row.get(k, "") for k in all_fields})


def _run_dry_run_search(combined_path: Path) -> None:
    """Run jbom inventory-search --dry-run --jlc to show JLC coverage stats."""
    print("\n--- Coverage preview (jbom inventory-search --dry-run --jlc) ---")
    result = subprocess.run(
        ["jbom", "inventory-search", str(combined_path), "--dry-run", "--jlc"],
        capture_output=False,
        text=True,
    )
    if result.returncode != 0:
        print("  WARNING: inventory-search returned non-zero exit", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=PROJECTS_DIR,
        help=f"Path to KiCad projects directory (default: {PROJECTS_DIR})",
    )
    parser.add_argument(
        "--spcoast",
        type=Path,
        default=SPCOAST_INVENTORY,
        help="Path to SPCoast-INVENTORY.csv (default: examples/SPCoast-INVENTORY.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=OUTPUT_FILE,
        help="Output file path (default: examples/combined.csv)",
    )
    parser.add_argument(
        "--exclude",
        metavar="PROJECT",
        action="append",
        dest="exclude",
        default=[],
        help="Project directory name(s) to skip (can be repeated). "
        "Use for known-bad or corrupted projects.",
    )
    parser.add_argument(
        "--dry-run-search",
        action="store_true",
        help="After writing combined.csv, run jbom inventory-search --dry-run",
    )
    args = parser.parse_args(argv)

    # ---- Discover projects ----
    project_dirs = _find_project_dirs(args.projects_dir)
    if args.exclude:
        excluded = set(args.exclude)
        project_dirs = [d for d in project_dirs if d.name not in excluded]
        print(
            f"Found {len(project_dirs)} KiCad project(s) in {args.projects_dir} "
            f"(excluding: {', '.join(sorted(excluded))})"
        )
    else:
        print(f"Found {len(project_dirs)} KiCad project(s) in {args.projects_dir}")

    # ---- Harvest COMPONENT rows ----
    component_rows_by_id: dict[str, dict[str, str]] = {}
    total_harvested = 0

    for proj_dir in project_dirs:
        rows, _fields = _harvest_project(proj_dir)
        total_harvested += len(rows)

        # Deduplicate by ComponentID (first occurrence wins)
        new_count = 0
        for row in rows:
            cid = row.get("ComponentID", "")
            if cid and cid not in component_rows_by_id:
                component_rows_by_id[cid] = row
                new_count += 1

        print(f"  {proj_dir.name:35s}: {len(rows):3d} rows  (+{new_count} unique)")

    component_rows = [
        _normalise_component_row(r) for r in component_rows_by_id.values()
    ]
    print(
        f"\nHarvested {total_harvested} total COMPONENT rows across {len(project_dirs)} project(s)."
    )
    print(f"After deduplication: {len(component_rows)} unique COMPONENT rows.")

    # ---- Load ITEM rows ----
    item_rows, item_fields = _load_item_rows(args.spcoast)
    print(f"Loaded {len(item_rows)} ITEM rows from {args.spcoast.name}.")

    # ---- Build unified field list ----
    all_fields = _ordered_union(item_fields, item_rows)
    print(f"Combined column count: {len(all_fields)}")

    # ---- Write output ----
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _write_combined(component_rows, item_rows, all_fields, args.output)
    print(f"\nWrote {len(component_rows) + len(item_rows)} rows → {args.output}")

    # ---- Optional dry-run search ----
    if args.dry_run_search:
        _run_dry_run_search(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
