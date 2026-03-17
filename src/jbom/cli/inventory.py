"""Inventory command - manage component inventory."""

from __future__ import annotations

import argparse
import copy
from typing import TYPE_CHECKING, Any
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

import shutil

from jbom.cli.output import (
    OutputDestination,
    OutputKind,
    OutputRefusedError,
    add_force_argument,
    open_output_text_file,
    resolve_output_destination,
)
from jbom.common.value_parsing import farad_to_eia, henry_to_eia, ohms_to_eia
from jbom.common.types import Component, InventoryItem
from jbom.common.options import GeneratorOptions
from jbom.cli.formatting import print_inventory_table
from jbom.services.inventory_reader import InventoryReader
from jbom.common.component_filters import apply_component_filters
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.services.project_inventory import ProjectInventoryGenerator
from jbom.services.schematic_reader import SchematicReader
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)

if TYPE_CHECKING:
    from jbom.config.suppliers import SupplierConfig
    from jbom.services.search.inventory_search_service import InventorySearchService

# Fields always present
# so the designer can fill them in or use "~" for heuristic defaults.
_NO_AGGREGATE_ALWAYS_FIELDS: list[str] = [
    "RowType",
    "ComponentID",
    # Identity — required for jbom annotate component routing
    "Project",
    "ProjectName",
    "UUID",
    "SourceFile",
    "Reference",
    "Category",
    "IPN",
    # Electro-mechanical attributes
    "Value",
    "Description",
    "Inductance",
    "Resistance",
    "Capacitance",
    "Package",
    "Color",
    "Tolerance",
    "Power",
    "Current",
    "Voltage",
    "Temperature Coefficient",
    "Voltage",
    "Wavelength",
    "mcd",
    "Symbol",
    "Footprint",
    "footprint_full",
    "symbol_name",
    "ki_keywords",
]

# Fields included only when at least one component carries a non-empty value.
_NO_AGGREGATE_CONDITIONAL_FIELDS: list[str] = [
    "SMD",
    "Type",
    "Form",
    "Pins",
    "Pitch",
    "Angle",
    "Manufacturer",
    "MFGPN",
    "LCSC",
    "Datasheet",
    "Keywords",
    "Height",
    "Manufacturer_Name",
    "Manufacturer_Part_Number",
    "Mouser Part Number",
    "Mouser Price/Stock",
    "Sim.Device",
    "Sim.Pins",
    "Supplier",
    "Name",
]


def register_command(subparsers) -> None:
    """Register inventory command with argument parser."""
    parser = subparsers.add_parser(
        "inventory",
        help="Generate component inventory from project",
        description="Generate component inventory from project",
    )

    # Project input as main positional argument — accepts one or more paths for batch mode
    parser.add_argument(
        "input",
        nargs="*",
        default=None,
        help=(
            "Path(s) to .kicad_sch file, project directory, or base name. "
            "Accepts multiple paths for batch mode (default: current directory). "
            "Multiple projects are merged with COMPONENT rows deduplicated on ComponentID."
        ),
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Output destination: omit for console table output, "
            "use 'console' for table, '-' for stdout, or a file path"
        ),
        default=None,
    )

    # Inventory merge options
    parser.add_argument(
        "--inventory",
        help="Path to existing inventory CSV file for merge operations (can be specified multiple times)",
        type=Path,
        action="append",
        dest="inventory_files",
    )

    parser.add_argument(
        "--filter-matches",
        action="store_true",
        help="Filter out components that match existing inventory items",
    )
    parser.add_argument(
        "--per-instance",
        action="store_true",
        dest="per_instance",
        help="Emit one inventory row per component instance with category sub-header rows",
    )
    # Deprecated alias — kept for backward compatibility.
    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        dest="per_instance",
        help=argparse.SUPPRESS,
    )

    # Safety options
    add_force_argument(parser)

    # Batch mode options
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        dest="stop_on_error",
        help="Abort batch processing on first project failure (default: continue and report)",
    )

    # Verbose mode
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    # Supplier enrichment options (optional; require search provider configuration)
    parser.add_argument(
        "--supplier",
        metavar="SUPPLIER_ID",
        action="append",
        default=None,
        help=(
            "Supplier ID for auto-populating supplier PN columns. "
            "Repeat to enrich from multiple suppliers in one run "
            "(e.g. --supplier lcsc --supplier mouser)."
        ),
    )
    parser.add_argument(
        "--api-key",
        metavar="KEY",
        default=None,
        help="API key for the supplier search provider (overrides env vars)",
    )
    parser.add_argument(
        "--limit",
        metavar="N",
        type=int,
        default=1,
        help=(
            "Maximum supplier candidates to apply per unmatched row. "
            "Use 1 (default) to apply best match only; use >1 to emit ranked alternatives."
        ),
    )

    parser.set_defaults(handler=handle_inventory)


def handle_inventory(args: argparse.Namespace) -> int:
    """Handle inventory command - generate inventory from project."""
    try:
        # Normalise input: None or empty list -> ["."] (current directory)
        raw_inputs: list[str] = args.input or ["."]

        if len(raw_inputs) > 1:
            return _handle_batch_inventory(raw_inputs, args)
        # Single-project: delegate to the existing handler unchanged
        return _handle_generate_inventory(raw_inputs[0], args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _load_components_from_path(
    input_path: str,
    args: argparse.Namespace,
    options,
) -> tuple[list[Component], str, Path] | None:
    """Resolve a project path, load and filter its components.

    Shared by both single-project and batch-mode inventory handlers.

    Returns:
        (components, project_name, project_directory) on success, or None on failure
        (error message already printed to stderr).
    """
    resolver = ProjectFileResolver(
        prefer_pcb=False, target_file_type="schematic", options=options
    )

    try:
        resolved_input = resolver.resolve_input(input_path)

        if not resolved_input.is_schematic:
            if args.verbose:
                print(
                    f"Note: Inventory generation requires a schematic file. "
                    f"Found {resolved_input.resolved_path.suffix} file, trying to find matching schematic.",
                    file=sys.stderr,
                )
            resolved_input = resolver.resolve_for_wrong_file_type(
                resolved_input, "schematic"
            )
            if args.verbose:
                print(
                    f"Using schematic: {resolved_input.resolved_path.name}",
                    file=sys.stderr,
                )

        schematic_file = resolved_input.resolved_path
        reader = SchematicReader(options)

        if resolved_input.project_context:
            hierarchical_files = resolved_input.get_hierarchical_files()
            if args.verbose and len(hierarchical_files) > 1:
                print(
                    f"Processing hierarchical design with {len(hierarchical_files)} schematic files",
                    file=sys.stderr,
                )
            components = []
            for sch_file in hierarchical_files:
                if args.verbose:
                    print(f"Loading components from {sch_file.name}", file=sys.stderr)
                components.extend(reader.load_components(sch_file))
        else:
            components = reader.load_components(schematic_file)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

    if not components:
        print(
            "Error: No components found in project. "
            "Cannot create inventory from empty schematic.",
            file=sys.stderr,
        )
        return None

    components = apply_component_filters(
        components,
        {
            "exclude_dnp": True,
            "include_only_bom": True,
            "include_virtual_symbols": False,
        },
    )

    if not components:
        print(
            "Error: No real components found after filtering virtual symbols. "
            "Cannot create inventory from empty schematic.",
            file=sys.stderr,
        )
        return None

    if args.inventory_files or args.filter_matches:
        components = _filter_components_by_existing_inventory(
            components,
            inventory_files=args.inventory_files,
            filter_matches=args.filter_matches,
            verbose=args.verbose,
        )

    project_directory = (
        resolved_input.project_context.project_directory
        if resolved_input.project_context
        else schematic_file.parent
    )
    project_name = (
        resolved_input.project_context.project_base_name
        if resolved_input.project_context
        else project_directory.name
    )

    return components, project_name, project_directory


def _handle_batch_inventory(input_paths: list[str], args: argparse.Namespace) -> int:
    """Process multiple project paths, merge and deduplicate COMPONENT rows.

    Deduplication key: ``component_id`` (first-seen across projects wins).
    Field names are unioned across all projects so no data is lost.
    On per-project failure: continue by default; abort if ``--stop-on-error``.
    Prints a per-project summary at the end.
    """
    options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

    # Accumulate items and fields across all projects
    accumulated_items: list = []
    seen_component_ids: set[str] = set()
    all_field_names: set[str] = set()

    # Track per-project results for summary
    results: list[tuple[str, bool, str]] = []  # (path, success, message)

    for input_path in input_paths:
        if args.verbose:
            print(f"\nProcessing: {input_path}", file=sys.stderr)

        result = _load_components_from_path(input_path, args, options)
        if result is None:
            results.append((input_path, False, "failed to load components"))
            if args.stop_on_error:
                print(
                    f"Aborting batch: --stop-on-error set and '{input_path}' failed.",
                    file=sys.stderr,
                )
                _print_batch_summary(results)
                return 1
            continue

        components, project_name, _project_dir = result

        generator = ProjectInventoryGenerator(components)
        try:
            items, field_names = generator.load()
        except Exception as e:
            results.append((input_path, False, str(e)))
            print(
                f"Error generating inventory for '{input_path}': {e}", file=sys.stderr
            )
            if args.stop_on_error:
                _print_batch_summary(results)
                return 1
            continue

        # Deduplicate: first-seen component_id wins
        new_count = 0
        for item in items:
            cid = item.component_id
            if cid and cid not in seen_component_ids:
                seen_component_ids.add(cid)
                accumulated_items.append(item)
                new_count += 1
            elif not cid:
                # Items without a component_id are always included
                accumulated_items.append(item)
                new_count += 1

        all_field_names.update(field_names)
        results.append(
            (input_path, True, f"{len(items)} items ({new_count} unique added)")
        )
        if args.verbose:
            print(
                f"  {project_name}: {len(items)} items, {new_count} new after dedup",
                file=sys.stderr,
            )

    _print_batch_summary(results)

    # Require at least one successful project
    successful = [r for r in results if r[1]]
    if not successful:
        print("Error: No projects produced output.", file=sys.stderr)
        return 1

    if not accumulated_items:
        print(
            "Error: No inventory items collected across all projects.", file=sys.stderr
        )
        return 1

    # Produce a deterministic field order
    ordered_fields = _merge_field_names(all_field_names)

    # Supplier enrichment (batch path)
    supplier_services = _build_inventory_supplier_services(args)
    if supplier_services:
        accumulated_items, ordered_fields = _enrich_items_with_suppliers(
            accumulated_items,
            ordered_fields,
            supplier_services,
            limit=max(1, int(getattr(args, "limit", 1))),
            verbose=args.verbose,
        )

    return _output_inventory(
        accumulated_items, ordered_fields, args.output, args.force, args.verbose
    )


def _print_batch_summary(results: list[tuple[str, bool, str]]) -> None:
    """Print a per-project success/failure summary to stderr."""
    print("\nBatch inventory summary:", file=sys.stderr)
    for path, success, message in results:
        status = "OK " if success else "FAIL"
        print(f"  [{status}] {path}: {message}", file=sys.stderr)


def _merge_field_names(all_field_names: set[str]) -> list[str]:
    """Return a deterministic ordered field list from a union of field name sets.

    Canonical inventory fields appear first in a fixed order; any additional
    fields discovered across projects are appended alphabetically.
    """
    canonical_order = [
        "RowType",
        "ComponentID",
        "IPN",
        "Category",
        "Value",
        "Package",
        "Description",
        "Keywords",
        "Manufacturer",
        "MFGPN",
        "LCSC",
        "Datasheet",
        "Resistance",
        "Capacitance",
        "Inductance",
        "UUID",
        "footprint_full",
        "symbol_lib",
        "symbol_name",
        "ki_keywords",
    ]
    ordered: list[str] = []
    seen: set[str] = set()
    for field in canonical_order:
        if field in all_field_names:
            ordered.append(field)
            seen.add(field)
    for field in sorted(all_field_names - seen):
        ordered.append(field)
    return ordered


def _normalize_supplier_ids(raw_suppliers: Any) -> list[str]:
    """Normalize and de-duplicate supplier IDs while preserving input order."""

    if raw_suppliers is None:
        return []

    if isinstance(raw_suppliers, str):
        candidates = [raw_suppliers]
    elif isinstance(raw_suppliers, list):
        candidates = [str(value) for value in raw_suppliers]
    else:
        candidates = [str(raw_suppliers)]

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        supplier_id = candidate.strip().lower()
        if not supplier_id or supplier_id in seen:
            continue
        seen.add(supplier_id)
        normalized.append(supplier_id)

    return normalized


def _build_inventory_supplier_services(
    args: argparse.Namespace,
) -> "list[tuple[InventorySearchService, SupplierConfig, str]]":
    """Build ordered supplier search services from CLI args.

    Returns a list of (service, supplier_config, supplier_id) tuples preserving
    ``--supplier`` order.
    """
    supplier_ids = _normalize_supplier_ids(getattr(args, "supplier", None))
    if not supplier_ids:
        return []

    api_key = getattr(args, "api_key", None)
    resolved_services: list[tuple[InventorySearchService, SupplierConfig, str]] = []

    try:
        from jbom.config.suppliers import resolve_supplier_by_id
        from jbom.services.search.provider_factory import create_search_provider
        from jbom.services.search.inventory_search_service import InventorySearchService

        for supplier_id in supplier_ids:
            supplier_config = resolve_supplier_by_id(supplier_id)
            if supplier_config is None:
                print(f"Error: Unknown supplier '{supplier_id}'", file=sys.stderr)
                continue

            provider = create_search_provider(
                supplier_id,
                api_key=api_key,
                cache=None,  # default DiskSearchCache
            )
            verbose = getattr(args, "verbose", False)
            service = InventorySearchService(
                provider, request_delay_seconds=0.2, verbose=verbose
            )
            resolved_services.append((service, supplier_config, supplier_id))

        return resolved_services
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return []


def _supplier_part_number(
    item: "InventoryItem", *, supplier_column: str, is_lcsc: bool
) -> str:
    """Return the normalized PN value for this supplier from one inventory row."""

    if is_lcsc:
        return (item.lcsc or "").strip()
    return str((item.raw_data or {}).get(supplier_column, "")).strip()


def _has_any_target_supplier_pn(
    item: "InventoryItem",
    supplier_services: "list[tuple[InventorySearchService, SupplierConfig, str]]",
) -> bool:
    """Return True if row already has a PN for any target supplier."""

    for _service, supplier_config, supplier_id in supplier_services:
        if _supplier_part_number(
            item,
            supplier_column=supplier_config.inventory_column,
            is_lcsc=(supplier_id == "lcsc"),
        ):
            return True
    return False


def _supplier_item_key(
    item: "InventoryItem", *, supplier_column: str, is_lcsc: bool
) -> tuple[str, str, str]:
    """Return a stable de-duplication key for one supplier-assigned row."""

    pn = _supplier_part_number(item, supplier_column=supplier_column, is_lcsc=is_lcsc)
    identity = (
        (item.ipn or "").strip()
        or (item.component_id or "").strip()
        or f"{(item.category or '').strip()}|{(item.value or '').strip()}|{(item.package or '').strip()}"
    )
    return identity, supplier_column, pn


def _extract_explicit_priority(item: "InventoryItem") -> int | None:
    """Return explicit row priority from raw inventory data, when present."""

    raw_priority = str((item.raw_data or {}).get("Priority", "")).strip()
    if not raw_priority:
        return None
    try:
        value = int(raw_priority)
    except ValueError:
        return None
    return value if value > 0 else None


def _build_next_priority_by_ipn(items: "list[InventoryItem]") -> dict[str, int]:
    """Return per-IPN next priority counters based on explicit inventory values."""

    max_priority_by_ipn: dict[str, int] = {}
    for item in items:
        ipn = (item.ipn or "").strip()
        if not ipn:
            continue
        explicit_priority = _extract_explicit_priority(item)
        if explicit_priority is None:
            continue
        max_priority_by_ipn[ipn] = max(
            explicit_priority, max_priority_by_ipn.get(ipn, 0)
        )

    return {
        ipn: (max_priority + 1) for ipn, max_priority in max_priority_by_ipn.items()
    }


def _assign_next_priority(
    item: "InventoryItem", *, next_priority_by_ipn: dict[str, int]
) -> bool:
    """Assign the next global per-IPN priority to an added row.

    Returns True when a priority value was assigned.
    """

    ipn = (item.ipn or "").strip()
    if not ipn:
        return False

    next_priority = next_priority_by_ipn.get(ipn, 1)
    if item.raw_data is None:
        item.raw_data = {}
    item.raw_data["Priority"] = str(next_priority)
    item.priority = next_priority
    next_priority_by_ipn[ipn] = next_priority + 1
    return True


def _enrich_items_with_suppliers(
    items: "list[InventoryItem]",
    field_names: list[str],
    supplier_services: "list[tuple[InventorySearchService, SupplierConfig, str]]",
    *,
    limit: int = 1,
    verbose: bool = False,
) -> "tuple[list[InventoryItem], list[str]]":
    """Apply supplier enrichment for one or more suppliers.

    Multi-supplier mode is additive: original rows are preserved and supplier-
    specific rows are appended for discovered candidates.
    """

    if not supplier_services:
        return items, field_names

    if len(supplier_services) == 1:
        service, supplier_config, supplier_id = supplier_services[0]
        return _enrich_items_with_supplier(
            items,
            field_names,
            service,
            supplier_config,
            supplier_id,
            limit=limit,
            verbose=verbose,
        )

    candidate_limit = max(1, int(limit))
    base_items = list(items)
    working_field_names = list(field_names)
    added_items: list[InventoryItem] = []

    seed_items = [
        item
        for item in base_items
        if (item.row_type or "ITEM").strip().upper() in {"ITEM", "COMPONENT"}
        and not _has_any_target_supplier_pn(item, supplier_services)
    ]

    if not seed_items:
        return base_items, working_field_names

    next_priority_by_ipn = _build_next_priority_by_ipn(base_items)
    seen_keys: set[tuple[str, str, str]] = set()

    for base_item in base_items:
        for _service, supplier_config, supplier_id in supplier_services:
            key = _supplier_item_key(
                base_item,
                supplier_column=supplier_config.inventory_column,
                is_lcsc=(supplier_id == "lcsc"),
            )
            if key[-1]:
                seen_keys.add(key)

    priority_assigned = False
    for service, supplier_config, supplier_id in supplier_services:
        supplier_seed = copy.deepcopy(seed_items)
        enriched_items, working_field_names = _enrich_items_with_supplier(
            supplier_seed,
            working_field_names,
            service,
            supplier_config,
            supplier_id,
            limit=candidate_limit,
            verbose=verbose,
        )
        supplier_column = supplier_config.inventory_column
        is_lcsc = supplier_id == "lcsc"

        for enriched_item in enriched_items:
            supplier_pn = _supplier_part_number(
                enriched_item,
                supplier_column=supplier_column,
                is_lcsc=is_lcsc,
            )
            if not supplier_pn:
                continue

            key = _supplier_item_key(
                enriched_item,
                supplier_column=supplier_column,
                is_lcsc=is_lcsc,
            )
            if key in seen_keys:
                continue

            priority_assigned = (
                _assign_next_priority(
                    enriched_item, next_priority_by_ipn=next_priority_by_ipn
                )
                or priority_assigned
            )
            added_items.append(enriched_item)
            seen_keys.add(key)

    if priority_assigned and "Priority" not in working_field_names:
        working_field_names = list(working_field_names) + ["Priority"]

    if not added_items:
        return base_items, working_field_names
    return base_items + added_items, working_field_names


def _enrich_items_with_supplier(
    items: "list[InventoryItem]",
    field_names: list[str],
    service: "InventorySearchService",
    supplier_config: "SupplierConfig",
    supplier_id: str,
    *,
    limit: int = 1,
    verbose: bool = False,
) -> "tuple[list[InventoryItem], list[str]]":
    """Auto-populate supplier PN column for items that lack one.

    Skips items that already carry a PN for the target supplier.  After search,
    backfills ``manufacturer`` and ``mfgpn`` when blank.

    Args:
        items: All inventory items (ITEM rows only are enriched).
        field_names: Current ordered field list — extended with the supplier
            column when not already present.
        service: Instantiated :class:`InventorySearchService`.
        supplier_config: Resolved :class:`SupplierConfig` for the supplier.
        supplier_id: Normalized supplier ID string.
        limit: Number of ranked candidates to emit per row when available.
            ``1`` applies only the top result (default behavior).
            ``>1`` emits up to ``limit`` ranked alternatives.
        verbose: When True, progress is printed to stderr.

    Returns:
        Updated ``(items, field_names)`` pair.
    """
    from jbom.services.search.inventory_search_service import InventorySearchService

    col = supplier_config.inventory_column
    is_lcsc = supplier_id == "lcsc"
    candidate_limit = max(1, int(limit))

    # Ensure supplier column is present in field list.
    if col not in field_names:
        field_names = list(field_names) + [col]
    if candidate_limit > 1 and "Priority" not in field_names:
        field_names = list(field_names) + ["Priority"]

    # Enrich both ITEM rows (inventory catalog) and COMPONENT rows (schematic-generated).
    item_rows = [
        i
        for i in items
        if (i.row_type or "ITEM").strip().upper() in {"ITEM", "COMPONENT"}
    ]
    needs_pn: list[InventoryItem] = []
    for item in item_rows:
        if is_lcsc:
            existing = (item.lcsc or "").strip()
        else:
            existing = str((item.raw_data or {}).get(col, "")).strip()
        if not existing:
            needs_pn.append(item)

    if not needs_pn:
        return items, field_names

    searchable = InventorySearchService.filter_searchable_items(
        needs_pn, categories=None
    )
    if not searchable:
        return items, field_names

    if verbose:
        print(
            f"Enriching {len(searchable)} item(s) with supplier PN ({supplier_id!r})...",
            file=sys.stderr,
        )

    records = service.search(searchable)
    records_by_item_id = {id(record.inventory_item): record for record in records}
    needs_pn_ids = {id(item) for item in needs_pn}

    enriched_items: list[InventoryItem] = []
    for item in items:
        item_id = id(item)
        if item_id not in needs_pn_ids:
            enriched_items.append(item)
            continue

        record = records_by_item_id.get(item_id)
        if record is None or not record.candidates:
            if candidate_limit > 1:
                if item.raw_data is None:
                    item.raw_data = {}
                item.raw_data.setdefault("Notes", "No supplier matches found")
                if "Notes" not in field_names:
                    field_names = list(field_names) + ["Notes"]
            enriched_items.append(item)
            continue

        candidates = record.candidates[:candidate_limit]
        if candidate_limit == 1:
            _apply_supplier_candidate_to_item(
                item=item,
                supplier_column=col,
                is_lcsc=is_lcsc,
                candidate=candidates[0].result,
            )
            if verbose:
                applied_pn = (
                    item.lcsc
                    if is_lcsc
                    else str((item.raw_data or {}).get(col, "")).strip()
                )
                print(f"  {item.ipn}: set {col}={applied_pn!r}", file=sys.stderr)
            enriched_items.append(item)
            continue

        emitted_any = False
        for rank, candidate in enumerate(candidates, start=1):
            distributor_pn = candidate.result.distributor_part_number or ""
            if not distributor_pn:
                continue
            ranked_item = copy.deepcopy(item)
            _apply_supplier_candidate_to_item(
                item=ranked_item,
                supplier_column=col,
                is_lcsc=is_lcsc,
                candidate=candidate.result,
            )
            if ranked_item.raw_data is None:
                ranked_item.raw_data = {}
            ranked_item.raw_data["Priority"] = str(rank)
            ranked_item.priority = rank
            enriched_items.append(ranked_item)
            emitted_any = True
            if verbose:
                print(
                    f"  {ranked_item.ipn}: candidate {rank} {col}={distributor_pn!r}",
                    file=sys.stderr,
                )

        if not emitted_any:
            if candidate_limit > 1:
                if item.raw_data is None:
                    item.raw_data = {}
                item.raw_data.setdefault("Notes", "No supplier matches found")
                if "Notes" not in field_names:
                    field_names = list(field_names) + ["Notes"]
            enriched_items.append(item)

    return enriched_items, field_names


def _apply_supplier_candidate_to_item(
    *,
    item: InventoryItem,
    supplier_column: str,
    is_lcsc: bool,
    candidate: Any,
) -> None:
    """Apply one supplier candidate result onto an inventory item."""
    pn = candidate.distributor_part_number or ""
    if is_lcsc:
        item.lcsc = pn
    else:
        if item.raw_data is None:
            item.raw_data = {}
        item.raw_data[supplier_column] = pn
    if not (item.manufacturer or "").strip() and candidate.manufacturer:
        item.manufacturer = candidate.manufacturer
    if not (item.mfgpn or "").strip() and candidate.mpn:
        item.mfgpn = candidate.mpn


def _handle_generate_inventory(input_path: str, args: argparse.Namespace) -> int:
    """Generate inventory from project components with project-centric input resolution.

    Output destination handling (following BOM command pattern):
    - None (default): print formatted table to stdout
    - "console": pretty print table to stdout
    - "-": write CSV format to stdout
    - otherwise: treat as a file path
    """
    options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

    result = _load_components_from_path(input_path, args, options)
    if result is None:
        return 1

    components, project_name, project_directory = result

    # Generate inventory
    generator = ProjectInventoryGenerator(components)

    if args.per_instance:
        rows, field_names = _generate_per_instance_inventory_rows(
            components,
            project_directory=project_directory,
            project_name=project_name,
        )
        return _output_inventory_rows(
            rows, field_names, args.output, args.force, args.verbose
        )

    inventory_items, field_names = generator.load()

    # Supplier enrichment (single-project path)
    supplier_services = _build_inventory_supplier_services(args)
    if supplier_services:
        inventory_items, field_names = _enrich_items_with_suppliers(
            inventory_items,
            list(field_names),
            supplier_services,
            limit=max(1, int(getattr(args, "limit", 1))),
            verbose=args.verbose,
        )

    # Handle output using same pattern as BOM command
    return _output_inventory(
        inventory_items, field_names, args.output, args.force, args.verbose
    )


def _generate_per_instance_inventory_rows(
    components: list[Component],
    project_directory: Path,
    project_name: str = "",
) -> tuple[list[dict[str, str]], list[str]]:
    """Generate per-instance inventory rows grouped by category with sub-headers.

    Emits one row per component instance (no aggregation).  Used by the
    ``--per-instance`` flag to support the ``jbom annotate`` back-annotation
    workflow, where ``SourceFile`` + ``UUID`` are needed to route IPNs back
    to the correct schematic component.

    Schema always includes identity and electro-mechanical attribute columns
    (``_NO_AGGREGATE_ALWAYS_FIELDS``).  Supply-chain and simulation columns are
    included only when at least one component carries a non-empty value for that
    field (``_NO_AGGREGATE_CONDITIONAL_FIELDS``).

    Identity semantics:
    - ``SourceFile`` (absolute path) + ``UUID`` is the canonical annotation routing key.
    - ``ProjectName`` and ``Project`` are cosmetic context only, never used for routing.
    - ``Reference`` is the human-readable designator (e.g. "R1", "C3").
    """

    generator = ProjectInventoryGenerator(components)
    inventory_items, base_field_names = generator.load_per_instance()

    project_value = str(project_directory.resolve())
    project_name_value = project_name or project_directory.name

    uuid_to_source: dict[str, str] = {}
    uuid_to_ref: dict[str, str] = {}
    for comp in components:
        if comp.uuid:
            uuid_to_source[comp.uuid] = (
                str(comp.source_file) if comp.source_file else ""
            )
            uuid_to_ref[comp.uuid] = comp.reference

    # Build raw rows using all candidate fields so conditional-field detection
    # can inspect actual values before the final field list is determined.
    candidate_fields: list[str] = list(
        dict.fromkeys(
            _NO_AGGREGATE_ALWAYS_FIELDS
            + _NO_AGGREGATE_CONDITIONAL_FIELDS
            + list(base_field_names)
        )
    )

    raw_rows: list[dict[str, str]] = []
    for item in inventory_items:
        row = _inventory_item_to_row(item, candidate_fields)
        row["Project"] = project_value
        row["ProjectName"] = project_name_value
        row["UUID"] = item.uuid
        row["SourceFile"] = uuid_to_source.get(item.uuid, "")
        row["Reference"] = uuid_to_ref.get(item.uuid, "")
        row["Category"] = item.category
        row["IPN"] = item.ipn
        raw_rows.append(row)

    # Determine final field order: always fields + conditional fields that have data.
    field_names = _build_no_aggregate_field_order(base_field_names, raw_rows)

    sorted_rows = sorted(
        raw_rows, key=lambda r: (r.get("Category", ""), r.get("UUID", ""))
    )

    grouped_rows: list[dict[str, str]] = []
    current_category = ""
    for row in sorted_rows:
        category = row.get("Category", "")
        if category != current_category:
            grouped_rows.append(_build_no_aggregate_subheader_row(field_names))
            current_category = category
        grouped_rows.append({fn: row.get(fn, "") for fn in field_names})

    return grouped_rows, field_names


def _build_no_aggregate_field_order(
    base_field_names: list[str],
    data_rows: list[dict[str, str]],
) -> list[str]:
    """Return deterministic field ordering for no-aggregate inventory output.

    Always-include fields appear first (even when every value is empty).
    Conditional fields follow only when at least one data row carries a
    non-empty value.  Any remaining fields from *base_field_names* that have
    data but are not in either list are appended at the end.
    """

    ordered: list[str] = list(_NO_AGGREGATE_ALWAYS_FIELDS)
    already: set[str] = set(ordered)

    def _has_data(field: str) -> bool:
        return any(row.get(field, "") for row in data_rows)

    for field in _NO_AGGREGATE_CONDITIONAL_FIELDS:
        if field not in already and _has_data(field):
            ordered.append(field)
            already.add(field)

    # Append any extra fields from the KiCad base data not already covered.
    for field in base_field_names:
        if field not in already and _has_data(field):
            ordered.append(field)
            already.add(field)

    return ordered


def _build_no_aggregate_subheader_row(field_names: list[str]) -> dict[str, str]:
    """Build minimal deterministic sub-header marker row for no-aggregate output.

    Identity columns (Project … Reference) are marked with their field name as
    a sentinel.  IPN is marked optional.  All other columns are left empty so
    the designer can fill in component-specific values.
    """

    row = {field_name: "" for field_name in field_names}
    row["Project"] = "Project"
    row["RowType"] = "COMPONENT"
    row["ComponentID"] = "ComponentID"
    row["ProjectName"] = "ProjectName"
    row["UUID"] = "UUID"
    row["SourceFile"] = "SourceFile"
    row["Reference"] = "Reference"
    row["Category"] = "Category"
    row["IPN"] = "(Optional)\nIPN"
    row["Value"] = "Value"
    row["Package"] = "Package"
    return row


def _filter_components_by_existing_inventory(
    components: list[Component],
    *,
    inventory_files: list[Path] | None,
    filter_matches: bool,
    verbose: bool,
) -> list[Component]:
    """Filter project components based on whether they match an existing inventory.

    This is used by `jbom inventory` to show only "new" components not already
    represented in an inventory file.

    Args:
        components: Components loaded from schematic(s).
        inventory_files: Inventory CSV file paths.
        filter_matches: If True, exclude components that match (show only new).
        verbose: Emit diagnostic match info to stderr.

    Returns:
        Filtered component list.
    """
    inventory_files = inventory_files or []
    if not inventory_files:
        if filter_matches:
            print(
                "Error: --filter-matches requires --inventory file(s)",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return components

    # Load and merge inventory files (first occurrence of each IPN wins).
    merged_inventory: list[InventoryItem] = []
    seen_ipns: set[str] = set()

    if verbose:
        print(
            f"Loading {len(inventory_files)} inventory file(s):",
            file=sys.stderr,
        )

    missing_file_detected = False
    total_files_loaded = 0

    for i, inventory_file in enumerate(inventory_files):
        if not inventory_file.exists():
            missing_file_detected = True
            print(
                f"Error: Inventory file not found: {inventory_file}",
                file=sys.stderr,
            )
            continue

        try:
            reader = InventoryReader(inventory_file)
            file_inventory, _ = reader.load()

            added_count = 0
            for item in file_inventory:
                if item.ipn not in seen_ipns:
                    merged_inventory.append(item)
                    seen_ipns.add(item.ipn)
                    added_count += 1

            total_files_loaded += 1
            if verbose:
                file_desc = f"file {i + 1}"
                print(
                    f"  {file_desc}: {inventory_file} ({added_count}/{len(file_inventory)} items added)",
                    file=sys.stderr,
                )

        except Exception as e:
            print(f"Error loading {inventory_file}: {e}", file=sys.stderr)

    if missing_file_detected:
        raise SystemExit(1)

    if not merged_inventory:
        print("Error: No inventory items loaded from any file", file=sys.stderr)
        raise SystemExit(1)

    if verbose:
        print(
            f"Merged inventory: {len(merged_inventory)} total items from {total_files_loaded} file(s)",
            file=sys.stderr,
        )

    matcher = SophisticatedInventoryMatcher(MatchingOptions(include_debug_info=verbose))

    filtered_components: list[Component] = []
    matched_count = 0

    for comp in components:
        matches = matcher.find_matches(comp, merged_inventory)

        if matches:
            matched_count += 1
            if verbose:
                print(
                    f"Matched {comp.reference}: {matches[0].debug_info}",
                    file=sys.stderr,
                )

            if not filter_matches:
                filtered_components.append(comp)
        else:
            if verbose:
                print(
                    f"No match for {comp.reference} ({comp.lib_id} {comp.value} {comp.footprint})",
                    file=sys.stderr,
                )
            filtered_components.append(comp)

    if verbose:
        total = len(components)
        filtered = len(filtered_components)
        action = "kept" if filter_matches else "included"
        print(
            f"\nInventory filtering: {matched_count}/{total} matched, {filtered} {action}",
            file=sys.stderr,
        )

    return filtered_components


def _output_inventory(
    inventory_items, field_names, output, force: bool = False, verbose: bool = False
) -> int:
    """Output inventory data in the requested format.

    Defaults:
    - output omitted => print formatted table to stdout
    - output == "console" => formatted table to stdout
    - output == "-" => CSV to stdout
    - otherwise => treat as file path with safety checks
    """

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(OutputKind.CONSOLE),
    )

    if dest.kind == OutputKind.CONSOLE:
        _print_console_table(inventory_items, field_names)
        return 0

    if dest.kind == OutputKind.STDOUT:
        _print_csv(inventory_items, field_names, out=sys.stdout)
        return 0

    if not dest.path:
        raise ValueError("Internal error: file output selected but no path provided")

    output_path = dest.path
    refused = (
        f"Error: Output file '{output_path}' already exists. Use --force to overwrite."
    )

    def _backup(p: Path) -> Path | None:
        backup_path = _create_backup(p, verbose)
        if backup_path and verbose:
            print(f"Created backup: {backup_path}", file=sys.stderr)
        return backup_path

    try:
        with open_output_text_file(
            output_path,
            force=force,
            refused_message=refused,
            make_backup=_backup,
        ) as f:
            _write_csv(inventory_items, field_names, out=f)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Generated inventory with {len(inventory_items)} items written to {output_path}"
    )
    return 0


def _output_inventory_rows(
    rows: list[dict[str, str]],
    field_names: list[str],
    output,
    force: bool = False,
    verbose: bool = False,
) -> int:
    """Output pre-built inventory row dictionaries in the requested format."""

    dest = resolve_output_destination(
        output,
        default_destination=OutputDestination(OutputKind.CONSOLE),
    )

    if dest.kind == OutputKind.CONSOLE:
        print_inventory_table(rows, field_names)
        print(f"\nGenerated inventory with {_count_data_rows(rows)} items")
        return 0

    if dest.kind == OutputKind.STDOUT:
        _write_csv_rows(rows, field_names, out=sys.stdout)
        return 0

    if not dest.path:
        raise ValueError("Internal error: file output selected but no path provided")

    output_path = dest.path
    refused = (
        f"Error: Output file '{output_path}' already exists. Use --force to overwrite."
    )

    def _backup(path: Path) -> Path | None:
        backup_path = _create_backup(path, verbose)
        if backup_path and verbose:
            print(f"Created backup: {backup_path}", file=sys.stderr)
        return backup_path

    try:
        with open_output_text_file(
            output_path,
            force=force,
            refused_message=refused,
            make_backup=_backup,
        ) as handle:
            _write_csv_rows(rows, field_names, out=handle)
    except OutputRefusedError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Generated inventory with {_count_data_rows(rows)} items written to {output_path}"
    )
    return 0


def _count_data_rows(rows: list[dict[str, str]]) -> int:
    """Count inventory data rows excluding no-aggregate sentinel sub-headers."""

    return sum(1 for row in rows if row.get("Project", "") != "Project")


def _create_backup(file_path: Path, verbose: bool = False) -> Path:
    """Create a timestamped backup of an existing file.

    Args:
        file_path: Path to file to backup
        verbose: Enable verbose output

    Returns:
        Path to created backup file, or None if backup failed
    """
    if not file_path.exists():
        return None

    # Generate timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_name(
        f"{file_path.stem}.backup.{timestamp}{file_path.suffix}"
    )

    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except Exception as e:
        if verbose:
            print(f"Warning: Failed to create backup: {e}", file=sys.stderr)
        return None


def _print_console_table(inventory_items, field_names) -> None:
    """Print inventory as formatted console table."""
    # Convert inventory items to dict format for print_inventory_table
    item_dicts = []
    for item in inventory_items:
        row = {
            "IPN": item.ipn,
            "Category": item.category,
            "Value": item.value,
            "Description": item.description,
            "Package": item.package,
            "Manufacturer": item.manufacturer,
            "MFGPN": item.mfgpn,
            "LCSC": item.lcsc,
            "Datasheet": item.datasheet,
            "UUID": item.uuid,
        }
        # Add any extra fields from component properties
        for field in field_names:
            if (
                field not in row
                and hasattr(item, "raw_data")
                and field in item.raw_data
            ):
                row[field] = item.raw_data[field]
        item_dicts.append(row)

    # Use the common formatting utility
    print_inventory_table(item_dicts, field_names)
    print(f"\nGenerated inventory with {len(inventory_items)} items")


def _print_csv(inventory_items, field_names, *, out: TextIO) -> None:
    """Print inventory as CSV to a file-like object."""
    rows = [_inventory_item_to_row(item, field_names) for item in inventory_items]
    _write_csv_rows(rows, field_names, out=out)


def _write_csv(inventory_items, field_names, *, out: TextIO) -> None:
    """Write inventory as CSV to a file-like object."""
    rows = [_inventory_item_to_row(item, field_names) for item in inventory_items]
    _write_csv_rows(rows, field_names, out=out)


def _inventory_item_to_row(
    item: InventoryItem, field_names: list[str]
) -> dict[str, str]:
    """Convert an InventoryItem to a CSV row dictionary."""

    row = {
        "RowType": item.row_type,
        "ComponentID": item.component_id,
        "IPN": item.ipn,
        "Category": item.category,
        "Value": item.value,
        "Description": item.description,
        "Package": item.package,
        "Manufacturer": item.manufacturer,
        "MFGPN": item.mfgpn,
        "LCSC": item.lcsc,
        "Datasheet": item.datasheet,
        "UUID": item.uuid,
        "Priority": str((item.raw_data or {}).get("Priority", "")),
        "Notes": str((item.raw_data or {}).get("Notes", "")),
    }

    # Write canonical EIA text for typed parametric fields, overriding the
    # raw schematic strings so "1.0uF" and "1uF" are both rendered as "1uF".
    if item.resistance is not None:
        row["Resistance"] = ohms_to_eia(item.resistance)
    if item.capacitance is not None:
        row["Capacitance"] = farad_to_eia(item.capacitance)
    if item.inductance is not None:
        row["Inductance"] = henry_to_eia(item.inductance)

    for field_name in field_names:
        if (
            field_name not in row
            and hasattr(item, "raw_data")
            and field_name in item.raw_data
        ):
            row[field_name] = item.raw_data[field_name]

    for field_name in field_names:
        row.setdefault(field_name, "")

    return row


def _write_csv_rows(
    rows: list[dict[str, str]], field_names: list[str], *, out: TextIO
) -> None:
    """Write row dictionaries as CSV using the provided field order."""

    # QUOTE_ALL ensures values like "0603" are written as "\"0603\"" so
    # spreadsheet apps treat them as text and preserve leading zeros.
    writer = csv.DictWriter(
        out, fieldnames=field_names, extrasaction="ignore", quoting=csv.QUOTE_ALL
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
