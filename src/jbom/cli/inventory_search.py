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
from jbom.services.inventory_reader import InventoryReader
from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.services.search.mouser_provider import MouserProvider


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
        choices=["mouser"],
        default="mouser",
        help="Search provider to use (default: mouser)",
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
        "--dry-run",
        action="store_true",
        help="Validate input and compute searchable items without performing API calls",
    )

    parser.add_argument(
        "--categories",
        help="Comma-separated list of categories to search (e.g. 'RES,CAP,IC')",
    )

    parser.set_defaults(handler=handle_inventory_search)


def handle_inventory_search(args: argparse.Namespace) -> int:
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

        # filter_searchable_items is pure logic — no provider or API key needed.
        searchable = InventorySearchService.filter_searchable_items(
            items, categories=args.categories
        )

        if args.dry_run:
            _print_dry_run_summary(searchable)
            return 0

        cache = InMemorySearchCache()
        provider = _create_provider(args.provider, api_key=args.api_key, cache=cache)
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


def _create_provider(provider_id: str, *, api_key: str | None, cache) -> MouserProvider:
    pid = (provider_id or "").strip().lower()
    if pid == "mouser":
        return MouserProvider(api_key=api_key, cache=cache)

    raise ValueError(f"Unknown provider: {provider_id}")


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
        "IPN",
        "Category",
        "Value",
        "Description",
        "Package",
        "Manufacturer",
        "MFGPN",
    ]
