"""inventory-search command - bulk catalog search for inventory backfill (Phase 6.3)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import TextIO

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_selection_from_args,
)
from jbom.common.types import InventoryItem
from jbom.config.fabricators import load_fabricator
from jbom.config.providers import get_provider, list_searchable_suppliers
from jbom.config.suppliers import load_supplier, resolve_supplier_by_id
from jbom.services.inventory_reader import InventoryReader
from jbom.services.search.cache import DiskSearchCache, InMemorySearchCache, SearchCache
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.services.search.provider import SearchProvider
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _default_provider_for_fabricator(fabricator_id: str, *, api_key: str | None) -> str:
    """Pick the first available provider based on fab supplier priority."""

    fab = load_fabricator(fabricator_id)
    for supplier_id in fab.suppliers:
        supplier = resolve_supplier_by_id(supplier_id)
        if supplier is None or not supplier.search_providers:
            continue

        cfg = supplier.search_providers[0]
        if api_key:
            cfg = cfg.with_extra({"api_key": api_key})

        # Use a transient in-memory cache for availability probing.
        try:
            provider = get_provider(cfg, cache=InMemorySearchCache())
        except Exception:
            continue

        if provider.available():
            return supplier.id

    # Fallback: preserve historical default behavior.
    return "mouser"


def register_command(subparsers) -> None:
    """Register inventory-search command with argument parser."""

    parser = subparsers.add_parser(
        "inventory-search",
        help="Search distributor catalogs based on an inventory file",
        description="Bulk catalog search to find candidate supplier part numbers for inventory items.",
    )

    parser.add_argument(
        "inventory_file",
        help="Path to inventory file (CSV, Excel, or Numbers)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output destination for enhanced inventory CSV: omit/console for none, '-' for stdout, or a file path",
    )
    add_force_argument(parser)

    parser.add_argument(
        "--report",
        help="Output file for analysis report (default: stdout)",
    )

    parser.add_argument(
        "--provider",
        choices=list_searchable_suppliers(),
        default=None,
        help="Search provider to use (default: derived from fabricator supplier priority)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of candidates per inventory item (default: 3)",
    )

    parser.add_argument(
        "--api-key",
        help="API key for the provider (overrides env vars)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable persistent disk cache for this run",
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear persistent cache entries for this provider before running",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and compute searchable items without performing API calls",
    )

    parser.add_argument(
        "--categories",
        help="Comma-separated list of categories to search (e.g. 'RES,CAP,IC')",
    )

    # Fabricator selection (optional). When specified, inventory-search will scope
    # to items that are sparse for that fabricator.
    add_fabricator_arguments(parser)

    parser.set_defaults(handler=handle_inventory_search)


def handle_inventory_search(
    args: argparse.Namespace, *, _cache: SearchCache | None = None
) -> int:
    try:
        inventory_path = Path(args.inventory_file)
        if not inventory_path.exists():
            print(f"Error: Inventory file not found: {inventory_path}", file=sys.stderr)
            return 1

        reader = InventoryReader(inventory_path)
        items, _fields = reader.load()
        if not items:
            print("Error: No inventory items found in file", file=sys.stderr)
            return 1
        component_rows, item_rows = InventorySearchService.split_rows_by_type(items)
        search_base = component_rows if component_rows else item_rows

        # filter_searchable_items is pure logic — no provider or API key needed.
        searchable = InventorySearchService.filter_searchable_items(
            search_base, categories=args.categories
        )
        # Deduplication against item_rows only applies when COMPONENT rows are the
        # search target. In the fallback (ITEM-only inventory), search_base IS
        # item_rows — deduplicating against itself would zero out all results.
        if component_rows:
            searchable = _filter_already_covered_requirements(searchable, item_rows)

        # Fab-relative sparseness is opt-in: only apply when the user explicitly
        # selects a fabricator.
        fabricator_id, fabricator_explicit = resolve_fabricator_selection_from_args(
            args
        )
        if fabricator_explicit:
            fab = load_fabricator(fabricator_id)
            searchable = InventorySearchService.filter_sparse_items_for_fabricator(
                searchable,
                fabricator=fab,
            )

        if args.dry_run:
            _print_dry_run_summary(searchable)
            return 0

        provider_id = (args.provider or "").strip().lower()
        if not provider_id:
            # Preserve historical default when no fabricator is explicitly selected.
            provider_id = (
                _default_provider_for_fabricator(
                    fabricator_id,
                    api_key=args.api_key,
                )
                if fabricator_explicit
                else "mouser"
            )

        cache = _cache if _cache is not None else _build_cache(provider_id, args)
        provider = _create_provider(provider_id, api_key=args.api_key, cache=cache)
        service = InventorySearchService(
            provider,
            candidate_limit=args.limit,
            request_delay_seconds=0.2,
        )

        records = service.search(searchable)

        dest = resolve_output_destination(
            args.output,
            default_destination=OutputDestination(OutputKind.CONSOLE),
        )

        report = service.generate_report(records)
        if args.report:
            Path(args.report).write_text(report, encoding="utf-8")
        else:
            # If the user asked for CSV to stdout, keep stdout machine-readable by
            # emitting the human report to stderr.
            report_stream = sys.stderr if dest.kind == OutputKind.STDOUT else sys.stdout
            print(report, file=report_stream)

        if dest.kind == OutputKind.FILE or dest.kind == OutputKind.STDOUT:
            header_order = _load_header_order(inventory_path)
            enhanced_rows = service.enhance_inventory_rows(
                items,
                original_field_order=header_order,
                records=records,
            )
            out_fields = header_order + service.enhanced_csv_columns()

            if dest.kind == OutputKind.STDOUT:
                _write_enhanced_csv(enhanced_rows, out_fields, out=sys.stdout)
            else:
                if not dest.path:
                    raise ValueError(
                        "Internal error: file output selected but no path provided"
                    )

                out_path = dest.path
                refused = f"Error: Output file '{out_path}' already exists. Use -F/--force to overwrite."

                try:
                    with open_output_text_file(
                        out_path,
                        force=args.force,
                        refused_message=refused,
                    ) as f:
                        _write_enhanced_csv(enhanced_rows, out_fields, out=f)
                except OutputRefusedError as exc:
                    print(str(exc), file=sys.stderr)
                    return 1

                print(f"Enhanced inventory written to {out_path}")

        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _build_cache(provider_id: str, args: argparse.Namespace) -> SearchCache:
    if getattr(args, "clear_cache", False):
        DiskSearchCache.clear_provider(provider_id)

    if getattr(args, "no_cache", False):
        return InMemorySearchCache()

    return DiskSearchCache(provider_id)


def _create_provider(
    provider_id: str, *, api_key: str | None, cache: SearchCache
) -> SearchProvider:
    supplier_id = (provider_id or "").strip().lower()
    supplier = load_supplier(supplier_id)

    if not supplier.search_providers:
        raise ValueError(f"Supplier '{supplier_id}' has no configured search providers")

    cfg = supplier.search_providers[0]
    if api_key:
        cfg = cfg.with_extra({"api_key": api_key})

    provider = get_provider(cfg, cache=cache)
    if not provider.available():
        raise RuntimeError(provider.unavailable_reason())

    return provider


def _print_dry_run_summary(items) -> None:
    print("DRY RUN")
    print(f"Searchable items: {len(items)}")

    by_cat: dict[str, int] = {}
    for item in items:
        cat = (item.category or "").strip().upper() or "(missing)"
        by_cat[cat] = by_cat.get(cat, 0) + 1

    if by_cat:
        print("By category:")
        for cat, count in sorted(by_cat.items()):
            print(f"  {cat}: {count}")


def _filter_already_covered_requirements(
    component_rows: list[InventoryItem], item_rows: list[InventoryItem]
) -> list[InventoryItem]:
    """Skip search for COMPONENT requirements already satisfiable by ITEM rows."""
    if not component_rows or not item_rows:
        return component_rows

    matcher = SophisticatedInventoryMatcher(MatchingOptions())
    filtered = []
    for row in component_rows:
        requirement = InventorySearchService._inventory_item_to_component(row)
        matches = matcher.find_matches(requirement, item_rows)
        if not matches:
            filtered.append(row)
    return filtered


def _write_enhanced_csv(rows: list[dict], fields: list[str], *, out: TextIO) -> None:
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def _load_header_order(path: Path) -> list[str]:
    # Best effort: preserve original CSV header order.
    if path.suffix.lower() == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return next(reader)

    # For non-CSV, fall back to a stable default.
    return [
        "RowType",
        "ComponentID",
        "IPN",
        "Category",
        "Value",
        "Description",
        "Package",
        "Manufacturer",
        "MFGPN",
    ]
