"""Search command - catalog lookup via external suppliers (Phase 6)."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from dataclasses import dataclass
from typing import Callable, Optional, TextIO

from jbom.cli.formatting import Column, print_table
from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.config.providers import get_provider
from jbom.config.suppliers import list_suppliers, load_supplier, resolve_supplier_by_id
from jbom.services.search.cache import DiskSearchCache, InMemorySearchCache, SearchCache
from jbom.services.search.filtering import (
    SearchFilter,
    SearchSorter,
    apply_default_filters,
)
from jbom.services.search.models import SearchResult
from jbom.services.search.provider import SearchProvider


@dataclass(frozen=True)
class _FieldDef:
    """Registry entry describing a selectable search output field."""

    key: str
    column: Column
    extractor: Callable[[SearchResult], str]


def _s(r: SearchResult, value: object) -> str:
    # Ensure everything is a safe string for console/CSV output.
    return str(value if value is not None else "")


_FIELD_REGISTRY: dict[str, _FieldDef] = {
    # NOTE: SearchResult currently exposes distributor_part_number (normalized provider field).
    # We use supplier_part_number as the public registry key to keep the CLI supplier-agnostic.
    "supplier_part_number": _FieldDef(
        key="supplier_part_number",
        column=Column(
            header="Supplier PN",
            key="supplier_part_number",
            preferred_width=28,
            wrap=True,
        ),
        extractor=lambda r: _s(r, r.distributor_part_number),
    ),
    "mpn": _FieldDef(
        key="mpn",
        column=Column(header="MPN", key="mpn", preferred_width=18, wrap=True),
        extractor=lambda r: _s(r, r.mpn),
    ),
    "manufacturer": _FieldDef(
        key="manufacturer",
        column=Column(
            header="Manufacturer", key="manufacturer", preferred_width=16, wrap=True
        ),
        extractor=lambda r: _s(r, r.manufacturer),
    ),
    "price": _FieldDef(
        key="price",
        column=Column(
            header="Price",
            key="price",
            preferred_width=10,
            fixed=True,
            align="right",
        ),
        extractor=lambda r: _s(r, r.price),
    ),
    "stock_quantity": _FieldDef(
        key="stock_quantity",
        column=Column(
            header="Stock",
            key="stock_quantity",
            preferred_width=8,
            fixed=True,
            align="right",
        ),
        extractor=lambda r: _s(r, r.stock_quantity),
    ),
    "lifecycle_status": _FieldDef(
        key="lifecycle_status",
        column=Column(
            header="Lifecycle",
            key="lifecycle_status",
            preferred_width=10,
            wrap=True,
        ),
        extractor=lambda r: _s(r, r.lifecycle_status),
    ),
    "description": _FieldDef(
        key="description",
        column=Column(
            header="Description", key="description", preferred_width=60, wrap=True
        ),
        extractor=lambda r: _s(r, r.description),
    ),
    "availability": _FieldDef(
        key="availability",
        column=Column(
            header="Availability", key="availability", preferred_width=18, wrap=True
        ),
        extractor=lambda r: _s(r, r.availability),
    ),
    "details_url": _FieldDef(
        key="details_url",
        column=Column(
            header="Details URL", key="details_url", preferred_width=40, wrap=True
        ),
        extractor=lambda r: _s(r, r.details_url),
    ),
}


def _provider_choices() -> list[str]:
    """Return supplier IDs that declare at least one search provider."""

    out: list[str] = []
    for sid in list_suppliers():
        try:
            supplier = load_supplier(sid)
        except ValueError:
            continue

        if supplier.search_providers:
            out.append(supplier.id)

    return sorted(set(out))


def register_command(subparsers) -> None:
    """Register search command with argument parser."""

    parser = subparsers.add_parser(
        "search",
        help="Search supplier catalogs (e.g. Mouser)",
        description="Search supplier catalogs and print results.",
    )

    parser.add_argument(
        "query", help="Search query (keyword, part number, description)"
    )

    # Provider is selected by supplier ID, discovered from supplier YAML profiles.
    provider_choices = _provider_choices()
    default_provider = "mouser" if "mouser" in provider_choices else None
    if default_provider is None and provider_choices:
        default_provider = provider_choices[0]

    parser.add_argument(
        "--provider",
        choices=provider_choices,
        default=default_provider,
        help="Search provider to use (default: derived from supplier profiles)",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to display (default: 10)",
    )

    parser.add_argument("--api-key", help="API key (overrides env vars)")

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
        "--fields",
        help="Comma-separated list of output field registry keys (use --list-fields to discover)",
    )

    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List available field keys and exit",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output destination: omit for console, use 'console' for table, '-' for CSV to stdout, or a file path",
    )
    add_force_argument(parser)

    parser.set_defaults(handler=handle_search)


def handle_search(
    args: argparse.Namespace, *, _cache: SearchCache | None = None
) -> int:
    """Handle `jbom search` command."""

    if bool(getattr(args, "list_fields", False)):
        _print_list_fields()
        return 0

    resolved_fields = _resolve_fields_from_args(args)
    if resolved_fields is None:
        return 1

    cache = _cache if _cache is not None else _build_cache(args)

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
    return _output_results(
        results,
        output=args.output,
        force=force,
        fields=resolved_fields,
    )


def _print_list_fields() -> None:
    width = max((len(k) for k in _FIELD_REGISTRY.keys()), default=1) + 2
    print("\nAvailable fields:")
    for key in sorted(_FIELD_REGISTRY.keys()):
        label = _FIELD_REGISTRY[key].column.header
        print(f"  {key:<{width}}{label}")
    print("")


def _parse_fields_argument(fields: str) -> list[str] | None:
    raw = [t.strip() for t in (fields or "").split(",")]
    tokens: list[str] = []
    for tok in raw:
        if not tok:
            continue
        tokens.append(tok)

    if not tokens:
        print("Error: --fields parameter cannot be empty", file=sys.stderr)
        return None

    # Registry keys only.
    normalized = [t.strip().lower() for t in tokens]

    unknown = [f for f in normalized if f not in _FIELD_REGISTRY]
    if unknown:
        print(f"Error: Unknown field(s): {', '.join(unknown)}", file=sys.stderr)
        print("\nUse --list-fields to see valid field keys.", file=sys.stderr)
        return None

    # Deduplicate, preserve order.
    seen: set[str] = set()
    deduped: list[str] = []
    for f in normalized:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    return deduped


def _resolve_fields_from_args(args: argparse.Namespace) -> list[str] | None:
    # 1) CLI override
    if getattr(args, "fields", None) is not None:
        return _parse_fields_argument(args.fields)

    # 2) Supplier profile fields (provider id is the closest proxy for supplier id)
    supplier_id = (getattr(args, "provider", "") or "").strip().lower()
    supplier = resolve_supplier_by_id(supplier_id)
    if supplier is not None and supplier.search_fields:
        return list(supplier.search_fields)

    # 3) Generic profile fields
    try:
        generic = load_supplier("generic")
        if generic.search_fields:
            return list(generic.search_fields)
    except ValueError:
        pass

    # 4) Emergency fallback (keep it simple and always include description)
    return [
        "supplier_part_number",
        "price",
        "stock_quantity",
        "lifecycle_status",
        "description",
    ]


def _row_for_result(r: SearchResult) -> dict[str, str]:
    """Build a row mapping containing every known registry key."""

    return {k: _FIELD_REGISTRY[k].extractor(r) for k in _FIELD_REGISTRY.keys()}


def _build_cache(args: argparse.Namespace) -> SearchCache:
    if getattr(args, "clear_cache", False):
        DiskSearchCache.clear_provider(args.provider)

    if getattr(args, "no_cache", False):
        return InMemorySearchCache()

    return DiskSearchCache(args.provider)


def _create_provider(
    provider_id: str, *, api_key: Optional[str], cache: SearchCache
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


def _output_results(
    results: list[SearchResult],
    *,
    output: Optional[str],
    force: bool,
    fields: list[str],
) -> int:
    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(OutputKind.CONSOLE),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console(results, fields=fields)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(results, fields=fields, out=sys.stdout)
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
            _print_csv(results, fields=fields, out=f)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Search results written to {path}")
    return 0


def _print_console(results: list[SearchResult], *, fields: list[str]) -> None:
    if not results:
        print("No results found.")
        return

    rows = [_row_for_result(r) for r in results]

    cols: list[Column] = []
    for f in fields:
        if f not in _FIELD_REGISTRY:
            # Defensive: should never happen after validation.
            continue
        cols.append(_FIELD_REGISTRY[f].column)

    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
    print("")
    print_table(rows, cols, terminal_width=terminal_width)
    print("")
    print(f"Found {len(results)} results.")


def _print_csv(results: list[SearchResult], *, fields: list[str], out: TextIO) -> None:
    writer = csv.writer(out)
    writer.writerow(_csv_headers(fields))

    for r in results:
        row = _csv_row_for_result(r, fields)
        writer.writerow(row)


def _csv_headers(fields: list[str]) -> list[str]:
    return [_FIELD_REGISTRY[f].column.header for f in fields]


def _csv_row_for_result(r: SearchResult, fields: list[str]) -> list[str]:
    full = _row_for_result(r)
    return [str(full.get(f, "")) for f in fields]
