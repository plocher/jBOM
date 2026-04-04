"""Baseline tests grounded in real KiCad Connector* footprint libraries.

These tests intentionally validate corpus quality and extraction behavior before
heuristic expansion work, so future algorithm changes can be measured against a
practical connector footprint foundation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jbom.common.types import InventoryItem
from jbom.suppliers.lcsc.query_planner import build_parametric_query_plan


_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "connector_footprints"
    / "kicad_connector_footprint_corpus.json"
)
_PITCH_TOKEN_RE = re.compile(r"(?P<pitch>\d+(?:\.\d+)?)mm")
_PINS_TOKEN_RE = re.compile(r"(?P<pins>\d+)-pin")


def _load_corpus_fixture() -> dict[str, object]:
    return json.loads(_FIXTURE_PATH.read_text())


def _inv_item_for_connector_footprint(footprint_full: str) -> InventoryItem:
    return InventoryItem(
        ipn="CON-BASELINE",
        keywords="",
        category="CON",
        description="",
        smd="",
        value="connector",
        type="",
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        lcsc="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package="",
        footprint_full=footprint_full,
        pins="",
        pitch="",
        raw_data={},
    )


def _query_pitch_values(keyword_query: str) -> set[float]:
    return {float(m.group("pitch")) for m in _PITCH_TOKEN_RE.finditer(keyword_query)}


def _query_pin_values(keyword_query: str) -> set[int]:
    return {int(m.group("pins")) for m in _PINS_TOKEN_RE.finditer(keyword_query)}


def test_connector_corpus_fixture_summary_consistency() -> None:
    payload = _load_corpus_fixture()
    records = payload["records"]
    summary = payload["summary"]

    assert payload["schema_version"] == 1
    assert isinstance(records, list)
    assert summary["footprints"] == len(records)
    assert summary["libraries"] == len({r["library"] for r in records})

    # Guardrails: this fixture should stay broadly representative.
    assert summary["libraries"] >= 50
    assert summary["footprints"] >= 7000
    assert summary["with_pitch_strict"] >= 6000
    assert summary["with_pin_grid"] >= 6000
    assert 0.7 <= summary["pin_pad_exact_ratio"] <= 0.9


def test_connector_corpus_contains_common_pitch_families() -> None:
    records = _load_corpus_fixture()["records"]
    pitches = {float(r["pitch_mm_broad"]) for r in records if r["pitch_mm_broad"]}

    # Common connector pitches called out for practical matching work.
    assert 2.54 in pitches
    assert 5.08 in pitches
    assert 3.5 in pitches


def test_query_planner_extracts_pitch_and_pin_tokens_on_real_footprints() -> None:
    payload = _load_corpus_fixture()
    records = payload["records"]

    candidates = [r for r in records if r["pitch_mm_strict"] and r["pin_grid"]]
    assert len(candidates) > 1000

    # Deterministic spread sample across many connector families/libraries.
    sample_size = 240
    step = max(1, len(candidates) // sample_size)
    sampled = candidates[::step][:sample_size]
    assert len(sampled) >= 200

    for record in sampled:
        item = _inv_item_for_connector_footprint(record["footprint_full"])
        plan = build_parametric_query_plan(item, base_query="connector")
        assert plan.use_parametric is True

        pitch_expected = float(record["pitch_mm_strict"])
        pin_expected = int(record["pins_from_name"])
        pitch_values = _query_pitch_values(plan.keyword_query)
        pin_values = _query_pin_values(plan.keyword_query)

        assert pitch_expected in pitch_values
        assert pin_expected in pin_values


def test_real_corpus_highlights_nontrivial_pin_vs_pad_mismatch_population() -> None:
    records = _load_corpus_fixture()["records"]
    paired = [
        r for r in records if r["pins_from_name"] is not None and r["pad_count"] > 0
    ]
    mismatches = [r for r in paired if int(r["pins_from_name"]) != int(r["pad_count"])]

    # This confirms the corpus carries meaningful structural edge cases
    # (mounting pads/shields/etc.) for future heuristic work.
    assert len(mismatches) >= 1000
