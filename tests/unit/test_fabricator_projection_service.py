"""Unit tests for FabricatorProjectionService."""

from __future__ import annotations

from jbom.services.fabricator_projection_service import FabricatorProjectionService


def test_build_projection_maps_jlc_bom_headers() -> None:
    service = FabricatorProjectionService()
    projection = service.build_projection(
        fabricator_id="jlc",
        output_type="bom",
        selected_fields=[
            "reference",
            "quantity",
            "value",
            "description",
            "k:footprint",
            "fabricator_part_number",
            "smd",
        ],
    )

    assert projection.fabricator_config is not None
    assert projection.headers == (
        "Designator",
        "Quantity",
        "Value",
        "Comment",
        "Footprint",
        "LCSC Part #",
        "Surface Mount",
    )


def test_build_projection_unknown_fabricator_uses_default_headers() -> None:
    service = FabricatorProjectionService()
    projection = service.build_projection(
        fabricator_id="nonexistent-fabricator",
        output_type="bom",
        selected_fields=["reference", "i:package"],
    )

    assert projection.fabricator_config is None
    assert projection.headers == ("Reference", "I:Package")


def test_build_projection_maps_jlc_pos_headers() -> None:
    service = FabricatorProjectionService()
    projection = service.build_projection(
        fabricator_id="jlc",
        output_type="pos",
        selected_fields=["reference", "x", "y", "side", "rotation", "package"],
    )

    assert projection.fabricator_config is not None
    assert projection.headers == (
        "Designator",
        "Mid X",
        "Mid Y",
        "Layer",
        "Rotation",
        "Package",
    )


def test_resolve_fabricator_part_number_prefers_explicit_attribute() -> None:
    config = FabricatorProjectionService().load_config("jlc")
    assert config is not None

    result = FabricatorProjectionService.resolve_fabricator_part_number(
        {
            "fabricator_part_number": "JLC-OVERRIDE-001",
            "spn": "C1234",
        },
        fabricator_id="jlc",
        fabricator_config=config,
    )

    assert result == "JLC-OVERRIDE-001"


def test_resolve_fabricator_part_number_uses_synonyms() -> None:
    config = FabricatorProjectionService().load_config("jlc")
    assert config is not None

    # In the Supplier/SPN schema, "SPN" is the canonical column for JLC fab_pn.
    result = FabricatorProjectionService.resolve_fabricator_part_number(
        {"lcsc": "C965799"},
        fabricator_id="jlc",
        fabricator_config=config,
    )

    assert result == "C965799"


def test_resolve_fabricator_part_number_uses_pcbway_mpn_precedence() -> None:
    config = FabricatorProjectionService().load_config("pcbway")
    assert config is not None

    result = FabricatorProjectionService.resolve_fabricator_part_number(
        {
            "mpn": "SN74HC595D",
            "supplier_pn": "ALT-SUP-001",
            "fab_pn": "FAB-001",
        },
        fabricator_id="pcbway",
        fabricator_config=config,
    )

    assert result == "SN74HC595D"
