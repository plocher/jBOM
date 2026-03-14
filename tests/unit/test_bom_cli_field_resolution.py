"""Unit tests for BOM CLI field resolution helpers."""

from jbom.cli.bom import _get_field_value
from jbom.services.bom_generator import BOMEntry


def _make_entry(attributes: dict[str, object]) -> BOMEntry:
    """Create a minimal BOM entry for field resolution tests."""
    return BOMEntry(
        references=["R1"],
        value="10k",
        footprint="Resistor_SMD:R_0603_1608Metric",
        quantity=1,
        attributes=attributes,
    )


def test_fabricator_part_number_resolves_from_jlc_lcsc_attribute() -> None:
    entry = _make_entry({"lcsc": "C25585"})
    assert (
        _get_field_value(entry, "fabricator_part_number", fabricator_id="jlc")
        == "C25585"
    )


def test_fabricator_part_number_resolves_from_jlc_synonym_alias() -> None:
    entry = _make_entry({"jlcpcb_part_#": "C965799"})
    assert (
        _get_field_value(entry, "fabricator_part_number", fabricator_id="jlc")
        == "C965799"
    )


def test_fabricator_part_number_prefers_explicit_value() -> None:
    entry = _make_entry(
        {
            "fabricator_part_number": "JLC-OVERRIDE-123",
            "lcsc": "C25585",
            "jlcpcb_part_#": "C965799",
        }
    )
    assert (
        _get_field_value(entry, "fabricator_part_number", fabricator_id="jlc")
        == "JLC-OVERRIDE-123"
    )
