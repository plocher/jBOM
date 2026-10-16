"""LCSC/JLCPCB price-break helpers for BOM cost enrichment.

JLCPCB search rows expose ``componentPrices`` as a list of
``{productNumber, productPrice}`` breaks. Qty-1 unit prices are often
inflated relative to realistic fab buys; BOM ``cost`` therefore defaults
to a bulk break in the qty-20/50 class (charter Q5 / issue #381).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

# Default bulk class used when BOM requests the optional ``cost`` field.
# Prefer the break that applies at this quantity (largest break qty <= target).
DEFAULT_BULK_BREAK_QTY: int = 50

# Documented bulk-class anchors (qty-20 and qty-50 style buys).
BULK_BREAK_CLASS_QTYS: tuple[int, ...] = (20, 50)


def _parse_break(raw: Mapping[str, Any]) -> tuple[int, str] | None:
    """Parse one price-break mapping into ``(qty, price_text)``."""

    if not isinstance(raw, Mapping):
        return None

    qty_raw = raw.get("productNumber", raw.get("qty", raw.get("quantity")))
    price_raw = raw.get("productPrice", raw.get("price"))
    if qty_raw is None or price_raw is None:
        return None

    try:
        qty = int(qty_raw)
    except (TypeError, ValueError):
        return None
    if qty <= 0:
        return None

    price_text = str(price_raw).strip()
    if not price_text or price_text.upper() == "N/A":
        return None
    try:
        float(price_text)
    except (TypeError, ValueError):
        return None

    return qty, price_text


def parse_price_breaks(
    price_breaks: Sequence[Any] | None,
) -> list[tuple[int, str]]:
    """Return sorted ``(qty, price)`` pairs from a raw ``componentPrices`` list."""

    if not price_breaks or isinstance(price_breaks, (str, bytes)):
        return []
    if not isinstance(price_breaks, Sequence):
        return []

    parsed: list[tuple[int, str]] = []
    for item in price_breaks:
        if not isinstance(item, Mapping):
            continue
        pair = _parse_break(item)
        if pair is not None:
            parsed.append(pair)

    parsed.sort(key=lambda item: item[0])
    return parsed


def select_bulk_unit_price(
    price_breaks: Sequence[Any] | None,
    *,
    target_qty: int = DEFAULT_BULK_BREAK_QTY,
) -> str:
    """Select a unit price at the bulk break class for ``target_qty``.

    Picks the break with the largest ``productNumber`` that is still
    ``<= target_qty`` (the unit price that applies when buying that many).
    If every break is above ``target_qty``, uses the smallest available
    break so a price is still returned when the catalog only publishes
    larger MOQ tiers.

    Args:
        price_breaks: Raw ``componentPrices`` list from a JLCPCB row, or
            any sequence of mappings with qty/price keys.
        target_qty: Bulk quantity class (default 50). Values ``<= 0`` fall
            back to :data:`DEFAULT_BULK_BREAK_QTY`.

    Returns:
        Unit price as a plain decimal string (e.g. ``\"0.0123\"``), or
        ``\"\"`` when no parseable breaks exist.
    """

    breaks = parse_price_breaks(price_breaks)
    if not breaks:
        return ""

    qty_target = int(target_qty) if int(target_qty) > 0 else DEFAULT_BULK_BREAK_QTY

    applicable = [pair for pair in breaks if pair[0] <= qty_target]
    if applicable:
        return applicable[-1][1]

    # All breaks are above the target (unusual MOQ ladder) — take the
    # cheapest entry tier rather than inventing a price.
    return breaks[0][1]


def select_bulk_unit_price_from_row(
    row: Mapping[str, Any] | None,
    *,
    target_qty: int = DEFAULT_BULK_BREAK_QTY,
) -> str:
    """Select bulk unit price from a JLCPCB component row mapping."""

    if not isinstance(row, Mapping):
        return ""
    return select_bulk_unit_price(row.get("componentPrices"), target_qty=target_qty)


__all__ = [
    "BULK_BREAK_CLASS_QTYS",
    "DEFAULT_BULK_BREAK_QTY",
    "parse_price_breaks",
    "select_bulk_unit_price",
    "select_bulk_unit_price_from_row",
]
