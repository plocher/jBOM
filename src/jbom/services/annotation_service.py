"""Services for inventory-driven schematic annotation and triage."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sexpdata

from jbom.common.sexp_parser import load_kicad_file, walk_nodes

_NORMALIZE_FIELD_MAP: dict[str, str] = {
    "V": "Voltage",
    "A": "Current",
    "W": "Power",
    "Amperage": "Current",
    "Wattage": "Power",
}


@dataclass(frozen=True)
class AnnotationChange:
    """Represents one proposed/applied schematic property change."""

    uuid: str
    field: str
    before: str
    after: str
    row_number: int


@dataclass(frozen=True)
class NormalizationChange:
    """One normalized property change on a symbol."""

    uuid: str
    source_field: str
    target_field: str
    value: str
    source_file: Path


@dataclass(frozen=True)
class NormalizationConflict:
    """Conflict that prevents safe normalization."""

    uuid: str
    target_field: str
    source_fields: tuple[str, ...]
    source_values: tuple[str, ...]
    source_file: Path


@dataclass
class NormalizationResult:
    """Result summary for property normalization execution."""

    dry_run: bool
    updated_components: int
    changes: list[NormalizationChange] = field(default_factory=list)
    conflicts: list[NormalizationConflict] = field(default_factory=list)


@dataclass(frozen=True)
class RepairsRow:
    """One ``Action=SET`` row parsed from an audit ``report.csv``."""

    check_type: str
    project_path: str
    ref_des: str
    uuid: str
    field_name: str
    approved_value: str


@dataclass
class RepairsAnnotationResult:
    """Result of applying repairs from an audit ``report.csv``.

    Attributes:
        dry_run: Whether changes were written or just simulated.
        applied: Number of ``Action=SET`` rows successfully applied.
        skipped: Number of rows with ``Action`` other than ``SET`` (ignored).
        failed: Number of ``Action=SET`` rows whose UUID was not found in any
            schematic.  A non-zero ``failed`` count produces exit-code 1.
        changes: Detailed per-field change records.
        errors: Human-readable error strings for failed rows.
    """

    dry_run: bool
    applied: int = 0
    skipped: int = 0
    failed: int = 0
    changes: list[AnnotationChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_schematic_properties(
    schematic_files: list[Path], *, dry_run: bool = False
) -> NormalizationResult:
    """Normalize alias property names (V/A/W, Amperage/Wattage) to canonical names.

    Conflict policy:
    - If alias and canonical fields coexist with different values, normalization
      is unsafe and no files are written.
    - If multiple aliases map to the same canonical field with differing values
      and canonical is absent, normalization is unsafe and no files are written.
    """

    schematics: dict[Path, list[Any]] = {}
    changes: list[NormalizationChange] = []
    conflicts: list[NormalizationConflict] = []
    changed_symbol_ids: set[tuple[Path, str]] = set()
    file_mutations: dict[Path, list[tuple[list[Any], str, str, str]]] = {}

    inverse_map: dict[str, list[str]] = {}
    for source, target in _NORMALIZE_FIELD_MAP.items():
        inverse_map.setdefault(target, []).append(source)

    for schematic_path in schematic_files:
        if not schematic_path.exists():
            continue
        schematic = load_kicad_file(schematic_path)
        schematics[schematic_path] = schematic
        file_mutations[schematic_path] = []

        for symbol in walk_nodes(schematic, "symbol"):
            symbol_uuid = _get_symbol_uuid(symbol)
            for target_field, source_fields in inverse_map.items():
                sources = [
                    src
                    for src in source_fields
                    if _find_property_node(symbol, src) is not None
                ]
                if not sources:
                    continue

                target_value = _get_property_value(symbol, target_field)
                source_values = {
                    src: _get_property_value(symbol, src) for src in sources
                }
                unique_source_values = sorted(set(source_values.values()))

                conflict = False
                if target_value and any(
                    value != target_value for value in source_values.values()
                ):
                    conflict = True
                if not target_value and len(unique_source_values) > 1:
                    conflict = True

                if conflict:
                    conflicts.append(
                        NormalizationConflict(
                            uuid=symbol_uuid,
                            target_field=target_field,
                            source_fields=tuple(sources),
                            source_values=tuple(source_values[src] for src in sources),
                            source_file=schematic_path,
                        )
                    )
                    continue

                chosen_value = target_value or source_values[sources[0]]
                for source in sources:
                    changes.append(
                        NormalizationChange(
                            uuid=symbol_uuid,
                            source_field=source,
                            target_field=target_field,
                            value=chosen_value,
                            source_file=schematic_path,
                        )
                    )
                    file_mutations[schematic_path].append(
                        (symbol, source, target_field, chosen_value)
                    )
                    changed_symbol_ids.add((schematic_path, symbol_uuid))

    if dry_run or conflicts:
        return NormalizationResult(
            dry_run=dry_run,
            updated_components=len(changed_symbol_ids),
            changes=changes,
            conflicts=conflicts,
        )

    for schematic_path, mutations in file_mutations.items():
        if not mutations:
            continue
        for symbol, source_field, target_field, chosen_value in mutations:
            if not _find_property_node(symbol, target_field):
                _set_property_value(symbol, target_field, chosen_value)
            _remove_property(symbol, source_field)
        schematic_path.write_text(
            sexpdata.dumps(schematics[schematic_path]), encoding="utf-8"
        )

    return NormalizationResult(
        dry_run=dry_run,
        updated_components=len(changed_symbol_ids),
        changes=changes,
        conflicts=conflicts,
    )


def annotate_from_repairs(
    repairs_path: Path,
    schematic_files: list[Path],
    *,
    dry_run: bool = False,
) -> RepairsAnnotationResult:
    """Apply ``Action=SET`` rows from an audit ``report.csv`` to schematic files.

    Workflow:
    1. Load *repairs_path* (audit ``report.csv``).
    2. Skip any row where ``Action`` is not ``'SET'``
       (blank / ``SKIP`` / ``IGNORE`` etc.) — counted as *skipped*.
    3. Parse updates from either:
       - legacy tall rows (``Field`` + ``ApprovedValue``), or
       - wide rows (``RowType=SUGGESTED`` + non-metadata suggestion columns).
       Skip silently when a row has no actionable updates.
    4. Build a UUID → (symbol, file-path) index across all *schematic_files*.
    5. For each actionable ``SET`` row, look up the UUID in the index and write
       one or more field updates to the matching symbol. A missing UUID is a
       **hard failure** (added to *errors*, counted as *failed*); processing
       continues for subsequent rows.
    6. Write modified schematic files (unless *dry_run*).

    Args:
        repairs_path: Path to the audit ``report.csv`` file.
        schematic_files: List of ``.kicad_sch`` paths that form the project
            hierarchy (typically obtained from
            :class:`~jbom.services.project_file_resolver.ProjectFileResolver`).
        dry_run: When ``True``, compute all changes but do not write any files.

    Returns:
        :class:`RepairsAnnotationResult` with counts and change details.
    """
    rows = _load_repairs_rows(repairs_path)

    # Compute project directories for multi-project filtering.
    project_dirs = {sch.parent.resolve() for sch in schematic_files if sch.exists()}

    # Build UUID → (symbol_node, schematic_path) index.
    uuid_to_location: dict[str, tuple[Any, Path]] = {}
    schematics_cache: dict[Path, Any] = {}
    load_warnings: list[str] = []

    for sch_path in schematic_files:
        if not sch_path.exists():
            load_warnings.append(f"Schematic file not found, skipping: {sch_path}")
            continue
        schematic = load_kicad_file(sch_path)
        schematics_cache[sch_path] = schematic
        for symbol in walk_nodes(schematic, "symbol"):
            symbol_uuid = _get_symbol_uuid(symbol)
            if symbol_uuid and symbol_uuid not in uuid_to_location:
                uuid_to_location[symbol_uuid] = (symbol, sch_path)

    result = RepairsAnnotationResult(dry_run=dry_run)
    result.errors.extend(load_warnings)
    changed_files: set[Path] = set()
    current_rows_by_uuid: dict[str, _RepairsRowRaw] = {}
    for loaded_row in rows:
        if _repairs_cell(loaded_row, "RowType").upper() != "CURRENT":
            continue
        current_uuid = _repairs_cell(loaded_row, "UUID")
        if current_uuid:
            current_rows_by_uuid[current_uuid] = loaded_row

    for row in rows:
        action = _repairs_cell(row, "Action").upper()
        if action != "SET":
            result.skipped += 1
            continue

        row_type = _repairs_cell(row, "RowType").upper()
        if row_type and row_type != "SUGGESTED":
            result.skipped += 1
            continue
        row_field_name = _repairs_cell(row, "Field")
        row_approved_value = _repairs_cell(row, "ApprovedValue")
        has_legacy_columns = bool(row_field_name or row_approved_value)
        if has_legacy_columns and not row_field_name:
            result.failed += 1
            result.errors.append(
                f"SET row for RefDes={_repairs_cell(row, 'RefDes')!r} has blank UUID or Field — skipped"
            )
            continue

        row_uuid = _repairs_cell(row, "UUID")
        row_ref_des = _repairs_cell(row, "RefDes")
        row_project_path = _repairs_cell(row, "ProjectPath")
        if not row_uuid:
            result.failed += 1
            result.errors.append(
                f"SET row for RefDes={row_ref_des!r} has blank UUID — skipped"
            )
            continue
        updates = _extract_row_updates(
            row,
            current_row=current_rows_by_uuid.get(row_uuid),
        )
        if not updates:
            result.skipped += 1
            continue

        # Multi-project filter: silently skip rows that belong to a different project.
        if row_project_path:
            rp = Path(row_project_path).resolve()
            if rp.suffix == ".kicad_pro":
                rp = rp.parent
            if rp not in project_dirs:
                result.skipped += 1
                continue

        location = uuid_to_location.get(row_uuid)
        if location is None:
            result.failed += 1
            field_names = ", ".join(field for field, _ in updates)
            result.errors.append(
                f"UUID {row_uuid!r} (RefDes={row_ref_des!r}, Fields={field_names!r}) "
                "not found in any schematic file"
            )
            continue

        symbol, sch_path = location

        if row_ref_des:
            current_ref = _get_property_value(symbol, "Reference")
            if current_ref and current_ref != row_ref_des:
                result.warnings.append(
                    f"INFO: UUID {row_uuid!r}: RefDes changed "
                    f"from {row_ref_des!r} (audit) to {current_ref!r} (schematic) "
                    f"\u2014 applying by UUID"
                )

        for field_name, approved_value in updates:
            current = _get_property_value(symbol, field_name)
            if current == approved_value:
                result.applied += 1
                continue

            result.changes.append(
                AnnotationChange(
                    uuid=row_uuid,
                    field=field_name,
                    before=current,
                    after=approved_value,
                    row_number=row.row_number,
                )
            )
            result.applied += 1
            if not dry_run:
                _set_property_value(symbol, field_name, approved_value)
                changed_files.add(sch_path)

    if not dry_run:
        for sch_path in changed_files:
            sch_path.write_text(
                sexpdata.dumps(schematics_cache[sch_path]), encoding="utf-8"
            )

    return result


@dataclass(frozen=True)
class _RepairsRowRaw:
    """Internal: one raw row from repairs CSV before filtering."""

    row_number: int
    cells: dict[str, str]


def _load_repairs_rows(repairs_path: Path) -> list[_RepairsRowRaw]:
    """Load and parse an audit report.csv into raw repairs rows."""
    rows: list[_RepairsRowRaw] = []
    with repairs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return rows
        for line_idx, raw in enumerate(reader, start=2):
            cells: dict[str, str] = {}
            for col, val in raw.items():
                if not col:
                    continue
                if isinstance(val, str):
                    cells[col] = val.strip()
                else:
                    cells[col] = ""

            rows.append(
                _RepairsRowRaw(
                    row_number=line_idx,
                    cells=cells,
                )
            )
    return rows


_WIDE_REPAIRS_METADATA_COLUMNS: set[str] = {
    "RowType",
    "ProjectPath",
    "RefDes",
    "UUID",
    "Category",
    "Debug",
    "Matchability",
    "MatchBasis",
    "EMMatchability",
    "EMBasis",
    "SupplierMatchability",
    "SupplierBasis",
    "CheckType",
    "Severity",
    "CatalogFile",
    "IPN",
    "Field",
    "CurrentValue",
    "SuggestedValue",
    "ApprovedValue",
    "Action",
    "Supplier",
    "SupplierPN",
    "Description",
    "Notes",
}


def _repairs_cell(row: _RepairsRowRaw, col: str) -> str:
    """Return a normalized cell value from a parsed repairs CSV row."""
    return (row.cells.get(col) or "").strip()


def _extract_row_updates(
    row: _RepairsRowRaw,
    *,
    current_row: _RepairsRowRaw | None = None,
) -> list[tuple[str, str]]:
    """Extract field updates from a repairs row (legacy tall or wide format)."""
    field_name = _repairs_cell(row, "Field")
    approved_value = _repairs_cell(row, "ApprovedValue")
    has_legacy_columns = bool(field_name or approved_value)
    if has_legacy_columns:
        if not field_name:
            return []
        normalized_value = _normalize_repair_update_value(approved_value)
        if not normalized_value or normalized_value.upper() == "MISSING":
            return []
        return [(field_name, normalized_value)]

    updates: list[tuple[str, str]] = []
    for col, val in row.cells.items():
        if col in _WIDE_REPAIRS_METADATA_COLUMNS:
            continue
        baseline_value = _repairs_cell(current_row, col) if current_row else ""
        cell_value = _normalize_repair_update_value_with_baseline(
            val,
            baseline_value=baseline_value,
        )
        if not cell_value or cell_value.upper() == "MISSING":
            continue
        updates.append((col, cell_value))
    return updates


def _normalize_repair_update_value(raw_value: str) -> str:
    """Normalize a repairs update value for schematic annotation."""
    return _normalize_repair_update_value_with_baseline(
        raw_value,
        baseline_value="",
    )


def _normalize_repair_update_value_with_baseline(
    raw_value: str,
    *,
    baseline_value: str,
) -> str:
    """Normalize a repairs update value using CURRENT row content as fallback."""
    text = str(raw_value or "").strip()
    if not text:
        return ""
    parsed_value = _parse_merge_notation_value(text)
    if not parsed_value["has_merge_notation"]:
        return parsed_value["bare_value"]

    parsed_baseline = _parse_merge_notation_value(baseline_value)
    baseline_s = parsed_baseline["source_values"].get(
        "s", parsed_baseline["bare_value"]
    )
    baseline_p = parsed_baseline["source_values"].get(
        "p", parsed_baseline["bare_value"]
    )

    resolved_s = parsed_value["source_values"].get("s", baseline_s)
    resolved_p = parsed_value["source_values"].get("p", baseline_p)

    if resolved_s:
        return resolved_s
    if resolved_p:
        return resolved_p
    return ""


def _parse_merge_notation_value(raw_value: str) -> dict[str, Any]:
    """Parse s:/p: merge notation from a repairs cell value."""
    text = str(raw_value or "").strip()
    if not text:
        return {
            "has_merge_notation": False,
            "source_values": {},
            "bare_value": "",
        }
    expanded_text = text.replace("\\n", "\n")
    lines = [line.strip() for line in expanded_text.splitlines() if line.strip()]
    source_values: dict[str, str] = {}
    bare_parts: list[str] = []
    has_merge_notation = False

    for line in lines:
        if ":" in line:
            source, value = line.split(":", 1)
            source_key = source.strip().lower()
            if source_key in {"s", "p"}:
                source_values[source_key] = value.strip()
                has_merge_notation = True
                continue
        bare_parts.append(line)

    bare_value = "\n".join(bare_parts).strip()

    return {
        "has_merge_notation": has_merge_notation,
        "source_values": source_values,
        "bare_value": bare_value,
    }


def _get_symbol_uuid(symbol: list[Any]) -> str:
    """Extract UUID from a symbol node."""

    for child in symbol[1:]:
        if (
            isinstance(child, list)
            and child
            and child[0] == sexpdata.Symbol("uuid")
            and len(child) >= 2
        ):
            return str(child[1])
    return ""


def _find_property_node(symbol: list[Any], field_name: str) -> list[Any] | None:
    """Find a property node by property name within a symbol node."""

    for child in symbol[1:]:
        if not (
            isinstance(child, list)
            and child
            and child[0] == sexpdata.Symbol("property")
            and len(child) >= 3
        ):
            continue

        if str(child[1]) == field_name:
            return child
    return None


def _get_property_value(symbol: list[Any], field_name: str) -> str:
    """Get the current property value for a symbol field."""

    node = _find_property_node(symbol, field_name)
    if node is None:
        return ""
    return str(node[2])


def _set_property_value(symbol: list[Any], field_name: str, value: str) -> None:
    """Set or create a property value on a symbol node."""

    node = _find_property_node(symbol, field_name)
    if node is not None:
        node[2] = value
        return

    next_id = _next_property_id(symbol)
    symbol.append(
        [
            sexpdata.Symbol("property"),
            field_name,
            value,
            [sexpdata.Symbol("id"), next_id],
            [sexpdata.Symbol("at"), 0, 0, 0],
        ]
    )


def _remove_property(symbol: list[Any], field_name: str) -> None:
    """Remove a property node from a symbol if present."""

    node = _find_property_node(symbol, field_name)
    if node is not None:
        symbol.remove(node)


def _next_property_id(symbol: list[Any]) -> int:
    """Return the next available property id for a symbol."""

    highest = -1
    for child in symbol[1:]:
        if not (
            isinstance(child, list)
            and child
            and child[0] == sexpdata.Symbol("property")
        ):
            continue

        for token in child[3:]:
            if (
                isinstance(token, list)
                and token
                and token[0] == sexpdata.Symbol("id")
                and len(token) >= 2
            ):
                try:
                    highest = max(highest, int(token[1]))
                except (TypeError, ValueError):
                    continue

    return highest + 1
