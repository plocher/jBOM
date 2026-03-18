"""Search command - catalog lookup via external suppliers (Phase 6)."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from typing import Callable, Optional, TextIO

from jbom.cli.formatting import Column, get_terminal_width, print_table
from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.config.defaults import get_defaults
from jbom.config.providers import get_provider, list_searchable_suppliers
from jbom.config.suppliers import load_supplier, resolve_supplier_by_id
from jbom.services.search.cache import DiskSearchCache, InMemorySearchCache, SearchCache
from jbom.services.search.filtering import (
    SearchFilter,
    SearchSorter,
    apply_default_filters,
)
from jbom.services.search.models import SearchResult
from jbom.services.search.query_shaping import shape_search_query
from jbom.services.search.provider import SearchProvider

_MAX_ADAPTIVE_FETCH_LIMIT = 1024


@dataclass(frozen=True)
class _FieldDef:
    """Registry entry describing a selectable search output field."""

    key: str
    column: Column
    extractor: Callable[[SearchResult], str]


def _s(r: SearchResult, value: object) -> str:
    # Ensure everything is a safe string for console/CSV output.
    return str(value if value is not None else "")


_PACKAGE_PATTERN = re.compile(
    r"\b(0201|0402|0603|0805|1206|1210|1812|2010|2512)\b", re.IGNORECASE
)


def _package_value(r: SearchResult) -> str:
    """Resolve package from normalized attrs or provider raw fields."""

    if r.attributes and r.attributes.get("Package"):
        return _s(r, r.attributes.get("Package", ""))

    if r.raw_data:
        for key in ("componentSpecificationEn", "Package", "package"):
            raw = str(r.raw_data.get(key, "")).strip()
            if raw:
                return raw

    match = _PACKAGE_PATTERN.search((r.description or "").upper())
    if match:
        return match.group(1).upper()

    return ""


def _component_library_tier_label(r: SearchResult) -> str:
    """Return display label for provider library tier metadata."""

    if not r.raw_data:
        return ""

    raw = str(r.raw_data.get("componentLibraryType", "")).strip().lower()
    if raw in {"base", "basic"}:
        return "basic"
    if raw in {"expand", "extended"}:
        return "extended"
    return ""


def _description_value(r: SearchResult) -> str:
    """Render description with optional basic/extended tier notation."""

    desc = str(r.description or "").strip()
    tier = _component_library_tier_label(r)
    if not tier:
        return desc
    if not desc:
        return f"[{tier}]"
    return f"[{tier}] {desc}"


def _category_value(r: SearchResult) -> str:
    """Resolve category from normalized field or provider raw payload."""

    if r.category:
        return r.category
    if r.raw_data:
        primary = str(r.raw_data.get("firstSortName", "")).strip()
        secondary = str(r.raw_data.get("secondSortName", "")).strip()
        if primary and secondary:
            return f"{secondary}: {primary}"
        if primary:
            return primary
        if secondary:
            return secondary
    return ""


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
    "package": _FieldDef(
        key="package",
        column=Column(header="Package", key="package", preferred_width=10, wrap=True),
        extractor=lambda r: _s(r, _package_value(r)),
    ),
    "category": _FieldDef(
        key="category",
        column=Column(header="Category", key="category", preferred_width=18, wrap=True),
        extractor=lambda r: _s(r, _category_value(r)),
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
        extractor=lambda r: _s(r, _description_value(r)),
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

_FIELD_ALIASES: dict[str, str] = {
    "stock": "stock_quantity",
    "supplier_pn": "supplier_part_number",
    "supplierpn": "supplier_part_number",
    "supplier_part": "supplier_part_number",
}


def _normalize_field_key(field_token: str) -> str:
    """Normalize a user-supplied field token to a registry key."""

    normalized = field_token.strip().lower().replace("-", "_").replace(" ", "_")
    return _FIELD_ALIASES.get(normalized, normalized)


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

    # Search backend is selected by supplier ID discovered from supplier YAML profiles.
    supplier_choices = list_searchable_suppliers()
    default_supplier = "generic" if "generic" in supplier_choices else None
    if default_supplier is None and supplier_choices:
        default_supplier = supplier_choices[0]

    parser.add_argument(
        "--supplier",
        type=lambda value: str(value).strip().lower(),
        choices=supplier_choices,
        default=default_supplier,
        help="Supplier ID to use for search (default: derived from supplier profiles)",
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
        help="Clear persistent cache entries for this supplier before running",
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
        provider = _create_provider(args.supplier, api_key=args.api_key, cache=cache)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Pull extra results to allow client-side filtering.
    display_limit = max(1, int(args.limit))
    initial_fetch_limit = min(100, max(50, display_limit * 3))
    shaped_query = shape_search_query(args.query)

    results = _run_adaptive_search_pipeline(
        provider=provider,
        args=args,
        query=shaped_query,
        display_limit=display_limit,
        initial_fetch_limit=initial_fetch_limit,
    )
    if results is None:
        return 1
    results = results[:display_limit]

    force = bool(getattr(args, "force", False))
    return _output_results(
        results,
        output=args.output,
        force=force,
        fields=resolved_fields,
    )


def _run_adaptive_search_pipeline(
    *,
    provider: SearchProvider,
    args: argparse.Namespace,
    query: str,
    display_limit: int,
    initial_fetch_limit: int,
    max_fetch_limit: int = _MAX_ADAPTIVE_FETCH_LIMIT,
) -> list[SearchResult] | None:
    """Fetch, filter, and rank with progressive window expansion when needed."""

    fetch_limit = max(1, int(initial_fetch_limit))
    max_limit = max(fetch_limit, int(max_fetch_limit))
    best_results: list[SearchResult] = []
    last_raw_count = -1

    while True:
        try:
            raw_results = provider.search(query, limit=fetch_limit)
        except Exception as exc:
            if not best_results:
                print(f"Error: search failed: {exc}", file=sys.stderr)
                return None
            break
        candidate_results = _apply_result_pipeline(raw_results, args, query=query)
        if len(candidate_results) > len(best_results):
            best_results = candidate_results

        if len(best_results) >= display_limit:
            break
        if fetch_limit >= max_limit:
            break

        raw_count = len(raw_results)
        if last_raw_count >= 0 and raw_count <= last_raw_count:
            # Provider appears saturated for this query; larger limits are unlikely to help.
            break
        last_raw_count = raw_count

        next_fetch_limit = min(max_limit, max(fetch_limit * 2, fetch_limit + 1))
        if next_fetch_limit == fetch_limit:
            break
        fetch_limit = next_fetch_limit

    return best_results


def _apply_result_pipeline(
    results: list[SearchResult], args: argparse.Namespace, *, query: str
) -> list[SearchResult]:
    """Apply default filters, parametric filtering, and ranking."""

    filtered = list(results)
    if not args.all:
        filtered = apply_default_filters(filtered)

    if not args.no_parametric:
        filtered = SearchFilter.filter_by_query(filtered, query)

    return SearchSorter.rank(filtered, query=query)


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
    normalized = [_normalize_field_key(t) for t in tokens]

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
    # 2) Supplier profile fields
    supplier_id = (getattr(args, "supplier", "") or "").strip().lower()
    supplier = resolve_supplier_by_id(supplier_id)
    if supplier is not None and supplier.search_fields:
        validated_supplier_fields = _validate_profile_field_list(
            supplier.search_fields, source=f"supplier profile '{supplier_id}'"
        )
        if validated_supplier_fields is None:
            return None
        return validated_supplier_fields

    # 3) Defaults profile fields (selected by --defaults, default: generic).
    defaults_cfg = get_defaults()
    defaults_fields = defaults_cfg.get_search_output_fields_default()
    if defaults_fields:
        validated_defaults_fields = _validate_profile_field_list(
            defaults_fields, source=f"defaults profile '{defaults_cfg.name}'"
        )
        if validated_defaults_fields is None:
            return None
        return validated_defaults_fields

    print(
        "Error: No default search fields configured. Set supplier.search.fields "
        "or defaults.search.output_fields.default.",
        file=sys.stderr,
    )
    return None


def _validate_profile_field_list(fields: list[str], *, source: str) -> list[str] | None:
    """Validate and normalize profile-provided field lists."""

    normalized = [str(field).strip().lower() for field in fields if str(field).strip()]
    unknown = [field for field in normalized if field not in _FIELD_REGISTRY]
    if unknown:
        print(
            f"Error: {source} defines unknown search field(s): {', '.join(unknown)}",
            file=sys.stderr,
        )
        print("Use --list-fields to see valid field keys.", file=sys.stderr)
        return None

    deduped: list[str] = []
    seen: set[str] = set()
    for field in normalized:
        if field in seen:
            continue
        seen.add(field)
        deduped.append(field)
    return deduped


def _row_for_result(r: SearchResult) -> dict[str, str]:
    """Build a row mapping containing every known registry key."""

    return {k: _FIELD_REGISTRY[k].extractor(r) for k in _FIELD_REGISTRY.keys()}


def _build_cache(args: argparse.Namespace) -> SearchCache:
    supplier_id = (getattr(args, "supplier", "") or "").strip().lower()
    if getattr(args, "clear_cache", False):
        DiskSearchCache.clear_provider(supplier_id)

    if getattr(args, "no_cache", False):
        return InMemorySearchCache()
    return DiskSearchCache(supplier_id)
    return DiskSearchCache(args.supplier)


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

    print("")
    print_table(rows, cols, terminal_width=get_terminal_width())
    print("")
    print(f"Found {len(results)} results.")


def _print_csv(results: list[SearchResult], *, fields: list[str], out: TextIO) -> None:
    # QUOTE_ALL ensures values like "0603" are written as "\"0603\"" so
    # spreadsheet apps treat them as text and preserve leading zeros.
    writer = csv.writer(out, quoting=csv.QUOTE_ALL)
    writer.writerow(_csv_headers(fields))

    for r in results:
        row = _csv_row_for_result(r, fields)
        writer.writerow(row)


def _csv_headers(fields: list[str]) -> list[str]:
    return [_FIELD_REGISTRY[f].column.header for f in fields]


def _csv_row_for_result(r: SearchResult, fields: list[str]) -> list[str]:
    full = _row_for_result(r)
    return [str(full.get(f, "")) for f in fields]
