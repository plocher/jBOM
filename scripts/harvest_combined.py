#!/usr/bin/env python3
"""Harvest COMPONENT rows from all KiCad projects and merge with SPCoast ITEM rows.

Produces examples/combined.csv with:
  - COMPONENT rows (deduplicated on ComponentID) from all 13 KiCad projects
  - ITEM rows from examples/SPCoast-INVENTORY.csv

Then optionally runs jbom inventory-search for coverage preview.

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


# ---------------------------------------------------------------------------
# Defaults (relative to jBOM project root)
# ---------------------------------------------------------------------------
JBOM_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = Path("/Users/jplocher/Dropbox/KiCad/projects")
SPCOAST_INVENTORY = JBOM_ROOT / "examples" / "SPCoast-INVENTORY.csv"
OUTPUT_FILE = JBOM_ROOT / "examples" / "combined.csv"

# Preferred column order for the combined output.
# Columns that appear in BOTH sources come first; source-specific cols follow.
_LEADING_COLS = [
    "RowType",
    "ComponentID",
    "IPN",
    "Category",
    "Value",
    "Description",
    "Package",
    "Tolerance",
    "Resistance",
    "Capacitance",
    "Inductance",
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
    """Run ``jbom inventory --no-aggregate`` on *project_dir* and return
    (component_rows, fieldnames).  Sub-header sentinel rows are excluded.
    """
    result = subprocess.run(
        ["jbom", "inventory", str(project_dir), "-o", "-", "--no-aggregate"],
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
    fieldnames: list[str] = list(reader.fieldnames or [])

    # Strip blank/None field names (can appear when a KiCad component has an
    # empty-string property key — a schematic data-quality issue)
    fieldnames = [f for f in fieldnames if f]

    rows = []
    for row in reader:
        # Skip the sub-header sentinel rows written by --no-aggregate
        if row.get("ComponentID") == "ComponentID":
            continue
        if row.get("RowType") == "COMPONENT":
            rows.append({k: v for k, v in row.items() if k})

    return rows, fieldnames


def _load_item_rows(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Load all rows from an existing inventory CSV (e.g. SPCoast-INVENTORY.csv)."""
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    return rows, fieldnames


def _ordered_union(
    component_fields: list[str],
    item_fields: list[str],
) -> list[str]:
    """Return a deterministic union of column names.

    Leading columns come first; then COMPONENT-specific (project provenance
    and search-hint fields); then remaining ITEM-specific columns.
    """
    seen: set[str] = set()
    ordered: list[str] = []

    def _add(col: str) -> None:
        if col not in seen:
            seen.add(col)
            ordered.append(col)

    for col in _LEADING_COLS:
        _add(col)

    # All COMPONENT fields in their natural order
    for col in component_fields:
        _add(col)

    # Remaining ITEM fields
    for col in item_fields:
        _add(col)

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
    """Run jbom inventory-search --dry-run to show coverage stats."""
    print("\n--- Coverage preview (jbom inventory-search --dry-run) ---")
    result = subprocess.run(
        ["jbom", "inventory-search", str(combined_path), "--dry-run"],
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
    all_component_fields: list[str] = []
    component_rows_by_id: dict[str, dict[str, str]] = {}
    total_harvested = 0

    for proj_dir in project_dirs:
        rows, fields = _harvest_project(proj_dir)
        total_harvested += len(rows)

        # Union of field names across all projects
        for f in fields:
            if f not in all_component_fields:
                all_component_fields.append(f)

        # Deduplicate by ComponentID (first occurrence wins)
        new_count = 0
        for row in rows:
            cid = row.get("ComponentID", "")
            if cid and cid not in component_rows_by_id:
                component_rows_by_id[cid] = row
                new_count += 1

        print(f"  {proj_dir.name:35s}: {len(rows):3d} rows  (+{new_count} unique)")

    component_rows = list(component_rows_by_id.values())
    print(
        f"\nHarvested {total_harvested} total COMPONENT rows across {len(project_dirs)} project(s)."
    )
    print(f"After deduplication: {len(component_rows)} unique COMPONENT rows.")

    # ---- Load ITEM rows ----
    item_rows, item_fields = _load_item_rows(args.spcoast)
    print(f"Loaded {len(item_rows)} ITEM rows from {args.spcoast.name}.")

    # ---- Build unified field list ----
    all_fields = _ordered_union(all_component_fields, item_fields)
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
