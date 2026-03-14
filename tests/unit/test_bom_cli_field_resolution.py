"""Unit tests for BOM CLI field resolution helpers."""

from jbom.cli.bom import _entry_smd_from_reference_lookup, _get_field_value
from jbom.services.bom_generator import BOMEntry


def _make_entry(
    attributes: dict[str, object],
    *,
    footprint: str = "Resistor_SMD:R_0603_1608Metric",
) -> BOMEntry:
    """Create a minimal BOM entry for field resolution tests."""
    return BOMEntry(
        references=["R1"],
        value="10k",
        footprint=footprint,
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


def test_smd_field_uses_footprint_inference_when_attribute_missing() -> None:
    entry = _make_entry({})
    assert _get_field_value(entry, "smd", fabricator_id="jlc") == "Yes"


def test_smd_field_honors_explicit_false_attribute() -> None:
    entry = _make_entry({"smd": False})
    assert _get_field_value(entry, "smd", fabricator_id="jlc") == "No"


def test_entry_smd_lookup_returns_none_without_known_references() -> None:
    entry = _make_entry({})
    assert _entry_smd_from_reference_lookup(entry, {}) is None


def test_entry_smd_lookup_requires_all_known_references_smd() -> None:
    entry = BOMEntry(
        references=["R1", "R2"],
        value="10k",
        footprint="Resistor_SMD:R_0603_1608Metric",
        quantity=2,
        attributes={},
    )
    assert _entry_smd_from_reference_lookup(entry, {"R1": True, "R2": True}) is True
    assert _entry_smd_from_reference_lookup(entry, {"R1": True, "R2": False}) is False


def test_inventory_package_field_falls_back_to_derived_package() -> None:
    entry = _make_entry({}, footprint="SignalMast-ColorLight-SingleHead:0603-LED")
    assert _get_field_value(entry, "i:package", fabricator_id="jlc") == "0603-LED"


def test_inventory_package_field_prefers_explicit_package_attribute() -> None:
    entry = _make_entry({"package": "0603-LED"})
    assert _get_field_value(entry, "i:package", fabricator_id="jlc") == "0603-LED"
