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


def test_load_generic_parses_field_synonyms_and_tier_rules() -> None:
    fab = load_fabricator("generic")

    assert isinstance(fab.field_synonyms, dict)
    assert "supplier_pn" in fab.field_synonyms
    assert isinstance(fab.field_synonyms["supplier_pn"], FieldSynonym)
    assert fab.field_synonyms["supplier_pn"].display_name == "Part Number"

    assert isinstance(fab.tier_rules, dict)
    assert 0 in fab.tier_rules
    assert isinstance(fab.tier_rules[0], TierRule)
    assert fab.tier_rules[0].conditions
    assert isinstance(fab.tier_rules[0].conditions[0], TierCondition)


def test_resolve_field_synonym_is_forgiving() -> None:
    fab = load_fabricator("jlc")

    assert fab.resolve_field_synonym(" Lcsc Part # ") == "fab_pn"
    assert fab.resolve_field_synonym("fab_pn") == "fab_pn"
    assert fab.resolve_field_synonym("unknown_field") is None


def test_from_yaml_dict_rejects_deprecated_priority_fields() -> None:
    data = {
        "name": "Example",
        "pos_columns": {"Designator": "reference"},
        "part_number": {"priority_fields": ["LCSC"]},
    }

    with pytest.raises(ValueError, match=r"priority_fields"):
        FabricatorConfig.from_yaml_dict(data, default_id="example")


def test_from_yaml_dict_rejects_unknown_tier_operator() -> None:
    data = {
        "name": "Example",
        "pos_columns": {"Designator": "reference"},
        "tier_rules": {
            0: {"conditions": [{"field": "fab_pn", "operator": "bogus"}]},
        },
    }

    with pytest.raises(ValueError, match=r"operator"):
        FabricatorConfig.from_yaml_dict(data, default_id="example")
