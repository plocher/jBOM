"""Unit tests for SupplierConfig schema parsing and loader behavior."""

from __future__ import annotations

import pytest

from jbom.config.suppliers import (
    SupplierConfig,
    get_available_suppliers,
    list_suppliers,
    load_supplier,
    validate_part_number,
)


def test_list_suppliers_includes_builtin_profiles() -> None:
    suppliers = list_suppliers()
    assert isinstance(suppliers, list)
    assert "generic" in suppliers
    assert "lcsc" in suppliers
    assert "mouser" in suppliers
    assert "digikey" in suppliers


def test_get_available_suppliers_is_non_empty() -> None:
    assert get_available_suppliers()


def test_load_supplier_lcsc() -> None:
    lcsc = load_supplier("lcsc")
    assert isinstance(lcsc, SupplierConfig)
    assert lcsc.id == "lcsc"
    assert lcsc.name == "LCSC"
    assert lcsc.inventory_column == "LCSC"
    assert lcsc.url_template
    assert lcsc.search_url_template
    assert lcsc.part_number_pattern

    assert lcsc.search_cache_ttl_hours == 24

    assert isinstance(lcsc.search_type_query_keywords, dict)
    assert lcsc.search_type_query_keywords == {}


def test_load_supplier_mouser_has_type_query_keywords() -> None:
    mouser = load_supplier("mouser")
    assert isinstance(mouser.search_type_query_keywords, dict)

    # Contract: the keys are normalized category tokens.
    assert mouser.search_type_query_keywords.get("RES") == "resistor"
    assert mouser.search_type_query_keywords.get("CAP") == "capacitor"
    assert mouser.search_type_query_keywords.get("IND") == "inductor"


def test_load_unknown_supplier_raises() -> None:
    with pytest.raises(ValueError, match=r"Unknown supplier"):
        load_supplier("does-not-exist")


def test_validate_part_number_with_pattern() -> None:
    lcsc = load_supplier("lcsc")

    assert validate_part_number(lcsc, "C25231") is True
    assert validate_part_number(lcsc, "c25231") is False
    assert validate_part_number(lcsc, "25231") is False


def test_validate_part_number_without_pattern_is_advisory() -> None:
    generic = load_supplier("generic")

    assert validate_part_number(generic, "ANYTHING") is True
    assert validate_part_number(generic, "") is False
