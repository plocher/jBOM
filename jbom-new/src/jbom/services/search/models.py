"""Search domain models.

These dataclasses normalize data returned by distributor APIs so the rest of the
application can stay provider-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    """A single normalized distributor catalog result."""

    manufacturer: str
    mpn: str
    description: str
    datasheet: str

    distributor: str
    distributor_part_number: str

    availability: str
    price: str
    details_url: str

    raw_data: dict[str, Any]

    lifecycle_status: str = "Unknown"
    min_order_qty: int = 1
    category: str = ""

    # Parametric attributes (e.g. Resistance, Tolerance, Technology)
    attributes: dict[str, str] = field(default_factory=dict)

    # Numeric stock quantity extracted from availability, when possible.
    stock_quantity: int = 0


__all__ = ["SearchResult"]
