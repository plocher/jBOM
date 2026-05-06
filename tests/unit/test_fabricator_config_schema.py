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

    # In the Supplier/SPN schema, "SPN" is the canonical fab_pn column for JLC.
    assert fab.resolve_field_synonym(" SPN ") == "fab_pn"
    assert fab.resolve_field_synonym("spn") == "fab_pn"
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
