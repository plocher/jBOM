"""Unit tests for FabricatorConfig schema parsing (field_synonyms + tier_rules)."""

from __future__ import annotations

import pytest

from jbom.config.fabricators import (
    FabricatorConfig,
    FieldSynonym,
    TierCondition,
    TierRule,
    load_fabricator,
)


def test_load_generic_derives_field_synonyms_and_tier_rules_from_suppliers() -> None:
    fab = load_fabricator("generic")

    assert isinstance(fab.field_synonyms, dict)

    assert "fab_pn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["fab_pn"], FieldSynonym)
    assert fab.field_synonyms["fab_pn"].display_name

    assert "supplier_pn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["supplier_pn"], FieldSynonym)
    assert fab.field_synonyms["supplier_pn"].display_name == "Part Number"

    # Contract: derived supplier_pn synonyms include common header variants.
    assert "Part Number" in fab.field_synonyms["supplier_pn"].synonyms

    assert "mpn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["mpn"], FieldSynonym)

    assert isinstance(fab.tier_rules, dict)
    assert 1 in fab.tier_rules
    assert 2 in fab.tier_rules
    assert 3 in fab.tier_rules
    assert isinstance(fab.tier_rules[1], TierRule)
    assert isinstance(fab.tier_rules[1].conditions[0], TierCondition)

    assert isinstance(fab.suppliers, list)
    assert fab.suppliers
    assert all(isinstance(s, str) for s in fab.suppliers)


def test_resolve_field_synonym_is_forgiving() -> None:
    fab = load_fabricator("jlc")

    assert fab.resolve_field_synonym(" Lcsc Part # ") == "fab_pn"
    assert fab.resolve_field_synonym("fab_pn") == "fab_pn"
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
