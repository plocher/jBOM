"""Unit tests for Issue #133 — Data quality and field handling.

Covers:
- P0: Property key normalization in BOMGenerator
- Bug 1: Inventory virtual symbol filtering
- Bug 2: IPN blank unless explicit schematic property
- Bug 3: BOM Description populated from KiCad Description property
- Bug 4: BOM Package populated / derived from footprint
- Bug 5: --fields permissive (no rejection)
- Enh 6: Component.source_file set by SchematicReader (via fixture)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from jbom.common.component_utils import derive_package_from_footprint
from jbom.common.field_parser import (
    parse_fields_argument,
    check_fabricator_field_completeness,
)
from jbom.common.component_filters import apply_component_filters
from jbom.common.types import Component
from jbom.config.fabricators import get_fabricator_presets
from jbom.services.bom_generator import BOMGenerator
from jbom.services.project_inventory import ProjectInventoryGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_comp(
    reference: str = "R1",
    lib_id: str = "Device:R",
    value: str = "10K",
    footprint: str = "Resistor_SMD:R_0603_1608Metric",
    uuid: str = "uuid-r1",
    in_bom: bool = True,
    dnp: bool = False,
    properties: dict | None = None,
    source_file: Path | None = None,
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        uuid=uuid,
        in_bom=in_bom,
        dnp=dnp,
        properties=properties or {},
        source_file=source_file,
    )


# ---------------------------------------------------------------------------
# P0: property key normalisation in BOMGenerator
# ---------------------------------------------------------------------------


class TestP0PropertyKeyNormalization:
    """BOMGenerator normalises KiCad title-cased property keys to snake_case."""

    def test_description_key_is_normalised(self) -> None:
        comp = _make_comp(properties={"Description": "10k Resistor"})
        gen = BOMGenerator()
        bom = gen.generate_bom_data([comp])
        entry = bom.entries[0]
        assert entry.attributes.get("description") == "10k Resistor"
        assert "Description" not in entry.attributes

    def test_package_key_is_normalised(self) -> None:
        comp = _make_comp(properties={"Package": "0603"})
        gen = BOMGenerator()
        bom = gen.generate_bom_data([comp])
        entry = bom.entries[0]
        assert entry.attributes.get("package") == "0603"

    def test_ipn_key_is_normalised(self) -> None:
        comp = _make_comp(properties={"IPN": "RES-0603-10K"})
        gen = BOMGenerator()
        bom = gen.generate_bom_data([comp])
        entry = bom.entries[0]
        assert entry.attributes.get("ipn") == "RES-0603-10K"

    def test_raw_component_properties_unchanged(self) -> None:
        """Component.properties must retain original KiCad casing."""
        comp = _make_comp(properties={"Description": "test", "Package": "0603"})
        assert "Description" in comp.properties
        assert "Package" in comp.properties


# ---------------------------------------------------------------------------
# Bug 1: Inventory virtual symbol filtering
# ---------------------------------------------------------------------------


class TestBug1VirtualSymbolFiltering:
    """apply_component_filters excludes virtual symbols by default."""

    def test_virtual_symbol_excluded_by_default(self) -> None:
        virtual = _make_comp(reference="#PWR01", lib_id="power:GND")
        real = _make_comp(reference="R1")
        result = apply_component_filters(
            [virtual, real],
            {
                "exclude_dnp": True,
                "include_only_bom": True,
                "include_virtual_symbols": False,
            },
        )
        assert len(result) == 1
        assert result[0].reference == "R1"

    def test_dnp_excluded_by_default(self) -> None:
        dnp_comp = _make_comp(reference="R2", dnp=True)
        real = _make_comp(reference="R1")
        result = apply_component_filters(
            [dnp_comp, real],
            {
                "exclude_dnp": True,
                "include_only_bom": True,
                "include_virtual_symbols": False,
            },
        )
        assert len(result) == 1
        assert result[0].reference == "R1"

    def test_non_bom_excluded_by_default(self) -> None:
        no_bom = _make_comp(reference="H1", in_bom=False)
        real = _make_comp(reference="R1")
        result = apply_component_filters(
            [no_bom, real],
            {
                "exclude_dnp": True,
                "include_only_bom": True,
                "include_virtual_symbols": False,
            },
        )
        assert len(result) == 1
        assert result[0].reference == "R1"


# ---------------------------------------------------------------------------
# Bug 2: IPN blank unless explicit schematic property
# ---------------------------------------------------------------------------


class TestBug2IPNBlankByDefault:
    """ProjectInventoryGenerator never invents an IPN."""

    def test_ipn_blank_when_no_schematic_property(self) -> None:
        comp = _make_comp(properties={})
        gen = ProjectInventoryGenerator([comp])
        items, _ = gen.load()
        assert items[0].ipn == ""

    def test_ipn_blank_for_unknown_category(self) -> None:
        comp = _make_comp(lib_id="Unknown:Widget", properties={})
        gen = ProjectInventoryGenerator([comp])
        items, _ = gen.load()
        assert items[0].ipn == ""

    def test_ipn_from_explicit_schematic_property(self) -> None:
        comp = _make_comp(properties={"IPN": "RES-0603-10K"})
        gen = ProjectInventoryGenerator([comp])
        items, _ = gen.load()
        assert items[0].ipn == "RES-0603-10K"

    def test_ipn_blank_per_instance(self) -> None:
        comp = _make_comp(properties={})
        gen = ProjectInventoryGenerator([comp])
        items, _ = gen.load_per_instance()
        assert items[0].ipn == ""


# ---------------------------------------------------------------------------
# Bug 3: BOM Description from KiCad property
# ---------------------------------------------------------------------------


class TestBug3DescriptionPopulated:
    """BOMEntry.attributes['description'] is populated from KiCad Description."""

    def test_description_populated(self) -> None:
        comp = _make_comp(properties={"Description": "Metal film resistor"})
        gen = BOMGenerator()
        bom = gen.generate_bom_data([comp])
        assert bom.entries[0].attributes.get("description") == "Metal film resistor"

    def test_description_empty_when_not_in_schematic(self) -> None:
        comp = _make_comp(properties={})
        gen = BOMGenerator()
        bom = gen.generate_bom_data([comp])
        assert bom.entries[0].attributes.get("description", "") == ""


# ---------------------------------------------------------------------------
# Bug 4: BOM Package from property or derived from footprint
# ---------------------------------------------------------------------------


class TestBug4PackagePopulated:
    """Package is taken from KiCad property, or derived by stripping lib prefix."""

    def test_derive_strips_library_prefix(self) -> None:
        assert derive_package_from_footprint("SPCoast:0603-RES") == "0603-RES"

    def test_derive_no_prefix_returns_as_is(self) -> None:
        assert derive_package_from_footprint("0603") == "0603"

    def test_derive_empty_footprint_returns_empty(self) -> None:
        assert derive_package_from_footprint("") == ""

    def test_package_from_kicad_property(self) -> None:
        comp = _make_comp(properties={"Package": "0805"})
        gen = BOMGenerator()
        bom = gen.generate_bom_data([comp])
        assert bom.entries[0].attributes.get("package") == "0805"


# ---------------------------------------------------------------------------
# Bug 5: --fields permissive
# ---------------------------------------------------------------------------


class TestBug5PermissiveFields:
    """parse_fields_argument accepts any field name without raising."""

    _available = {
        "reference": "Reference",
        "quantity": "Quantity",
        "value": "Value",
        "footprint": "Footprint",
        "description": "Description",
    }

    def test_known_fields_accepted(self) -> None:
        result = parse_fields_argument("reference,value", self._available)
        assert result == ["reference", "value"]

    def test_unknown_field_accepted_no_error(self) -> None:
        """IPN was previously rejected; now accepted silently."""
        result = parse_fields_argument(
            "Reference,Quantity,Value,IPN,Package,Footprint", self._available
        )
        assert "ipn" in result
        assert "package" in result
        assert "reference" in result

    def test_completely_unknown_field_accepted(self) -> None:
        result = parse_fields_argument(
            "reference,totally_made_up_field", self._available
        )
        assert "totally_made_up_field" in result

    def test_plus_unknown_field_accepted(self) -> None:
        result = parse_fields_argument("+nonexistent_preset_or_field", self._available)
        assert "nonexistent_preset_or_field" in result

    def test_no_error_on_multiple_unknown_fields(self) -> None:
        """Previously fail-fast on first unknown; now all accepted."""
        result = parse_fields_argument("bad1,bad2,bad3", self._available)
        assert result == ["bad1", "bad2", "bad3"]

    def test_empty_fields_still_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_fields_argument("", self._available)

    def test_jlc_header_tokens_map_to_internal_fields_without_warning(self) -> None:
        available = {
            "reference": "Reference",
            "quantity": "Quantity",
            "value": "Value",
            "description": "Description",
            "footprint": "Footprint",
            "i:package": "Inventory package",
            "fabricator_part_number": "Fabricator part number",
            "smd": "Surface mount indicator",
        }
        presets = get_fabricator_presets("jlc")
        selected = parse_fields_argument(
            "Designator,Quantity,Value,Comment,Footprint,SPN,Surface_Mount",
            available,
            fabricator_id="jlc",
            fabricator_presets=presets,
            context="bom",
        )
        assert selected == [
            "reference",
            "quantity",
            "value",
            "description",
            "i:package",
            "fabricator_part_number",
            "smd",
        ]
        warning = check_fabricator_field_completeness(selected, "jlc", presets)
        assert warning is None
