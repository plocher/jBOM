"""Unit tests for shared reference sorting helpers."""

from jbom.common.reference_sort import (
    natural_reference_sort_key,
    natural_sort_references,
)


def test_natural_sort_references_orders_numeric_suffixes() -> None:
    """Natural sorting should order numeric suffixes by integer value."""

    references = ["J10", "J2", "J1"]

    assert natural_sort_references(references) == ["J1", "J2", "J10"]


def test_natural_reference_sort_key_orders_prefixes_before_suffixes() -> None:
    """Natural key sorting should prioritize alphabetic prefixes consistently."""

    references = ["IO1", "GND0", "LEDCOM0"]

    assert sorted(references, key=natural_reference_sort_key) == [
        "GND0",
        "IO1",
        "LEDCOM0",
    ]
