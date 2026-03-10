#!/usr/bin/env python3
"""Validate Phase 4 parametric query plan quality for COMPONENT rows.

Loads combined.csv (or any inventory CSV) and calls build_parametric_query_plan
for each COMPONENT row in search-relevant categories (CAP, IND, CON by default).
Reports per-item plan type and details, then summarises hit rates per category.

No API calls are made — this is a pure local introspection tool.

Usage:
    python scripts/validate_phase4_plans.py
    python scripts/validate_phase4_plans.py --categories CAP,IND,CON
    python scripts/validate_phase4_plans.py --file examples/combined.csv
    python scripts/validate_phase4_plans.py --categories RES --verbose
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from the project root without install.
_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE / "src"))

# fmt: off
from jbom.common.component_classification import normalize_component_type  # noqa: E402
from jbom.common.value_parsing import farad_to_eia, henry_to_eia, ohms_to_eia  # noqa: E402
from jbom.services.inventory_reader import InventoryReader  # noqa: E402
from jbom.services.search.inventory_search_service import InventorySearchService  # noqa: E402
from jbom.suppliers.lcsc.query_planner import build_parametric_query_plan  # noqa: E402
# fmt: on

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
JBOM_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILE = JBOM_ROOT / "examples" / "combined.csv"
DEFAULT_CATEGORIES = {"CAP", "IND", "CON"}

_PLAN_WIDTH = 46  # truncation width for plan detail column


def _plan_summary(plan) -> str:
    """Return a compact one-line summary of a Phase 4 plan."""
    if plan.use_parametric:
        attrs = " ".join(f"{k}={','.join(v)}" for k, v in plan.component_attribute_list)
        specs = " ".join(plan.component_specification_list)
        detail = f"{plan.second_sort_name or plan.first_sort_name}"
        if specs:
            detail += f" [{specs}]"
        if attrs:
            detail += f" {attrs}"
        # For keyword-enriched parametric plans (e.g. CON), show the query.
        elif plan.keyword_query and plan.keyword_query != plan.base_query:
            detail += f"  q={plan.keyword_query!r}"
        return f"PARAMETRIC  {detail}"
    return f"keyword     {plan.reason}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=DEFAULT_FILE,
        help=f"Inventory CSV to analyse (default: {DEFAULT_FILE})",
    )
    parser.add_argument(
        "--categories",
        default=",".join(sorted(DEFAULT_CATEGORIES)),
        help="Comma-separated categories to analyse (default: CAP,CON,IND)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all rows, not just non-parametric ones",
    )
    parser.add_argument(
        "--component-rows-only",
        action="store_true",
        default=True,
        help="Only analyse COMPONENT rows (default: True)",
    )
    parser.add_argument(
        "--all-rows",
        dest="component_rows_only",
        action="store_false",
        help="Analyse both COMPONENT and ITEM rows",
    )
    args = parser.parse_args(argv)

    selected_cats = {c.strip().upper() for c in args.categories.split(",") if c.strip()}

    # ---- Load inventory ----
    reader = InventoryReader(args.file)
    reader.load()
    all_items = reader.inventory

    # ---- Filter ----
    searchable = InventorySearchService.filter_searchable_items(
        all_items, categories=",".join(selected_cats)
    )
    if args.component_rows_only:
        searchable = [i for i in searchable if i.row_type == "COMPONENT"]

    if not searchable:
        print(
            f"No searchable {'COMPONENT ' if args.component_rows_only else ''}rows "
            f"found for categories: {', '.join(sorted(selected_cats))}"
        )
        return 0

    # ---- Build plans and collect stats ----
    # Stats: per-category counts of parametric vs keyword
    stats: dict[str, dict[str, int]] = {}

    print(
        f"{'Category':6s}  {'Value':12s}  {'Package':22s}  "
        f"{'fp_full / sym_name':30s}  Plan"
    )
    print("-" * 120)

    for item in sorted(searchable, key=lambda i: (i.category, i.value)):
        cat = (item.category or "").upper().strip()
        stats.setdefault(cat, {"parametric": 0, "keyword": 0, "total": 0})
        stats[cat]["total"] += 1

        # Build the base keyword query the same way the service would.
        cat_norm = normalize_component_type(cat)
        if cat_norm == "CAP" and item.capacitance is not None:
            base = farad_to_eia(item.capacitance) + " capacitor"
        elif cat_norm == "IND" and item.inductance is not None:
            base = henry_to_eia(item.inductance) + " inductor"
        elif cat_norm == "RES" and item.resistance is not None:
            base = ohms_to_eia(item.resistance) + " resistor"
        else:
            base = f"{item.value} {cat_norm.lower()}"

        plan = build_parametric_query_plan(item, base_query=base)

        if plan.use_parametric:
            stats[cat]["parametric"] += 1
        else:
            stats[cat]["keyword"] += 1

        # Print detail line: show non-parametric always; parametric only with --verbose
        if args.verbose or not plan.use_parametric:
            fp_or_sym = (item.footprint_full or item.symbol_name or "").strip()
            fp_short = fp_or_sym[:30] if fp_or_sym else ""
            summary = _plan_summary(plan)
            print(
                f"{cat:6s}  {str(item.value)[:12]:12s}  {str(item.package)[:22]:22s}  "
                f"{fp_short:30s}  {summary}"
            )

    # ---- Summary ----
    print()
    print("=" * 60)
    print(
        f"{'Category':8s}  {'Total':>6s}  {'Parametric':>10s}  {'Keyword':>7s}  {'Hit%':>6s}"
    )
    print("-" * 60)
    grand_total = grand_para = 0
    for cat in sorted(stats):
        d = stats[cat]
        pct = 100 * d["parametric"] / d["total"] if d["total"] else 0
        print(
            f"{cat:8s}  {d['total']:>6d}  {d['parametric']:>10d}  "
            f"{d['keyword']:>7d}  {pct:>5.0f}%"
        )
        grand_total += d["total"]
        grand_para += d["parametric"]

    if grand_total:
        grand_pct = 100 * grand_para / grand_total
        print("-" * 60)
        print(
            f"{'TOTAL':8s}  {grand_total:>6d}  {grand_para:>10d}  "
            f"{grand_total - grand_para:>7d}  {grand_pct:>5.0f}%"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
