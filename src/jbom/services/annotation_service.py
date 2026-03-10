"""Services for inventory-driven schematic annotation and triage."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sexpdata

from jbom.common.sexp_parser import load_kicad_file, walk_nodes

_RESERVED_COLUMNS = {"project", "uuid", "sourcefile", "projectname", "refs"}
_REQUIRED_FIELDS = ("Value", "Package")
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
class AnnotationRow:
    """One inventory row loaded for annotation."""

    row_number: int
    project: str
    uuid: str
    values: dict[str, str]


@dataclass
class AnnotationResult:
    """Result summary for annotate execution."""

    dry_run: bool
    updated_components: int
    changes: list[AnnotationChange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TriageRowIssue:
    """A CSV row with missing required fields for annotation."""

    row_number: int
    project: str
    uuid: str
    missing_required_fields: list[str]


@dataclass
class TriageReport:
    """Triage report for required blanks in inventory rows."""

    total_data_rows: int
    rows_with_required_blanks: list[TriageRowIssue] = field(default_factory=list)


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


def annotate_schematic(
    schematic_path: Path,
    inventory_path: Path,
    *,
    dry_run: bool = False,
    schematic_files: list[Path] | None = None,
) -> AnnotationResult:
    """Apply annotation values from inventory rows to schematic symbols by UUID.

    Supports hierarchical projects via the ``schematic_files`` parameter.

    Routing logic:
    - **Primary path**: when CSV rows carry a non-blank ``SourceFile`` column,
      each row is routed directly to its named file and matched by UUID.
      ``SourceFile`` + ``UUID`` is the canonical, unambiguous key.
    - **Fallback path**: when ``SourceFile`` is absent (hand-crafted or
      pre-Enhancement-6 CSVs), a global UUID index is built across all
      ``schematic_files`` and rows are applied by UUID alone.  UUIDs are
      unique within a KiCad project hierarchy, so no collision is possible.

    Args:
        schematic_path: Primary ``.kicad_sch`` file (used when
            ``schematic_files`` is ``None`` — preserves single-file call-site
            compatibility).
        inventory_path: CSV inventory file used for annotation.
        dry_run: When ``True``, compute changes but do not write any files.
        schematic_files: Full list of schematic files in the project hierarchy.
            When ``None`` defaults to ``[schematic_path]``.
    """

    if schematic_files is None:
        schematic_files = [schematic_path]

    rows = _load_annotation_rows(inventory_path)

    # Determine routing strategy: primary (SourceFile present) vs fallback (UUID-only)
    has_source_file_column = any(
        row.values.get("SourceFile", "").strip()
        for row in rows
        if not _is_header_or_subheader_row(row)
    )

    if has_source_file_column:
        return _annotate_with_source_file_routing(
            rows, schematic_files, dry_run=dry_run
        )
    else:
        return _annotate_with_uuid_index(rows, schematic_files, dry_run=dry_run)


def _annotate_with_source_file_routing(
    rows: list[AnnotationRow],
    schematic_files: list[Path],
    *,
    dry_run: bool,
) -> AnnotationResult:
    """Primary annotation path: route each row to its SourceFile, apply by UUID."""

    changes: list[AnnotationChange] = []
    warnings: list[str] = []
    updated_components: set[str] = set()

    # Group rows by their SourceFile value
    rows_by_source: dict[str, list[AnnotationRow]] = {}
    for row in rows:
        if _is_header_or_subheader_row(row):
            continue
        source = row.values.get("SourceFile", "").strip()
        if not source:
            continue  # Skip rows without SourceFile in a SourceFile-routed pass
        rows_by_source.setdefault(source, []).append(row)

    # Build a set of known schematic file paths for fast lookup
    known_files = {str(p.resolve()): p for p in schematic_files}

    for source_path_str, source_rows in rows_by_source.items():
        # Resolve to absolute path
        source_path = Path(source_path_str)
        resolved_str = str(source_path.resolve())

        # Prefer the known project file if it matches; otherwise use as-is
        target_path = known_files.get(resolved_str, source_path)

        if not target_path.exists():
            warnings.append(
                f"SourceFile not found on disk, skipping {len(source_rows)} row(s): {source_path_str}"
            )
            continue

        result = _apply_rows_to_file(source_rows, target_path, dry_run=dry_run)
        changes.extend(result.changes)
        warnings.extend(result.warnings)
        updated_components.update(c.uuid for c in result.changes)

    return AnnotationResult(
        dry_run=dry_run,
        updated_components=len(updated_components),
        changes=changes,
        warnings=warnings,
    )


def _annotate_with_uuid_index(
    rows: list[AnnotationRow],
    schematic_files: list[Path],
    *,
    dry_run: bool,
) -> AnnotationResult:
    """Fallback annotation path: build global UUID index across all files.

    Used when the CSV has no ``SourceFile`` column.  Within a single KiCad
    project hierarchy KiCad guarantees UUID uniqueness, so no collision is
    possible.
    """

    changes: list[AnnotationChange] = []
    warnings: list[str] = []
    updated_components: set[str] = set()

    # Build UUID -> (symbol_node, source_file) index across all schematic files
    uuid_to_location: dict[str, tuple[list[Any], Path]] = {}
    schematics_cache: dict[Path, list[Any]] = {}

    for sch_path in schematic_files:
        if not sch_path.exists():
            warnings.append(f"Schematic file not found, skipping: {sch_path}")
            continue
        schematic = load_kicad_file(sch_path)
        schematics_cache[sch_path] = schematic
        for symbol in walk_nodes(schematic, "symbol"):
            symbol_uuid = _get_symbol_uuid(symbol)
            if symbol_uuid and symbol_uuid not in uuid_to_location:
                uuid_to_location[symbol_uuid] = (symbol, sch_path)

    # Apply rows using UUID index
    for row in rows:
        if _is_header_or_subheader_row(row):
            continue

        missing_required = _missing_required_fields(row.values)
        if missing_required:
            warnings.append(
                f"Row {row.row_number} UUID {row.uuid or '<blank>'}: required blank field(s): "
                + ", ".join(missing_required)
            )

        if not row.uuid:
            continue

        location = uuid_to_location.get(row.uuid)
        if location is None:
            warnings.append(
                f"Row {row.row_number}: UUID {row.uuid!r} not found in any schematic file"
            )
            continue

        symbol, source_path = location
        row_updates = _extract_row_updates(row.values)
        if not row_updates:
            continue

        row_changed = False
        for field_name, new_value in row_updates.items():
            current = _get_property_value(symbol, field_name)
            if current == new_value:
                continue
            changes.append(
                AnnotationChange(
                    uuid=row.uuid,
                    field=field_name,
                    before=current,
                    after=new_value,
                    row_number=row.row_number,
                )
            )
            row_changed = True
            if not dry_run:
                _set_property_value(symbol, field_name, new_value)

        if row_changed:
            updated_components.add(row.uuid)

    # Write back each modified schematic file
    if not dry_run and changes:
        changed_uuids = {c.uuid for c in changes}
        written: set[Path] = set()
        for uuid in changed_uuids:
            location = uuid_to_location.get(uuid)
            if location is None:
                continue
            _, source_path = location
            if source_path not in written:
                source_path.write_text(
                    sexpdata.dumps(schematics_cache[source_path]), encoding="utf-8"
                )
                written.add(source_path)

    return AnnotationResult(
        dry_run=dry_run,
        updated_components=len(updated_components),
        changes=changes,
        warnings=warnings,
    )


def _apply_rows_to_file(
    rows: list[AnnotationRow],
    schematic_path: Path,
    *,
    dry_run: bool,
) -> AnnotationResult:
    """Apply a set of annotation rows to a single schematic file."""

    schematic = load_kicad_file(schematic_path)
    symbols_by_uuid = _index_symbols_by_uuid(schematic)

    changes: list[AnnotationChange] = []
    warnings: list[str] = []
    updated_components: set[str] = set()

    for row in rows:
        missing_required = _missing_required_fields(row.values)
        if missing_required:
            warnings.append(
                f"Row {row.row_number} UUID {row.uuid or '<blank>'}: required blank field(s): "
                + ", ".join(missing_required)
            )

        if not row.uuid:
            continue

        symbol = symbols_by_uuid.get(row.uuid)
        if symbol is None:
            continue

        row_updates = _extract_row_updates(row.values)
        if not row_updates:
            continue

        row_changed = False
        for field_name, new_value in row_updates.items():
            current = _get_property_value(symbol, field_name)
            if current == new_value:
                continue
            changes.append(
                AnnotationChange(
                    uuid=row.uuid,
                    field=field_name,
                    before=current,
                    after=new_value,
                    row_number=row.row_number,
                )
            )
            row_changed = True
            if not dry_run:
                _set_property_value(symbol, field_name, new_value)

        if row_changed:
            updated_components.add(row.uuid)

    if not dry_run and changes:
        schematic_path.write_text(sexpdata.dumps(schematic), encoding="utf-8")

    return AnnotationResult(
        dry_run=dry_run,
        updated_components=len(updated_components),
        changes=changes,
        warnings=warnings,
    )


def triage_inventory(inventory_path: Path) -> TriageReport:
    """Report rows with required blanks (Value/Package) for triage workflow."""

    rows = _load_annotation_rows(inventory_path)

    row_issues: list[TriageRowIssue] = []
    total_data_rows = 0

    for row in rows:
        if _is_header_or_subheader_row(row):
            continue

        total_data_rows += 1
        missing_required = _missing_required_fields(row.values)
        if not missing_required:
            continue

        row_issues.append(
            TriageRowIssue(
                row_number=row.row_number,
                project=row.project,
                uuid=row.uuid,
                missing_required_fields=missing_required,
            )
        )

    return TriageReport(
        total_data_rows=total_data_rows,
        rows_with_required_blanks=row_issues,
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
    3. Validate that ``UUID``, ``Field``, and ``ApprovedValue`` are all
       non-blank for each ``SET`` row; skip silently if ``ApprovedValue`` is
       blank (designer cleared it intentionally).
    4. Build a UUID → (symbol, file-path) index across all *schematic_files*.
    5. For each ``SET`` row, look up the UUID in the index and write
       ``Field <- ApprovedValue`` to the matching symbol.  A missing UUID is a
       **hard failure** (added to *errors*, counted as *failed*); the row is
       still attempted for all other ``SET`` rows.
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

    # Build UUID → (symbol_node, schematic_path) index.
    uuid_to_location: dict[str, tuple[Any, Path]] = {}
    schematics_cache: dict[Path, Any] = {}
    warnings: list[str] = []

    for sch_path in schematic_files:
        if not sch_path.exists():
            warnings.append(f"Schematic file not found, skipping: {sch_path}")
            continue
        schematic = load_kicad_file(sch_path)
        schematics_cache[sch_path] = schematic
        for symbol in walk_nodes(schematic, "symbol"):
            symbol_uuid = _get_symbol_uuid(symbol)
            if symbol_uuid and symbol_uuid not in uuid_to_location:
                uuid_to_location[symbol_uuid] = (symbol, sch_path)

    result = RepairsAnnotationResult(dry_run=dry_run)
    result.errors.extend(warnings)
    changed_files: set[Path] = set()

    for row in rows:
        if row.action.upper() != "SET":
            result.skipped += 1
            continue

        # Blank ApprovedValue — designer intentionally cleared it; skip silently.
        if not row.approved_value.strip():
            result.skipped += 1
            continue

        if not row.uuid.strip() or not row.field_name.strip():
            # Malformed SET row — treat as failure.
            result.failed += 1
            result.errors.append(
                f"SET row for RefDes={row.ref_des!r} has blank UUID or Field — skipped"
            )
            continue

        location = uuid_to_location.get(row.uuid)
        if location is None:
            result.failed += 1
            result.errors.append(
                f"UUID {row.uuid!r} (RefDes={row.ref_des!r}, Field={row.field_name!r}) "
                "not found in any schematic file"
            )
            continue

        symbol, sch_path = location
        current = _get_property_value(symbol, row.field_name)
        if current == row.approved_value:
            # Already at the desired value — count as applied (idempotent).
            result.applied += 1
            continue

        result.changes.append(
            AnnotationChange(
                uuid=row.uuid,
                field=row.field_name,
                before=current,
                after=row.approved_value,
                row_number=row.row_number,
            )
        )
        result.applied += 1
        if not dry_run:
            _set_property_value(symbol, row.field_name, row.approved_value)
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
    uuid: str
    ref_des: str
    field_name: str
    approved_value: str
    action: str


def _load_repairs_rows(repairs_path: Path) -> list[_RepairsRowRaw]:
    """Load and parse an audit report.csv into raw repairs rows."""
    rows: list[_RepairsRowRaw] = []
    with repairs_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return rows
        for line_idx, raw in enumerate(reader, start=2):

            def _cell(col: str) -> str:
                v = raw.get(col) or ""
                return v.strip() if isinstance(v, str) else ""

            rows.append(
                _RepairsRowRaw(
                    row_number=line_idx,
                    uuid=_cell("UUID"),
                    ref_des=_cell("RefDes"),
                    field_name=_cell("Field"),
                    approved_value=_cell("ApprovedValue"),
                    action=_cell("Action"),
                )
            )
    return rows


def _load_annotation_rows(inventory_path: Path) -> list[AnnotationRow]:
    """Load annotation CSV rows as normalized row records."""

    with inventory_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []

        rows: list[AnnotationRow] = []
        for index, row in enumerate(reader, start=2):
            normalized = {str(k).strip(): _clean_cell(v) for k, v in row.items() if k}
            rows.append(
                AnnotationRow(
                    row_number=index,
                    project=normalized.get("Project", ""),
                    uuid=normalized.get("UUID", ""),
                    values=normalized,
                )
            )

    return rows


def _clean_cell(value: str | None) -> str:
    """Normalize a CSV cell value to stripped string."""

    return value.strip() if isinstance(value, str) else ""


def _is_header_or_subheader_row(row: AnnotationRow) -> bool:
    """Return True when row is a header/sub-header sentinel row."""

    return row.project == "Project"


def _missing_required_fields(values: dict[str, str]) -> list[str]:
    """Return required fields that are blank in a row."""

    missing: list[str] = []
    for field_name in _REQUIRED_FIELDS:
        if values.get(field_name, "").strip():
            continue
        missing.append(field_name)
    return missing


def _extract_row_updates(values: dict[str, str]) -> dict[str, str]:
    """Extract non-blank annotation updates from a row."""

    updates: dict[str, str] = {}
    for field_name, value in values.items():
        if not value.strip():
            continue
        if field_name.lower() in _RESERVED_COLUMNS:
            continue
        updates[field_name] = value
    return updates


def _index_symbols_by_uuid(schematic: Any) -> dict[str, list[Any]]:
    """Build UUID -> symbol-node map from parsed schematic data."""

    indexed: dict[str, list[Any]] = {}
    for symbol in walk_nodes(schematic, "symbol"):
        symbol_uuid = _get_symbol_uuid(symbol)
        if not symbol_uuid:
            continue
        indexed[symbol_uuid] = symbol
    return indexed


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
