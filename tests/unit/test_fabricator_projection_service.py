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
            "i:package",
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
        "LCSC",
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


def test_resolve_fabricator_part_number_prefers_explicit_attribute() -> None:
    config = FabricatorProjectionService().load_config("jlc")
    assert config is not None

    result = FabricatorProjectionService.resolve_fabricator_part_number(
        {
            "fabricator_part_number": "JLC-OVERRIDE-001",
            "lcsc": "C1234",
            "jlcpcb_part_#": "C9999",
        },
        fabricator_id="jlc",
        fabricator_config=config,
    )

    assert result == "JLC-OVERRIDE-001"


def test_resolve_fabricator_part_number_uses_synonyms() -> None:
    config = FabricatorProjectionService().load_config("jlc")
    assert config is not None

    result = FabricatorProjectionService.resolve_fabricator_part_number(
        {"jlcpcb_part_#": "C965799"},
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
