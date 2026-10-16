"""Unit tests for LCSC bulk-break unit price selection (#381)."""

from __future__ import annotations

from jbom.suppliers.lcsc.pricing import (
    DEFAULT_BULK_BREAK_QTY,
    parse_price_breaks,
    select_bulk_unit_price,
    select_bulk_unit_price_from_row,
)


def test_default_bulk_break_qty_is_fifty_class() -> None:
    assert DEFAULT_BULK_BREAK_QTY == 50


def test_select_bulk_prefers_break_at_or_below_target_not_qty_one() -> None:
    breaks = [
        {"productPrice": "0.1000", "productNumber": 1},
        {"productPrice": "0.0500", "productNumber": 10},
        {"productPrice": "0.0200", "productNumber": 50},
        {"productPrice": "0.0150", "productNumber": 100},
    ]

    # Qty-50 class must not return the inflated qty-1 price.
    assert select_bulk_unit_price(breaks, target_qty=50) == "0.0200"
    assert select_bulk_unit_price(breaks, target_qty=20) == "0.0500"
    assert select_bulk_unit_price(breaks) == "0.0200"


def test_select_bulk_uses_largest_break_not_exceeding_target() -> None:
    breaks = [
        {"productPrice": "0.08", "productNumber": 1},
        {"productPrice": "0.04", "productNumber": 25},
        {"productPrice": "0.03", "productNumber": 100},
    ]
    # target 50 → break 25 applies (100 does not yet).
    assert select_bulk_unit_price(breaks, target_qty=50) == "0.04"


def test_select_bulk_falls_back_to_qty_one_when_only_break() -> None:
    breaks = [{"productPrice": "0.99", "productNumber": 1}]
    assert select_bulk_unit_price(breaks, target_qty=50) == "0.99"


def test_select_bulk_empty_or_garbage_returns_empty_string() -> None:
    assert select_bulk_unit_price(None) == ""
    assert select_bulk_unit_price([]) == ""
    assert select_bulk_unit_price([{"productPrice": "x"}]) == ""
    assert select_bulk_unit_price([{"productNumber": 10}]) == ""
    assert select_bulk_unit_price("not-a-list") == ""  # type: ignore[arg-type]


def test_parse_price_breaks_sorted_and_skips_invalid() -> None:
    parsed = parse_price_breaks(
        [
            {"productPrice": "0.02", "productNumber": 50},
            {"productPrice": "bad", "productNumber": 10},
            {"productPrice": "0.05", "productNumber": 10},
            {"nope": True},
        ]
    )
    assert parsed == [(10, "0.05"), (50, "0.02")]


def test_select_bulk_from_jlcpcb_row() -> None:
    row = {
        "componentCode": "C25804",
        "componentPrices": [
            {"productPrice": "0.004", "productNumber": 1},
            {"productPrice": "0.0025", "productNumber": 50},
        ],
    }
    assert select_bulk_unit_price_from_row(row) == "0.0025"
    assert select_bulk_unit_price_from_row(None) == ""
