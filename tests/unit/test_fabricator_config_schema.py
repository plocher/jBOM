"""Unit tests for FabricatorConfig schema parsing (field_synonyms + tier_rules)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jbom.config.fabricators import (
    FabricatorConfig,
    FieldSynonym,
    TierCondition,
    TierRule,
    get_available_fabricators,
    load_fabricator,
)
from jbom.services.gerber_service import gerber_request_from_config

# ---------------------------------------------------------------------------
# Standard fabrication layer set — the "obvious thing" contract.
# All built-in fabricators must include at minimum these layers so that
# gherkin scenarios using default flags produce fabrication-ready output
# without any special configuration.
# ---------------------------------------------------------------------------
_REQUIRED_LAYERS = {
    "F.Cu",
    "B.Cu",
    "F.Mask",
    "B.Mask",
    "F.Paste",
    "B.Paste",
    "F.Silkscreen",
    "B.Silkscreen",
    "Edge.Cuts",
}


def test_load_generic_derives_field_synonyms_and_tier_rules_from_suppliers() -> None:
    fab = load_fabricator("generic")

    assert isinstance(fab.field_synonyms, dict)

    assert "fab_pn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["fab_pn"], FieldSynonym)
    assert fab.field_synonyms["fab_pn"].display_name

    assert "supplier_pn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["supplier_pn"], FieldSynonym)
    # supplier_pn display_name comes from generic supplier's supplier_pn.display_name
    assert fab.field_synonyms["supplier_pn"].display_name == "Part Number"

    # With the normalized Supplier/SPN schema, part-number resolution uses
    # item.supplier + item.spn at runtime, not column-name synonym lists.
    # Synonyms are intentionally empty in the new schema.
    assert isinstance(fab.field_synonyms["supplier_pn"].synonyms, list)

    assert "mpn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["mpn"], FieldSynonym)

    assert isinstance(fab.tier_rules, list)
    assert len(fab.tier_rules) >= 3
    assert isinstance(fab.tier_rules[0], TierRule)
    assert isinstance(fab.tier_rules[0].conditions[0], TierCondition)

    assert isinstance(fab.suppliers, list)
    assert fab.suppliers
    assert all(isinstance(s, str) for s in fab.suppliers)


def test_resolve_field_synonym_is_forgiving() -> None:
    fab = load_fabricator("jlc")

    # JLC recognizes both the new SPN column and legacy LCSC schematic properties.
    assert fab.resolve_field_synonym(" SPN ") == "fab_pn"
    assert fab.resolve_field_synonym("spn") == "fab_pn"
    assert fab.resolve_field_synonym(" Lcsc Part # ") == "fab_pn"
    assert fab.resolve_field_synonym("fab_pn") == "fab_pn"
    assert fab.resolve_field_synonym("Manufacturer_Part_Number") == "mpn"
    assert fab.resolve_field_synonym("unknown_field") is None


def test_from_yaml_dict_rejects_unknown_supplier_ids() -> None:
    data = {
        "name": "Example",
        "pos_columns": {"Designator": "reference"},
        "suppliers": ["definitely-not-a-real-supplier"],
    }

    with pytest.raises(ValueError, match=r"Unknown supplier"):
        FabricatorConfig.from_yaml_dict(data, default_id="example")


def test_from_yaml_dict_rejects_deprecated_priority_fields() -> None:
    data = {
        "name": "Example",
        "pos_columns": {"Designator": "reference"},
        "suppliers": ["generic"],
        "field_synonyms": {
            "fab_pn": {"display_name": "Fab PN"},
            "supplier_pn": {"display_name": "Supplier PN"},
            "mpn": {"display_name": "MPN"},
        },
        "part_number": {"priority_fields": ["LCSC"]},
    }

    with pytest.raises(ValueError, match=r"priority_fields"):
        FabricatorConfig.from_yaml_dict(data, default_id="example")


# ---------------------------------------------------------------------------
# Gerbers stanza contract: every built-in fabricator must produce the
# "obvious" fabrication-ready GerberRequest when used with defaults.
# This is the foundation the gherkin scenarios rely on — they don't assert
# output details because generic does the right thing.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fab_id", get_available_fabricators())
def test_all_fabricators_have_gerbers_stanza(fab_id: str) -> None:
    """Every built-in fabricator config must declare a gerbers: stanza."""
    fab = load_fabricator(fab_id)
    assert fab.gerbers is not None, (
        f"Fabricator '{fab_id}' is missing a gerbers: stanza. "
        "All built-in fabricators must define gerber export policy so that "
        "jbom gerbers / jbom fab with default flags produce fabrication-ready output."
    )


@pytest.mark.parametrize("fab_id", get_available_fabricators())
def test_all_fabricators_gerbers_stanza_includes_required_layers(
    fab_id: str, tmp_path: Path
) -> None:
    """Every fabricator's gerbers stanza must include the 9 standard fabrication layers."""
    fab = load_fabricator(fab_id)
    assert fab.gerbers is not None
    req = gerber_request_from_config(
        tmp_path / "board.kicad_pcb",
        tmp_path / "gerbers",
        fabricator_id=fab_id,
        gerbers_cfg=fab.gerbers,
    )
    assert req.layers is not None, f"'{fab_id}' gerbers.layers must be set"
    layer_set = set(req.layers)
    missing = _REQUIRED_LAYERS - layer_set
    assert (
        not missing
    ), f"Fabricator '{fab_id}' gerbers.layers is missing required layers: {sorted(missing)}"


@pytest.mark.parametrize("fab_id", get_available_fabricators())
def test_all_fabricators_gerbers_stanza_split_drill_and_maps(
    fab_id: str, tmp_path: Path
) -> None:
    """Every fabricator must produce split PTH/NPTH drill files and drill maps by default."""
    fab = load_fabricator(fab_id)
    assert fab.gerbers is not None
    req = gerber_request_from_config(
        tmp_path / "board.kicad_pcb",
        tmp_path / "gerbers",
        fabricator_id=fab_id,
        gerbers_cfg=fab.gerbers,
    )
    assert req.drill_split_plated_holes is True, (
        f"Fabricator '{fab_id}': drill.split_plated_holes must be true "
        "so jbom gerbers produces separate PTH.drl + NPTH.drl files"
    )
    assert (
        req.drill_map_format is not None
    ), f"Fabricator '{fab_id}': drill.map_format must be set so drill maps are produced"


@pytest.mark.parametrize("fab_id", get_available_fabricators())
def test_all_fabricators_gerbers_stanza_protel_extensions(
    fab_id: str, tmp_path: Path
) -> None:
    """Every fabricator must use Protel-style file extensions by default."""
    fab = load_fabricator(fab_id)
    assert fab.gerbers is not None
    req = gerber_request_from_config(
        tmp_path / "board.kicad_pcb",
        tmp_path / "gerbers",
        fabricator_id=fab_id,
        gerbers_cfg=fab.gerbers,
    )
    assert req.protel_extensions is True, (
        f"Fabricator '{fab_id}': naming.protel_extensions must be true "
        "so output files use .gtl/.gbl/etc extensions"
    )


def test_from_yaml_dict_rejects_unknown_tier_operator() -> None:
    data = {
        "name": "Example",
        "pos_columns": {"Designator": "reference"},
        "suppliers": ["generic"],
        "field_synonyms": {
            "fab_pn": {"display_name": "Fab PN"},
            "supplier_pn": {"display_name": "Supplier PN"},
            "mpn": {"display_name": "MPN"},
        },
        "tier_overrides": [
            {"conditions": [{"field": "fab_pn", "operator": "bogus"}]},
        ],
    }

    with pytest.raises(ValueError, match=r"operator"):
        FabricatorConfig.from_yaml_dict(data, default_id="example")
