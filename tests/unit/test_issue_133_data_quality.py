"""Unit tests for Issue #133 — Data quality and field handling.

Covers:
- P0: Property key normalization in BOMGenerator
- Bug 1: Inventory virtual symbol filtering
- Bug 2: IPN blank unless explicit schematic property
- Bug 3: BOM Description populated from KiCad Description property
- Bug 4: BOM Package populated / derived from footprint
- Bug 5: --fields permissive (no rejection)
- Enh 6: Component.source_file set by SchematicReader (via fixture)
- Enh 7: annotate_schematic() hierarchy (primary + fallback paths)
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from jbom.common.component_utils import derive_package_from_footprint
from jbom.common.field_parser import parse_fields_argument
from jbom.common.component_filters import apply_component_filters
from jbom.common.types import Component
from jbom.services.bom_generator import BOMGenerator
from jbom.services.project_inventory import ProjectInventoryGenerator
from jbom.services.annotation_service import annotate_schematic


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


def _write_schematic(path: Path, uuid: str = "uuid-r1") -> None:
    path.write_text(
        f"""(kicad_sch (version 20211123) (generator eeschema)
  (symbol (lib_id "Device:R") (at 50 50 0)
    (uuid "{uuid}")
    (property "Reference" "R1" (id 0) (at 52 48 0))
    (property "Value" "10K" (id 1) (at 52 52 0))
    (property "Footprint" "R_0603" (id 2) (at 52 54 0))
    (property "Package" "0603" (id 3) (at 52 56 0))
  )
)
""",
        encoding="utf-8",
    )


def _write_inventory_csv(
    path: Path, rows: list[dict], fieldnames: list[str] | None = None
) -> None:
    if not fieldnames:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


# ---------------------------------------------------------------------------
# Enhancement 7: annotate hierarchy — fallback path
# ---------------------------------------------------------------------------


class TestEnh7AnnotateHierarchyFallback:
    """annotate_schematic fallback path: UUID index across multiple files."""

    def test_fallback_annotates_component_in_sub_sheet(self, tmp_path: Path) -> None:
        root = tmp_path / "root.kicad_sch"
        sub = tmp_path / "sub.kicad_sch"
        _write_schematic(root, uuid="uuid-root")
        _write_schematic(sub, uuid="uuid-sub")

        inventory = tmp_path / "inv.csv"
        _write_inventory_csv(
            inventory,
            [
                {
                    "Project": str(tmp_path),
                    "UUID": "uuid-sub",
                    "Value": "22K",
                    "Package": "0805",
                }
            ],
            fieldnames=["Project", "UUID", "Value", "Package"],
        )

        result = annotate_schematic(
            schematic_path=root,
            inventory_path=inventory,
            dry_run=False,
            schematic_files=[root, sub],
        )

        assert result.updated_components == 1
        updated = sub.read_text(encoding="utf-8")
        assert '"Value" "22K"' in updated

    def test_fallback_warns_on_uuid_not_found(self, tmp_path: Path) -> None:
        root = tmp_path / "root.kicad_sch"
        _write_schematic(root, uuid="uuid-root")

        inventory = tmp_path / "inv.csv"
        _write_inventory_csv(
            inventory,
            [
                {
                    "Project": "",
                    "UUID": "no-such-uuid",
                    "Value": "33K",
                    "Package": "0402",
                }
            ],
            fieldnames=["Project", "UUID", "Value", "Package"],
        )

        result = annotate_schematic(
            schematic_path=root,
            inventory_path=inventory,
            dry_run=False,
            schematic_files=[root],
        )

        assert result.updated_components == 0
        assert any("no-such-uuid" in w for w in result.warnings)

    def test_fallback_dry_run_does_not_write(self, tmp_path: Path) -> None:
        root = tmp_path / "root.kicad_sch"
        _write_schematic(root, uuid="uuid-root")
        original = root.read_text(encoding="utf-8")

        inventory = tmp_path / "inv.csv"
        _write_inventory_csv(
            inventory,
            [{"Project": "", "UUID": "uuid-root", "Value": "47K", "Package": "1206"}],
            fieldnames=["Project", "UUID", "Value", "Package"],
        )

        result = annotate_schematic(
            schematic_path=root,
            inventory_path=inventory,
            dry_run=True,
            schematic_files=[root],
        )

        assert result.dry_run is True
        assert result.updated_components == 1
        assert root.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Enhancement 7: annotate hierarchy — primary path (SourceFile routing)
# ---------------------------------------------------------------------------


class TestEnh7AnnotateHierarchyPrimaryPath:
    """annotate_schematic primary path: SourceFile+UUID routing."""

    def test_primary_routes_to_correct_file(self, tmp_path: Path) -> None:
        root = tmp_path / "root.kicad_sch"
        sub = tmp_path / "sub.kicad_sch"
        _write_schematic(root, uuid="uuid-root")
        _write_schematic(sub, uuid="uuid-sub")

        inventory = tmp_path / "inv.csv"
        _write_inventory_csv(
            inventory,
            [
                {
                    "Project": str(tmp_path),
                    "UUID": "uuid-sub",
                    "SourceFile": str(sub),
                    "Value": "56K",
                    "Package": "0402",
                }
            ],
            fieldnames=["Project", "UUID", "SourceFile", "Value", "Package"],
        )

        result = annotate_schematic(
            schematic_path=root,
            inventory_path=inventory,
            dry_run=False,
            schematic_files=[root, sub],
        )

        assert result.updated_components == 1
        assert '"Value" "56K"' in sub.read_text(encoding="utf-8")

    def test_primary_warns_on_missing_source_file(self, tmp_path: Path) -> None:
        root = tmp_path / "root.kicad_sch"
        _write_schematic(root, uuid="uuid-root")

        inventory = tmp_path / "inv.csv"
        _write_inventory_csv(
            inventory,
            [
                {
                    "Project": "",
                    "UUID": "uuid-root",
                    "SourceFile": "/nonexistent/path.kicad_sch",
                    "Value": "1K",
                    "Package": "0603",
                }
            ],
            fieldnames=["Project", "UUID", "SourceFile", "Value", "Package"],
        )

        result = annotate_schematic(
            schematic_path=root,
            inventory_path=inventory,
            dry_run=False,
            schematic_files=[root],
        )

        assert result.updated_components == 0
        assert any("not found on disk" in w for w in result.warnings)
