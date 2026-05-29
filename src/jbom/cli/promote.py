"""Promote command - materialize supplier exports into canonical inventory shape."""

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
from jbom.cli.supplier_args import (
    parse_supplier_api_key_args as _parse_supplier_api_key_args,
    resolve_supplier_api_key as _resolve_supplier_api_key,
)
from jbom.config.suppliers import get_available_suppliers
from jbom.services.promote.source_adapters import (
    detect_source_format,
    select_adapter,
)
from jbom.services.promote.workflow import (
    PromotionResult,
    PromotionStats,
    promote_rows,
)

_PROMOTE_SUPPLIER_CONTEXT_COLUMN = "SupplierContext"
_PROMOTE_SUPPLIER_OVERLAP_ERROR = (
    "Multiple supplier contexts for `jbom promote` are not supported yet "
    "(tracked by #324)."
)


def register_command(subparsers) -> None:
    """Register the ``promote`` command."""

    parser = subparsers.add_parser(
        "promote",
        help="Promote supplier export CSV into canonical inventory shape",
        description=(
            "Promote a supplier-export CSV into canonical jBOM inventory rows. "
            "Parses descriptions and derives identity from each row.  When a "
            "supplier context is selected (--supplier or --jlc), the supplier's "
            "catalog is queried to enrich the canonical fields."
        ),
    )
    parser.add_argument(
        "source_inventory",
        help="Path to supplier-export inventory CSV",
    )
    parser.add_argument(
        "--supplier",
        metavar="SUPPLIER_ID",
        action="append",
        default=None,
        choices=get_available_suppliers(),
        type=lambda value: str(value).strip().lower(),
        help=(
            "Supplier context for promotion. Repeat is allowed only when every "
            "value resolves to the same supplier."
        ),
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY_OR_SUPPLIER_KEY",
        action="append",
        default=None,
        help=(
            "API key for supplier search providers. "
            "Use KEY for single-supplier runs, or SUPPLIER_ID=KEY for "
            "supplier-scoped keys."
        ),
    )
    parser.add_argument(
        "--jlc",
        action="store_true",
        help="Shortcut for --supplier lcsc",
    )
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Output destination: omit for default <input>.promoted.csv, "
            "use 'console' or '-' for stdout CSV, or provide a file path"
        ),
    )
    add_force_argument(parser)
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose diagnostics",
    )
    parser.set_defaults(handler=handle_promote)


def handle_promote(args: argparse.Namespace) -> int:
    """Handle ``jbom promote`` command."""

    source_path = Path(args.source_inventory)
    if not source_path.exists():
        print(f"Error: Source inventory file not found: {source_path}", file=sys.stderr)
        return 1

    try:
        supplier_context = _resolve_promote_supplier_context(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    try:
        _resolve_promote_api_key(args, supplier_context=supplier_context)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        rows, source_fieldnames = _load_inventory_rows(source_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    adapter = select_adapter(detect_source_format(source_fieldnames))

    # Supplier-search is implied by an explicit supplier context: when the user
    # passes --supplier <id> or --jlc, the workflow attempts catalog enrichment
    # through that supplier.  When neither flag is provided, the implicit
    # 'generic' context carries no catalog and no enrichment is attempted.
    search_service = None
    if _has_explicit_supplier_context(args):
        try:
            search_service = _build_promote_search_service(
                args, supplier_context=supplier_context
            )
        except Exception as exc:  # pragma: no cover - defensive: bad provider config
            if getattr(args, "verbose", False):
                print(
                    f"Note: supplier provider unavailable, continuing without "
                    f"enrichment ({exc})",
                    file=sys.stderr,
                )
            search_service = None

    supplier_label = _supplier_label_for_context(supplier_context)

    result: PromotionResult = promote_rows(
        rows,
        adapter=adapter,
        supplier_context=supplier_context,
        supplier_label=supplier_label,
        search_service=search_service,
        verbose=bool(getattr(args, "verbose", False)),
    )

    _print_summary(result.stats, enriched=search_service is not None)

    output_path = _default_output_path(source_path)
    destination = resolve_output_destination(
        getattr(args, "output", None),
        default_destination=OutputDestination(OutputKind.FILE, path=output_path),
    )
    return _write_promoted_rows(
        result,
        destination=destination,
        force=bool(getattr(args, "force", False)),
    )


def _has_explicit_supplier_context(args: argparse.Namespace) -> bool:
    """Return True when the user explicitly selected a supplier context."""

    if bool(getattr(args, "jlc", False)):
        return True
    raw = getattr(args, "supplier", None)
    if not raw:
        return False
    if isinstance(raw, str):
        return bool(raw.strip())
    return any(str(value).strip() for value in raw)


def _resolve_promote_supplier_context(args: argparse.Namespace) -> str:
    """Resolve the single effective supplier context for promotion."""

    supplier_values = _normalize_supplier_values(getattr(args, "supplier", None))
    jlc_enabled = bool(getattr(args, "jlc", False))

    if jlc_enabled and supplier_values:
        # TODO(#324): Support explicit multi-supplier context composition.
        raise ValueError(_PROMOTE_SUPPLIER_OVERLAP_ERROR)

    if len(supplier_values) > 1:
        # TODO(#324): Support deterministic overlap semantics for multiple contexts.
        raise ValueError(_PROMOTE_SUPPLIER_OVERLAP_ERROR)

    if jlc_enabled:
        return "lcsc"

    if supplier_values:
        return supplier_values[0]

    return "generic"


def _normalize_supplier_values(raw_values: list[str] | None) -> list[str]:
    """Normalize and de-duplicate supplier argument values preserving order."""

    if not raw_values:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        supplier_id = str(raw_value).strip().lower()
        if not supplier_id:
            continue
        if supplier_id in seen:
            continue
        seen.add(supplier_id)
        normalized.append(supplier_id)
    return normalized


def _resolve_promote_api_key(
    args: argparse.Namespace,
    *,
    supplier_context: str,
) -> str | None:
    """Resolve optional API key for the effective promote supplier context."""

    scoped_api_keys, default_api_key = _parse_supplier_api_key_args(
        getattr(args, "api_key", None),
        supplier_ids=[supplier_context],
    )
    return _resolve_supplier_api_key(
        supplier_context,
        scoped_api_keys=scoped_api_keys,
        default_api_key=default_api_key,
    )


def _load_inventory_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Load a CSV file as normalized row dictionaries."""

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(
                    f"Source inventory file has no CSV headers: {path}"
                ) from None

            fieldnames = [str(name).strip() for name in reader.fieldnames if name]
            rows: list[dict[str, str]] = []
            for row in reader:
                normalized_row = {
                    field: str((row or {}).get(field, "") or "") for field in fieldnames
                }
                rows.append(normalized_row)
    except OSError as exc:
        raise ValueError(f"Unable to read source inventory file {path}: {exc}") from exc

    return rows, fieldnames


# ---------------------------------------------------------------------------
# Supplier enrichment helpers
# ---------------------------------------------------------------------------


def _supplier_label_for_context(supplier_context: str) -> str:
    """Return the canonical supplier label for *supplier_context*."""

    try:
        from jbom.config.suppliers import resolve_supplier_by_id

        cfg = resolve_supplier_by_id(supplier_context)
        if cfg and getattr(cfg, "supplier_label", ""):
            return cfg.supplier_label
    except Exception:
        pass
    return supplier_context


def _build_promote_search_service(
    args: argparse.Namespace,
    *,
    supplier_context: str,
):
    """Best-effort construct an InventorySearchService for enrichment.

    Returns ``None`` when the supplier provider is unavailable or unknown.
    """

    try:
        from jbom.config.suppliers import resolve_supplier_by_id
        from jbom.services.search.inventory_search_service import (
            InventorySearchService,
        )
        from jbom.services.search.provider_factory import create_search_provider
    except Exception:
        return None

    cfg = resolve_supplier_by_id(supplier_context)
    if cfg is None:
        return None

    scoped_api_keys, default_api_key = _parse_supplier_api_key_args(
        getattr(args, "api_key", None),
        supplier_ids=[supplier_context],
    )
    api_key = _resolve_supplier_api_key(
        supplier_context,
        scoped_api_keys=scoped_api_keys,
        default_api_key=default_api_key,
    )

    try:
        provider = create_search_provider(supplier_context, api_key=api_key, cache=None)
    except Exception:
        return None

    if not getattr(provider, "available", lambda: True)():
        return None

    return InventorySearchService(
        provider,
        request_delay_seconds=0.2,
        verbose=bool(getattr(args, "verbose", False)),
    )


# ---------------------------------------------------------------------------
# Output and reporting
# ---------------------------------------------------------------------------


def _print_summary(stats: PromotionStats, *, enriched: bool) -> None:
    """Print a one-line non-verbose run summary to stderr."""

    if stats.rows_total == 0:
        return
    parts: list[str] = [
        f"rows={stats.rows_total}",
        f"parsed={stats.rows_parsed}",
        f"value={stats.rows_with_canonical_value}",
    ]
    if enriched:
        parts.append(f"mpn_hit={stats.rows_enriched_mpn}")
        parts.append(f"search_hit={stats.rows_enriched_search}")
        parts.append(f"misses={stats.rows_enrichment_misses}")
    else:
        parts.append("enrich=skipped")
    print("Promote summary: " + " ".join(parts), file=sys.stderr)


def _default_output_path(source_path: Path) -> Path:
    """Return default output path for promote command."""

    if source_path.suffix:
        return source_path.with_name(f"{source_path.stem}.promoted{source_path.suffix}")
    return source_path.with_name(f"{source_path.name}.promoted.csv")


def _write_promoted_rows(
    result: PromotionResult,
    *,
    destination: OutputDestination,
    force: bool,
) -> int:
    """Write promoted rows to requested destination."""

    rows_for_csv = [
        _merge_row_with_extras(row.canonical, row.extras) for row in result.rows
    ]

    if destination.kind in {OutputKind.CONSOLE, OutputKind.STDOUT}:
        _write_csv_rows(rows_for_csv, result.fieldnames, out=sys.stdout)
        return 0

    if destination.path is None:
        raise ValueError("Internal error: output path required for file destination")

    output_path = destination.path
    refused = (
        f"Error: Output file '{output_path}' already exists. "
        "Use -F/--force to overwrite."
    )

    try:
        with open_output_text_file(
            output_path,
            force=force,
            refused_message=refused,
        ) as handle:
            _write_csv_rows(rows_for_csv, result.fieldnames, out=handle)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Promoted inventory written to {output_path}")
    return 0


def _merge_row_with_extras(
    canonical: dict[str, str], extras: dict[str, str]
) -> dict[str, str]:
    """Combine canonical fields and supplemental extras into a single CSV row."""

    merged: dict[str, str] = dict(canonical)
    for key, value in extras.items():
        merged.setdefault(key, value)
    return merged


def _write_csv_rows(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    *,
    out: TextIO,
) -> None:
    """Write CSV rows with deterministic quoting behavior."""

    writer = csv.DictWriter(
        out,
        fieldnames=fieldnames,
        extrasaction="ignore",
        quoting=csv.QUOTE_ALL,
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
