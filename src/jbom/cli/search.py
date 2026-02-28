"""Search command - catalog lookup via external distributors (Phase 6)."""

from __future__ import annotations

import argparse
import csv
import sys
from typing import Optional, TextIO

from jbom.cli.formatting import Column, print_table
from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.services.search.cache import InMemorySearchCache, SearchCache
from jbom.services.search.filtering import (
    SearchFilter,
    SearchSorter,
    apply_default_filters,
)
from jbom.services.search.mouser_provider import MouserProvider
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider


def register_command(subparsers) -> None:
    """Register search command with argument parser."""

    parser = subparsers.add_parser(
        "search",
        help="Search distributor catalogs (e.g. Mouser)",
        description="Search distributor catalogs and print results.",
    )

    parser.add_argument(
        "query", help="Search query (keyword, part number, description)"
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
        default=10,
        help="Maximum number of results to display (default: 10)",
    )

    parser.add_argument("--api-key", help="API key (overrides env vars)")

    parser.add_argument(
        "--all",
        action="store_true",
        help="Disable default filters (show out-of-stock/obsolete results)",
    )

    parser.add_argument(
        "--no-parametric",
        action="store_true",
        help="Disable parametric filtering derived from the query text",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output destination: omit for console, use 'console' for table, '-' for CSV to stdout, or a file path",
    )
    add_force_argument(parser)

    parser.set_defaults(handler=handle_search)


def handle_search(args: argparse.Namespace) -> int:
    """Handle `jbom search` command."""

    cache = InMemorySearchCache()

    try:
        provider = _create_provider(args.provider, api_key=args.api_key, cache=cache)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Pull extra results to allow client-side filtering.
    display_limit = max(1, int(args.limit))
    fetch_limit = min(100, max(50, display_limit * 3))

    try:
        results = provider.search(args.query, limit=fetch_limit)
    except Exception as exc:
        print(f"Error: search failed: {exc}", file=sys.stderr)
        return 1

    if not args.all:
        results = apply_default_filters(results)

    # Parametric filtering is optional.
    if not args.no_parametric:
        results = SearchFilter.filter_by_query(results, args.query)

    results = SearchSorter.rank(results)
    results = results[:display_limit]

    force = bool(getattr(args, "force", False))
    return _output_results(results, output=args.output, force=force)


def _create_provider(
    provider_id: str, *, api_key: Optional[str], cache: SearchCache
) -> SearchProvider:
    pid = (provider_id or "").strip().lower()
    if pid == "mouser":
        return MouserProvider(api_key=api_key, cache=cache)

    raise ValueError(f"Unknown provider: {provider_id}")


def _output_results(
    results: list[SearchResult], *, output: Optional[str], force: bool
) -> int:
    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(OutputKind.CONSOLE),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console(results)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(results, out=sys.stdout)
        return 0

    if not dest.path:
        raise ValueError("Internal error: file output selected but no path provided")

    path = dest.path
    refused = (
        f"Error: Output file '{path}' already exists. Use -F/--force to overwrite."
    )

    try:
        with open_output_text_file(
            path,
            force=force,
            refused_message=refused,
        ) as f:
            _print_csv(results, out=f)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Search results written to {path}")
    return 0


def _print_console(results: list[SearchResult]) -> None:
    if not results:
        print("No results found.")
        return

    rows = [_row_for_result(r) for r in results]
    cols = [
        Column(
            header="Manufacturer", key="manufacturer", preferred_width=18, wrap=True
        ),
        Column(header="MPN", key="mpn", preferred_width=28, wrap=True),
        Column(
            header="Distributor PN",
            key="distributor_part_number",
            preferred_width=22,
            wrap=True,
        ),
        Column(
            header="Price", key="price", preferred_width=10, fixed=True, align="right"
        ),
        Column(
            header="Stock",
            key="stock_quantity",
            preferred_width=8,
            fixed=True,
            align="right",
        ),
        Column(
            header="Lifecycle", key="lifecycle_status", preferred_width=10, wrap=True
        ),
    ]

    print("")
    print_table(rows, cols, terminal_width=120)
    print("")
    print(f"Found {len(results)} results.")


def _print_csv(results: list[SearchResult], *, out: TextIO) -> None:
    writer = csv.DictWriter(out, fieldnames=_csv_headers())
    writer.writeheader()
    for r in results:
        writer.writerow(_csv_row_for_result(r))


def _csv_headers() -> list[str]:
    # House style: human-readable headers (Title Case / abbreviations) similar to
    # other jbom-new CSV outputs.
    return [
        "Manufacturer",
        "MPN",
        "Distributor",
        "Distributor PN",
        "Availability",
        "Stock",
        "Price",
        "Lifecycle",
        "Details URL",
    ]


def _csv_row_for_result(r: SearchResult) -> dict[str, str]:
    return {
        "Manufacturer": r.manufacturer,
        "MPN": r.mpn,
        "Distributor": r.distributor,
        "Distributor PN": r.distributor_part_number,
        "Availability": r.availability,
        "Stock": str(r.stock_quantity),
        "Price": r.price,
        "Lifecycle": r.lifecycle_status,
        "Details URL": r.details_url,
    }


def _row_for_result(r: SearchResult) -> dict[str, str]:
    # Internal row mapping used by console output.
    return {
        "manufacturer": r.manufacturer,
        "mpn": r.mpn,
        "distributor": r.distributor,
        "distributor_part_number": r.distributor_part_number,
        "availability": r.availability,
        "stock_quantity": str(r.stock_quantity),
        "price": r.price,
        "lifecycle_status": r.lifecycle_status,
        "details_url": r.details_url,
    }
