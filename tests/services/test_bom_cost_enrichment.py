"""Unit tests for optional BOM bulk-cost enrichment (#381)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jbom.services.bom_cost_enrichment import (
    cost_field_requested,
    enrich_bom_with_bulk_cost,
    extract_lcsc_identity,
    fixture_row_lookup_from_api_payload,
    resolve_entry_bulk_cost,
)
from jbom.services.bom_field_resolver import resolve_bom_field_value
from jbom.services.bom_generator import BOMData, BOMEntry

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "lcsc"
    / "price_breaks_bulk_c25804.json"
)


@pytest.fixture(scope="module")
def bulk_fixture_lookup():
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return fixture_row_lookup_from_api_payload(payload)


def _entry(*, refs: list[str] | None = None, **attrs: object) -> BOMEntry:
    return BOMEntry(
        references=refs or ["R1"],
        value="10k",
        footprint="Resistor_SMD:R_0603_1608Metric",
        quantity=2,
        lib_id="Device:R",
        attributes=dict(attrs),
    )


def test_cost_field_requested_detects_cost_token() -> None:
    assert cost_field_requested(["reference", "cost", "quantity"]) is True
    assert cost_field_requested(["Cost"]) is True
    assert cost_field_requested(["reference", "value"]) is False
    assert cost_field_requested(None) is False


def test_extract_lcsc_identity_from_common_keys() -> None:
    assert extract_lcsc_identity(_entry(lcsc="C25804")) == "C25804"
    assert extract_lcsc_identity(_entry(LCSC="c25804")) == "C25804"
    assert extract_lcsc_identity(_entry(fabricator_part_number="C25804")) == "C25804"
    assert extract_lcsc_identity(_entry(spn="C25804")) == "C25804"
    assert extract_lcsc_identity(_entry(spn="NOT-LCSC")) == ""
    assert extract_lcsc_identity(_entry()) == ""


def test_resolve_entry_bulk_cost_uses_qty_50_not_qty_one(bulk_fixture_lookup) -> None:
    entry = _entry(lcsc="C25804")
    cost = resolve_entry_bulk_cost(entry, lookup_row=bulk_fixture_lookup, target_qty=50)
    # Fixture: qty1=0.0100, qty50=0.0040
    assert cost == "0.0040"
    assert cost != "0.0100"


def test_resolve_entry_bulk_cost_empty_without_identity(bulk_fixture_lookup) -> None:
    assert resolve_entry_bulk_cost(_entry(), lookup_row=bulk_fixture_lookup) == ""


def test_resolve_entry_bulk_cost_empty_on_lookup_miss() -> None:
    def miss(_code: str):
        return None

    assert resolve_entry_bulk_cost(_entry(lcsc="C99999"), lookup_row=miss) == ""


def test_resolve_entry_bulk_cost_empty_on_lookup_exception() -> None:
    def boom(_code: str):
        raise RuntimeError("network down")

    assert resolve_entry_bulk_cost(_entry(lcsc="C25804"), lookup_row=boom) == ""


def test_enrich_skips_when_cost_not_requested(bulk_fixture_lookup) -> None:
    bom = BOMData(
        project_name="demo",
        entries=[_entry(lcsc="C25804")],
        metadata={},
    )
    result = enrich_bom_with_bulk_cost(
        bom,
        ["reference", "quantity"],
        lookup_row=bulk_fixture_lookup,
    )
    assert result.bom_data is bom
    assert "cost" not in (result.bom_data.entries[0].attributes or {})


def test_enrich_sets_cost_attribute_and_field_resolves(
    bulk_fixture_lookup,
) -> None:
    bom = BOMData(
        project_name="demo",
        entries=[
            _entry(refs=["R1", "R2"], lcsc="C25804"),
            _entry(refs=["C1"], value="100n"),  # no identity
        ],
        metadata={},
    )
    result = enrich_bom_with_bulk_cost(
        bom,
        ["reference", "cost"],
        lookup_row=bulk_fixture_lookup,
        verbose=True,
    )
    assert result.resolved_count == 1
    assert result.skipped_count == 1
    assert result.bom_data.entries[0].attributes["cost"] == "0.0040"
    assert result.bom_data.entries[1].attributes["cost"] == ""
    assert resolve_bom_field_value(result.bom_data.entries[0], "cost") == "0.0040"
    assert resolve_bom_field_value(result.bom_data.entries[1], "cost") == ""
    assert any("bulk qty class" in d.message for d in result.diagnostics)


def test_enrich_does_not_mutate_original_entry_attributes(
    bulk_fixture_lookup,
) -> None:
    original = _entry(lcsc="C25804")
    bom = BOMData(project_name="demo", entries=[original], metadata={})
    enrich_bom_with_bulk_cost(bom, ["cost"], lookup_row=bulk_fixture_lookup)
    assert "cost" not in original.attributes
