"""Unit tests for config/defaults.py.

Covers:
- load_defaults("generic") loads the built-in profile correctly
- get_defaults() returns generic on unknown name (no raise)
- load_defaults() raises ValueError for unknown name
- extends: deep-merge: dict values merged, list values replaced
- from_yaml_dict: all sections parsed correctly
- Helper methods: get_domain_default, get_package_power, get_package_voltage, etc.
- _deep_merge semantics
- component_id_fields: parsing, get_component_id_fields(), validation
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from jbom.config.defaults import (
    DefaultsConfig,
    EnrichmentCategoryConfig,
    _deep_merge,
    get_active_defaults_profile,
    get_defaults,
    load_defaults,
    set_active_defaults_profile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data))


# ---------------------------------------------------------------------------
# Built-in generic profile
# ---------------------------------------------------------------------------


def test_load_defaults_generic_loads_successfully() -> None:
    cfg = load_defaults("generic")
    assert cfg.name == "generic"


def test_generic_profile_has_resistor_tolerance() -> None:
    cfg = load_defaults("generic")
    assert cfg.get_domain_default("resistor", "tolerance") == "5%"


def test_generic_profile_has_capacitor_defaults() -> None:
    cfg = load_defaults("generic")
    assert cfg.get_domain_default("capacitor", "tolerance") == "10%"
    assert cfg.get_domain_default("capacitor", "dielectric") == "X7R"


def test_generic_profile_has_package_power() -> None:
    cfg = load_defaults("generic")
    assert cfg.get_package_power("0603") == "100mW"
    assert cfg.get_package_power("0805") == "125mW"
    assert cfg.get_package_power("9999") == ""  # unknown package → empty


def test_generic_profile_has_package_voltage() -> None:
    cfg = load_defaults("generic")
    assert cfg.get_package_voltage("0603") == "25V"
    assert cfg.get_package_voltage("0402") == "10V"


def test_generic_profile_has_parametric_query_fields() -> None:
    cfg = load_defaults("generic")
    resistor_fields = cfg.get_parametric_query_fields("resistor")
    assert "resistance" in resistor_fields
    assert "tolerance" in resistor_fields


def test_generic_profile_has_category_route_rules() -> None:
    cfg = load_defaults("generic")
    rules = cfg.get_category_route_rules("resistor")
    assert rules.get("first_sort") == "Resistors"
    assert rules.get("second_sort_smd") == "Chip Resistor - Surface Mount"


def test_generic_profile_has_enrichment_attributes() -> None:
    cfg = load_defaults("generic")
    assert "resistor" in cfg.enrichment_attributes
    res_cfg = cfg.enrichment_attributes["resistor"]
    assert isinstance(res_cfg, EnrichmentCategoryConfig)
    assert "tolerance" in res_cfg.show_in_mode_a
    assert "pricing" in res_cfg.suppress


def test_generic_profile_has_field_synonyms() -> None:
    cfg = load_defaults("generic")
    voltage = cfg.get_field_synonym_config("voltage")
    assert voltage is not None
    assert voltage.display_name == "Voltage"
    assert "V" in voltage.synonyms

    manufacturer = cfg.get_field_synonym_config("manufacturer")
    assert manufacturer is not None
    assert manufacturer.display_name == "Manufacturer"
    assert "Manufacturer_Name" in manufacturer.synonyms

    mpn = cfg.get_field_synonym_config("mpn")
    assert mpn is not None
    assert mpn.display_name == "MPN"
    assert "Manufacturer Part Number" in mpn.synonyms


def test_generic_profile_has_default_search_output_fields() -> None:
    cfg = load_defaults("generic")
    assert cfg.get_search_output_fields_default() == [
        "supplier_part_number",
        "manufacturer",
        "mpn",
        "package",
        "category",
        "price",
        "description",
    ]


def test_generic_profile_has_default_search_package_tokens() -> None:
    cfg = load_defaults("generic")
    assert cfg.get_search_package_tokens() == [
        "0201",
        "0402",
        "0603",
        "0805",
        "1206",
        "1210",
        "1812",
        "2010",
        "2512",
    ]


def test_generic_profile_has_field_precedence_policy() -> None:
    cfg = load_defaults("generic")
    policy = cfg.get_field_precedence_policy()
    assert "schematic_biased" in policy
    assert "pcb_biased" in policy
    assert "inventory_biased" in policy
    assert "value" in policy["schematic_biased"]
    assert "footprint" in policy["pcb_biased"]
    assert "spn" in policy["inventory_biased"]


def test_generic_profile_has_inventory_schema_contract() -> None:
    cfg = load_defaults("generic")
    schema = cfg.get_inventory_schema()
    assert "inventory_ipn" in schema.canonical_fields
    assert "fabricator_part_number" in schema.canonical_fields
    assert schema.field_synonyms["inventory_ipn"].display_name == "IPN"
    assert "ipn" in schema.field_synonyms["inventory_ipn"].synonyms
    assert "mfgpn" in schema.field_synonyms["manufacturer_part"].synonyms
    assert "mpn" in schema.field_synonyms["manufacturer_part"].synonyms
    assert schema.enrichment_bindings["manufacturer_part"] == "mfgpn"
    assert (
        schema.enrichment_bindings["fabricator_part_number"]
        == "__resolved_fabricator_part_number__"
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_load_defaults_raises_for_unknown_name() -> None:
    with pytest.raises(ValueError, match="not found"):
        load_defaults("nonexistent_xyz_profile_abc")


def test_get_defaults_returns_generic_on_unknown_name() -> None:
    cfg = get_defaults("nonexistent_xyz_profile_abc")
    assert cfg.name == "generic"
    assert cfg.get_domain_default("resistor", "tolerance") == "5%"


def test_get_defaults_uses_active_profile_when_name_omitted(tmp_path: Path) -> None:
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "tight.defaults.yaml").write_text(
        "extends: generic\n"
        "domain_defaults:\n"
        "  resistor:\n"
        "    tolerance: '1%'\n"
    )

    previous = get_active_defaults_profile()
    set_active_defaults_profile("tight")
    try:
        cfg = get_defaults(cwd=tmp_path)
        assert cfg.name == "tight"
        assert cfg.get_domain_default("resistor", "tolerance") == "1%"
    finally:
        set_active_defaults_profile(previous)


# ---------------------------------------------------------------------------
# extends: chain and deep-merge semantics
# ---------------------------------------------------------------------------


def test_extends_overrides_single_value(tmp_path: Path) -> None:
    """extends: generic + override one tolerance → only that value changes."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    override = jbom_dir / "aerospace.defaults.yaml"
    override.write_text(
        "extends: generic\n"
        "domain_defaults:\n"
        "  resistor:\n"
        "    tolerance: '1%'\n"
    )

    cfg = load_defaults("aerospace", cwd=tmp_path)
    assert cfg.get_domain_default("resistor", "tolerance") == "1%"
    # capacitor defaults still inherited from generic
    assert cfg.get_domain_default("capacitor", "tolerance") == "10%"
    assert cfg.get_domain_default("capacitor", "dielectric") == "X7R"


def test_extends_replaces_list_sections(tmp_path: Path) -> None:
    """When a list is overridden, the full list is replaced (not appended)."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "short.defaults.yaml").write_text(
        "extends: generic\n"
        "parametric_query_fields:\n"
        "  resistor:\n"
        "    - resistance\n"
        "    - tolerance\n"
    )

    cfg = load_defaults("short", cwd=tmp_path)
    fields = cfg.get_parametric_query_fields("resistor")
    # Replaced — only 2 fields, not the generic 5
    assert fields == ["resistance", "tolerance"]
    # Capacitor list is still inherited
    assert len(cfg.get_parametric_query_fields("capacitor")) > 0


def test_extends_inherits_all_unspecified_sections(tmp_path: Path) -> None:
    """A child that only overrides one section gets all others from parent."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "minimal.defaults.yaml").write_text(
        "extends: generic\n"
        "domain_defaults:\n"
        "  resistor:\n"
        "    tolerance: '0.1%'\n"
    )

    cfg = load_defaults("minimal", cwd=tmp_path)
    # Package power/voltage still present from generic
    assert cfg.get_package_power("0603") == "100mW"
    assert cfg.get_package_voltage("0603") == "25V"
    # Category route rules still present
    assert cfg.get_category_route_rules("resistor").get("first_sort") == "Resistors"


# ---------------------------------------------------------------------------
# _deep_merge unit tests
# ---------------------------------------------------------------------------


def test_deep_merge_child_overrides_leaf() -> None:
    base = {"a": {"b": "1", "c": "2"}}
    override = {"a": {"b": "99"}}
    result = _deep_merge(base, override)
    assert result == {"a": {"b": "99", "c": "2"}}


def test_deep_merge_list_replaced_not_appended() -> None:
    base = {"items": ["x", "y", "z"]}
    override = {"items": ["a"]}
    result = _deep_merge(base, override)
    assert result == {"items": ["a"]}


def test_deep_merge_new_key_added() -> None:
    base = {"a": "1"}
    override = {"b": "2"}
    result = _deep_merge(base, override)
    assert result == {"a": "1", "b": "2"}


def test_deep_merge_does_not_mutate_base() -> None:
    base = {"a": {"b": "1"}}
    override = {"a": {"c": "2"}}
    result = _deep_merge(base, override)
    assert "c" not in base["a"]
    assert result["a"] == {"b": "1", "c": "2"}


# ---------------------------------------------------------------------------
# from_yaml_dict: parsing edge cases
# ---------------------------------------------------------------------------


def test_from_yaml_dict_tolerates_empty_data() -> None:
    cfg = DefaultsConfig.from_yaml_dict({}, name="empty")
    assert cfg.name == "empty"
    assert cfg.domain_defaults == {}
    assert cfg.package_power == {}
    assert cfg.get_domain_default("resistor", "tolerance", fallback="5%") == "5%"


def test_from_yaml_dict_normalizes_category_to_lowercase() -> None:
    data = {
        "domain_defaults": {"RESISTOR": {"tolerance": "1%"}},
    }
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    assert cfg.get_domain_default("resistor", "tolerance") == "1%"
    assert cfg.get_domain_default("RESISTOR", "tolerance") == "1%"


def test_from_yaml_dict_normalizes_package_to_uppercase() -> None:
    data = {"package_power": {"0603": "100mW"}}
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    assert cfg.get_package_power("0603") == "100mW"
    assert cfg.get_package_power("0603") == "100mW"  # upper key lookup


def test_from_yaml_dict_parses_field_synonyms() -> None:
    data = {
        "field_synonyms": {
            "voltage": {
                "display_name": "Voltage",
                "synonyms": ["Voltage", "V"],
            }
        }
    }
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    voltage = cfg.get_field_synonym_config("voltage")
    assert voltage is not None
    assert voltage.display_name == "Voltage"
    assert voltage.synonyms == ("Voltage", "V")


def test_from_yaml_dict_parses_field_precedence_policy() -> None:
    data = {
        "field_precedence_policy": {
            "schematic_biased": ["value", "tolerance", "value"],
            "pcb_biased": ["footprint", "package"],
        }
    }
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    policy = cfg.get_field_precedence_policy()
    assert policy["schematic_biased"] == ("value", "tolerance")
    assert policy["pcb_biased"] == ("footprint", "package")


def test_from_yaml_dict_parses_search_package_tokens() -> None:
    data = {
        "search": {
            "package_tokens": ["0603", " 0805 ", "0603", "1206"],
        }
    }
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    assert cfg.get_search_package_tokens() == ["0603", "0805", "1206"]


def test_from_yaml_dict_parses_inventory_schema() -> None:
    data = {
        "inventory_schema": {
            "canonical_fields": ["inventory_ipn", "manufacturer_part"],
            "field_synonyms": {
                "inventory_ipn": {
                    "display_name": "IPN",
                    "synonyms": ["ipn"],
                },
                "manufacturer_part": {
                    "display_name": "Manufacturer Part Number",
                    "synonyms": ["mfgpn"],
                },
            },
            "enrichment_bindings": {
                "inventory_ipn": "ipn",
                "manufacturer_part": "mfgpn",
            },
        }
    }
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    schema = cfg.get_inventory_schema()
    assert schema.canonical_fields == ("inventory_ipn", "manufacturer_part")
    assert schema.field_synonyms["inventory_ipn"].display_name == "IPN"
    assert schema.field_synonyms["inventory_ipn"].synonyms == ("ipn",)
    assert (
        schema.field_synonyms["manufacturer_part"].display_name
        == "Manufacturer Part Number"
    )
    assert schema.field_synonyms["manufacturer_part"].synonyms == ("mfgpn",)
    assert schema.enrichment_bindings == {
        "inventory_ipn": "ipn",
        "manufacturer_part": "mfgpn",
    }


# ---------------------------------------------------------------------------
# component_id_fields: parsing and get_component_id_fields()
# ---------------------------------------------------------------------------


def test_generic_profile_has_component_id_fields_for_led() -> None:
    """The built-in generic profile restricts LED ComponentIDs to 'type' only."""
    cfg = load_defaults("generic")
    allowed = cfg.get_component_id_fields("led")
    assert allowed is not None
    assert "type" in allowed
    assert "voltage" not in allowed
    assert "current" not in allowed
    assert "wattage" not in allowed


def test_generic_profile_has_component_id_fields_for_res() -> None:
    """The built-in generic profile includes tolerance/voltage/wattage for RES."""
    cfg = load_defaults("generic")
    allowed = cfg.get_component_id_fields("res")
    assert allowed is not None
    assert "tolerance" in allowed
    assert "voltage" in allowed
    assert "wattage" in allowed
    assert "current" not in allowed


def test_generic_profile_has_component_id_fields_for_cap() -> None:
    """The built-in generic profile includes tolerance/voltage for CAP (no wattage)."""
    cfg = load_defaults("generic")
    allowed = cfg.get_component_id_fields("cap")
    assert allowed is not None
    assert "tolerance" in allowed
    assert "voltage" in allowed
    assert "wattage" not in allowed


def test_generic_profile_has_component_id_fields_for_ind() -> None:
    """The built-in generic profile includes tolerance/current for IND (no voltage)."""
    cfg = load_defaults("generic")
    allowed = cfg.get_component_id_fields("ind")
    assert allowed is not None
    assert "tolerance" in allowed
    assert "current" in allowed
    assert "voltage" not in allowed


def test_get_component_id_fields_returns_none_for_unlisted_category() -> None:
    """A category not in the profile returns None — caller uses all fields."""
    cfg = load_defaults("generic")
    assert cfg.get_component_id_fields("ic") is None
    assert cfg.get_component_id_fields("rly") is None
    assert cfg.get_component_id_fields("totally_custom_cat") is None


def test_get_component_id_fields_is_case_insensitive() -> None:
    """Category lookup is case-insensitive: LED, led, Led all resolve."""
    cfg = load_defaults("generic")
    assert cfg.get_component_id_fields("LED") == cfg.get_component_id_fields("led")
    assert cfg.get_component_id_fields("RES") == cfg.get_component_id_fields("res")


def test_from_yaml_dict_parses_component_id_fields() -> None:
    """from_yaml_dict parses component_id_fields into frozensets of profile names."""
    data = {
        "component_id_fields": {
            "led": ["type"],
            "res": ["tolerance", "voltage", "wattage"],
        }
    }
    cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    assert cfg.get_component_id_fields("led") == frozenset({"type"})
    assert cfg.get_component_id_fields("res") == frozenset(
        {"tolerance", "voltage", "wattage"}
    )
    assert cfg.get_component_id_fields("cap") is None  # not listed


def test_from_yaml_dict_warns_and_skips_unknown_field_names(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown profile names are warned about and omitted from the frozenset."""
    import logging

    data = {
        "component_id_fields": {
            "led": ["type", "wavelength"],  # 'wavelength' is not a known field
        }
    }
    with caplog.at_level(logging.WARNING):
        cfg = DefaultsConfig.from_yaml_dict(data, name="test")
    allowed = cfg.get_component_id_fields("led")
    assert allowed == frozenset({"type"})  # 'wavelength' was dropped
    assert any("wavelength" in r.message for r in caplog.records)


def test_component_id_fields_override_via_jbom_dir(tmp_path: Path) -> None:
    """A project .jbom/ override can customize LED component_id_fields."""
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    (jbom_dir / "custom.defaults.yaml").write_text(
        "extends: generic\n"
        "component_id_fields:\n"
        "  led:\n"
        "    - type\n"
        "    - voltage\n"  # re-add voltage for this project
    )
    cfg = load_defaults("custom", cwd=tmp_path)
    allowed = cfg.get_component_id_fields("led")
    assert allowed is not None
    assert "voltage" in allowed
    assert "type" in allowed
    # res still inherited from generic
    res_allowed = cfg.get_component_id_fields("res")
    assert res_allowed is not None
    assert "tolerance" in res_allowed
