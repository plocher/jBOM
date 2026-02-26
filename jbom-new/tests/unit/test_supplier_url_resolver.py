"""Unit tests for SupplierUrlResolver service."""

from __future__ import annotations

from jbom.services.supplier_url_resolver import SupplierUrlResolver


def test_resolve_url_lcsc() -> None:
    resolver = SupplierUrlResolver()

    url = resolver.resolve_url("lcsc", "C25231")
    assert url == "https://www.lcsc.com/product-detail/C25231.html"


def test_resolve_search_url_lcsc() -> None:
    resolver = SupplierUrlResolver()

    url = resolver.resolve_search_url("lcsc", "0603 100nF")
    assert url == "https://www.lcsc.com/search?q=0603+100nF"


def test_resolve_url_unknown_supplier_returns_none() -> None:
    resolver = SupplierUrlResolver()

    assert resolver.resolve_url("unknown", "ABC") is None
    assert resolver.resolve_search_url("unknown", "ABC") is None


def test_resolve_url_digikey_not_supported_returns_none() -> None:
    resolver = SupplierUrlResolver()

    assert resolver.resolve_url("digikey", "TPS62133") is None
    assert (
        resolver.resolve_search_url("digikey", "TPS62133")
        == "https://www.digikey.com/en/products?keywords=TPS62133"
    )


def test_resolve_url_encodes_part_number() -> None:
    resolver = SupplierUrlResolver()

    # Encoding behavior is important for safety; whether the target site accepts
    # the encoded form is a supplier-specific detail we can refine later.
    url = resolver.resolve_url("mouser", "ABC/DEF")
    assert url == "https://www.mouser.com/ProductDetail/ABC%2FDEF"
