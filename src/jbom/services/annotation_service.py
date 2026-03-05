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
