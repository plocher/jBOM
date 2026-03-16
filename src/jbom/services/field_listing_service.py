"""Field listing/discovery and source-priority field resolution services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from jbom.common.fields import normalize_field_name

_SOURCE_PREFIXES: tuple[str, ...] = ("s", "p", "i")


@dataclass(frozen=True)
class FieldNamespaceMatrixRow:
    """One row in the namespace matrix view for a canonical field name."""

    name: str
    s_token: str = ""
    p_token: str = ""
    i_token: str = ""

    def to_console_row(self) -> dict[str, str]:
        """Convert row to a console table mapping with fixed matrix columns."""

        return {
            "Name": self.name,
            "s:": self.s_token,
            "p:": self.p_token,
            "i:": self.i_token,
        }


def normalize_priority(priority: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize source-priority specifiers into an ordered (s|p|i) tuple."""

    if isinstance(priority, str):
        compact = priority.strip().lower()
        if not compact:
            raise ValueError("priority must not be empty")
        if any(separator in compact for separator in {",", " ", ">"}):
            tokens = [
                normalize_field_name(token).strip()
                for token in compact.replace(">", ",").replace(" ", ",").split(",")
                if token.strip()
            ]
        else:
            tokens = list(compact)
    else:
        tokens = [str(token or "").strip().lower() for token in priority if token]

    if len(tokens) != 3:
        raise ValueError("priority must specify exactly three source tokens")
    if len(set(tokens)) != 3:
        raise ValueError("priority cannot include duplicate source tokens")
    if any(token not in _SOURCE_PREFIXES for token in tokens):
        raise ValueError("priority may only contain source tokens: s, p, i")

    return tuple(tokens)


def resolve_namespaced_field(
    source: str,
    field_name: str,
    row_sources: Mapping[str, Mapping[str, object] | None],
) -> str:
    """Resolve one source-qualified field from row source maps."""

    normalized_source = str(source or "").strip().lower()
    if normalized_source not in _SOURCE_PREFIXES:
        return ""

    source_fields = row_sources.get(normalized_source) or {}
    return _lookup_normalized_value(source_fields, field_name)


def resolve_unqualified_field(
    field_name: str,
    row_sources: Mapping[str, Mapping[str, object] | None],
    *,
    priority: str | Sequence[str] = "pis",
) -> str:
    """Resolve an unqualified field using ordered source-priority lookup."""

    for source in normalize_priority(priority):
        value = resolve_namespaced_field(source, field_name, row_sources)
        if value:
            return value
    return ""


def get_field_names(
    *,
    schematic_components: Iterable[object] | None = None,
    pcb_components: Iterable[object] | None = None,
    inventory_column_names: Iterable[str] | None = None,
    source: str = "all",
) -> set[str]:
    """Discover normalized field names from schematic/PCB/inventory sources."""

    normalized_source = str(source or "all").strip().lower()
    if normalized_source not in {"s", "p", "i", "all"}:
        raise ValueError("source must be one of: s, p, i, all")

    discovered: set[str] = set()
    if normalized_source in {"s", "all"}:
        discovered.update(_discover_schematic_fields(schematic_components or []))
    if normalized_source in {"p", "all"}:
        discovered.update(_discover_pcb_fields(pcb_components or []))
    if normalized_source in {"i", "all"}:
        discovered.update(_discover_inventory_fields(inventory_column_names or []))
    return discovered


def get_namespaced_field_tokens(
    *,
    schematic_components: Iterable[object] | None = None,
    pcb_components: Iterable[object] | None = None,
    inventory_column_names: Iterable[str] | None = None,
) -> set[str]:
    """Return discovered source field tokens formatted as s:/p:/i: entries."""

    tokens: set[str] = set()
    for source in _SOURCE_PREFIXES:
        names = get_field_names(
            schematic_components=schematic_components,
            pcb_components=pcb_components,
            inventory_column_names=inventory_column_names,
            source=source,
        )
        tokens.update(f"{source}:{field_name}" for field_name in names)
    return tokens


class FieldListingService:
    """Build list-fields matrix data grouped by canonical field name."""

    def build_namespace_matrix(
        self,
        field_tokens: Iterable[str],
    ) -> list[FieldNamespaceMatrixRow]:
        """Group available tokens into Name|s:|p:|i: rows."""

        grouped: dict[str, dict[str, str]] = {}
        for raw_token in field_tokens:
            normalized_token = normalize_field_name(str(raw_token or ""))
            if not normalized_token:
                continue

            prefix, separator, remainder = normalized_token.partition(":")
            if separator and prefix in _SOURCE_PREFIXES and remainder:
                canonical_name = remainder
                slot = prefix
            elif separator and prefix == "a":
                continue
            else:
                canonical_name = normalized_token
                slot = "name"

            row = grouped.setdefault(
                canonical_name,
                {
                    "name": "",
                    "s": "",
                    "p": "",
                    "i": "",
                },
            )
            if not row[slot]:
                row[slot] = normalized_token

        matrix_rows: list[FieldNamespaceMatrixRow] = []
        for canonical_name in sorted(grouped.keys()):
            row = grouped[canonical_name]
            matrix_rows.append(
                FieldNamespaceMatrixRow(
                    name=row["name"] or canonical_name,
                    s_token=row["s"],
                    p_token=row["p"],
                    i_token=row["i"],
                )
            )
        return matrix_rows


def _discover_schematic_fields(schematic_components: Iterable[object]) -> set[str]:
    """Discover schematic source field names from component snapshots."""

    discovered: set[str] = set()
    for component in schematic_components:
        _add_if_present(discovered, "value", getattr(component, "value", ""))
        _add_if_present(discovered, "footprint", getattr(component, "footprint", ""))
        _add_if_present(discovered, "lib_id", getattr(component, "lib_id", ""))

        properties = getattr(component, "properties", {}) or {}
        if isinstance(properties, Mapping):
            for key in properties.keys():
                normalized_key = normalize_field_name(str(key or ""))
                if normalized_key:
                    discovered.add(normalized_key)
    return discovered


def _discover_pcb_fields(pcb_components: Iterable[object]) -> set[str]:
    """Discover PCB source field names from parsed board footprints."""

    discovered: set[str] = set()
    for component in pcb_components:
        _add_if_present(
            discovered, "footprint", getattr(component, "footprint_name", "")
        )
        _add_if_present(discovered, "package", getattr(component, "package_token", ""))
        _add_if_present(discovered, "side", getattr(component, "side", ""))
        _add_if_present(
            discovered,
            "x",
            getattr(component, "center_x_raw", "")
            or getattr(component, "center_x_mm", ""),
        )
        _add_if_present(
            discovered,
            "y",
            getattr(component, "center_y_raw", "")
            or getattr(component, "center_y_mm", ""),
        )
        _add_if_present(
            discovered,
            "rotation",
            getattr(component, "rotation_raw", "")
            or getattr(component, "rotation_deg", ""),
        )

        attributes = getattr(component, "attributes", {}) or {}
        if isinstance(attributes, Mapping):
            for key in attributes.keys():
                normalized_key = normalize_field_name(str(key or ""))
                if normalized_key:
                    discovered.add(normalized_key)
    return discovered


def _discover_inventory_fields(inventory_column_names: Iterable[str]) -> set[str]:
    """Discover inventory field names from loaded inventory column headers."""

    discovered: set[str] = set()
    for column_name in inventory_column_names:
        normalized_name = normalize_field_name(str(column_name or ""))
        if normalized_name:
            discovered.add(normalized_name)
    return discovered


def _add_if_present(field_names: set[str], field_name: str, raw_value: object) -> None:
    """Add a normalized field name when its source value is populated."""

    if str(raw_value or "").strip():
        normalized_name = normalize_field_name(field_name)
        if normalized_name:
            field_names.add(normalized_name)


def _lookup_normalized_value(
    source_fields: Mapping[str, object],
    field_name: str,
) -> str:
    """Resolve a field value from a source mapping using normalized key lookup."""

    normalized_name = normalize_field_name(str(field_name or ""))
    if not normalized_name:
        return ""

    direct_value = _normalize_scalar(source_fields.get(normalized_name))
    if direct_value:
        return direct_value

    raw_value = _normalize_scalar(source_fields.get(field_name))
    if raw_value:
        return raw_value

    for key, value in source_fields.items():
        if normalize_field_name(str(key or "")) != normalized_name:
            continue
        normalized_value = _normalize_scalar(value)
        if normalized_value:
            return normalized_value
    return ""


def _normalize_scalar(raw_value: object) -> str:
    """Normalize scalar values to stripped string form."""

    if raw_value is None:
        return ""
    if isinstance(raw_value, bool):
        return "Yes" if raw_value else "No"
    return str(raw_value).strip()
