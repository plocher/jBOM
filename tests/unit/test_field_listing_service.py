"""Unit tests for field discovery/listing and source-priority resolution services."""

import pytest

from jbom.common.pcb_types import PcbComponent
from jbom.common.types import Component
from jbom.services.field_listing_service import (
    FieldListingService,
    get_field_names,
    normalize_priority,
    resolve_field,
)


def _make_schematic_component() -> Component:
    return Component(
        reference="R1",
        lib_id="Device:R",
        value="10K",
        footprint="R_0805_2012",
        properties={
            "LCSC": "C17414",
            "Manufacturer": "Yageo",
        },
    )


def _make_pcb_component() -> PcbComponent:
    return PcbComponent(
        reference="R1",
        footprint_name="R_0805_2012",
        package_token="0805",
        center_x_mm=5.0,
        center_y_mm=3.0,
        rotation_deg=0.0,
        side="TOP",
        attributes={"Value": "9K99", "LCSC": "C17414"},
    )


def test_get_field_names_discovers_schematic_fields() -> None:
    names = get_field_names(
        schematic_components=[_make_schematic_component()],
        source="s",
    )

    assert {"value", "footprint", "lcsc", "manufacturer"} <= names


def test_get_field_names_discovers_pcb_fields() -> None:
    names = get_field_names(
        pcb_components=[_make_pcb_component()],
        source="p",
    )

    assert {"footprint", "package", "value", "lcsc"} <= names


def test_get_field_names_discovers_inventory_column_names() -> None:
    names = get_field_names(
        inventory_column_names=["Voltage", "Tolerance"],
        source="i",
    )

    assert names == {"voltage", "tolerance"}


def test_get_field_names_source_all_returns_union() -> None:
    names = get_field_names(
        schematic_components=[_make_schematic_component()],
        pcb_components=[_make_pcb_component()],
        inventory_column_names=["Voltage"],
        source="all",
    )

    assert {"value", "footprint", "lcsc", "voltage"} <= names


def test_build_namespace_matrix_excludes_annotation_namespace_column() -> None:
    row = FieldListingService().build_namespace_matrix(
        ["value", "s:value", "p:value", "i:value", "a:value"]
    )[0]
    console = row.to_console_row()

    assert set(console.keys()) == {"Name", "s:", "p:", "i:"}
    assert row.s_token == "s:value"
    assert row.p_token == "p:value"
    assert row.i_token == "i:value"


def test_normalize_priority_accepts_string_and_sequence_forms() -> None:
    assert normalize_priority("pis") == ("p", "i", "s")
    assert normalize_priority(("s", "i", "p")) == ("s", "i", "p")


def test_normalize_priority_rejects_invalid_forms() -> None:
    with pytest.raises(ValueError):
        normalize_priority("ppi")

    with pytest.raises(ValueError):
        normalize_priority("pix")


def test_resolve_field_reads_only_requested_source_for_namespaced_tokens() -> None:
    row_sources = {
        "s": {"value": "10K"},
        "p": {"value": "9K99"},
        "i": {"value": "10K-INV"},
    }

    assert resolve_field("s:value", row_sources) == "10K"
    assert resolve_field("p:value", row_sources) == "9K99"
    assert resolve_field("i:value", row_sources) == "10K-INV"
    assert resolve_field("p:footprint", row_sources) == ""


def test_resolve_field_uses_priority_order_for_unqualified_tokens() -> None:
    row_sources = {
        "s": {"value": "10K"},
        "p": {"value": "9K99"},
        "i": {"value": "10K-INV"},
    }

    assert resolve_field("value", row_sources, priority="pis") == "9K99"
    assert resolve_field("value", row_sources, priority="sip") == "10K"


def test_resolve_field_returns_empty_for_unsupported_namespace() -> None:
    row_sources = {
        "s": {"value": "10K"},
        "p": {"value": "9K99"},
        "i": {"value": "10K-INV"},
    }

    assert resolve_field("a:value", row_sources) == ""
