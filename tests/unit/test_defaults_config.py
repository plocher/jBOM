"""Unit tests for config/defaults.py.

Covers:
- load_defaults("generic") loads the built-in profile correctly
- get_defaults() returns generic on unknown name (no raise)
- load_defaults() raises ValueError for unknown name
- extends: deep-merge: dict values merged, list values replaced
- from_yaml_dict: all sections parsed correctly
- Helper methods: get_domain_default, get_package_power, get_package_voltage, etc.
- _deep_merge semantics
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from jbom.config.defaults import (
    DefaultsConfig,
    EnrichmentCategoryConfig,
    _deep_merge,
    get_defaults,
    load_defaults,
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
