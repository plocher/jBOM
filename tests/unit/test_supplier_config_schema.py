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
    assert "seeed" in suppliers


def test_get_available_suppliers_is_non_empty() -> None:
    assert get_available_suppliers()


def test_load_supplier_lcsc() -> None:
    lcsc = load_supplier("lcsc")
    assert isinstance(lcsc, SupplierConfig)
    assert lcsc.id == "lcsc"
    assert lcsc.name == "LCSC"
    assert lcsc.supplier_label == "LCSC"

    assert lcsc.url_template
    assert lcsc.search_url_template
    assert lcsc.part_number_pattern

    assert lcsc.search_cache_ttl_hours == 24

    # LCSC does not currently override search.fields; it should fall back to generic.
    assert lcsc.search_fields == []

    assert len(lcsc.search_providers) == 1
    assert lcsc.search_providers[0].type == "jlcpcb_api"
    assert lcsc.search_providers[0].extra.get("rate_limit_seconds") == 2

    # LCSC profile includes search.api.* overrides.
    assert lcsc.search_timeout_seconds == 20.0
    assert lcsc.search_max_retries == 3
    assert lcsc.search_retry_delay_seconds == 1.0

    assert isinstance(lcsc.search_type_query_keywords, dict)
    # LCSC profile now provides explicit keyword overrides (issue #163).
    assert lcsc.search_type_query_keywords.get("RES") == "resistor"
    assert lcsc.search_type_query_keywords.get("CAP") == "capacitor"
    assert lcsc.search_type_query_keywords.get("RLY") == "relay"


def test_load_supplier_mouser_has_type_query_keywords() -> None:
    mouser = load_supplier("mouser")
    assert isinstance(mouser.search_type_query_keywords, dict)

    # Contract: the keys are normalized category tokens.
    assert mouser.search_type_query_keywords.get("RES") == "resistor"
    assert mouser.search_type_query_keywords.get("CAP") == "capacitor"
    assert mouser.search_type_query_keywords.get("IND") == "inductor"

    assert len(mouser.search_providers) == 1
    assert mouser.search_providers[0].type == "mouser_api"
    assert mouser.search_providers[0].extra.get("api_key_env") == "MOUSER_API_KEY"


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


def test_load_supplier_generic_has_search_fields() -> None:
    generic = load_supplier("generic")

    assert generic.search_fields == [
        "supplier_part_number",
        "price",
        "stock_quantity",
        "lifecycle_status",
        "description",
    ]
