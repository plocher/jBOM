from __future__ import annotations

import json
from pathlib import Path

from jbom.services.search.parity_artifacts import generate_search_parity_artifacts
from jbom.services.search.parity_delta import (
    PARITY_DELTA_CONTRACT_VERSION,
    compare_parity_payloads,
    write_parity_delta_artifacts,
)


def test_compare_parity_payloads_marks_new_intent_as_improved() -> None:
    baseline = {
        "intents": [],
        "parity_gaps": [],
    }
    candidate = {
        "intents": [
            {
                "intent_id": "CON_HEADER_2X5_254",
                "category": "CON",
                "query": "2x5 2.54mm header connector",
                "suppliers": {
                    "mouser": {"summary": {"success": True, "ranked_count": 1}},
                    "lcsc": {"summary": {"success": True, "ranked_count": 1}},
                },
            }
        ],
        "parity_gaps": [],
    }

    report = compare_parity_payloads(baseline, candidate)

    assert report["summary"]["improved_count"] == 1
    assert report["summary"]["regressed_count"] == 0
    assert report["improved"][0]["intent_id"] == "CON_HEADER_2X5_254"
    assert report["improved"][0]["reason"] == "new_intent_added"


def test_compare_parity_payloads_detects_success_regression() -> None:
    baseline = {
        "intents": [
            {
                "intent_id": "LED_GREEN_0603",
                "category": "LED",
                "query": "green LED 0603",
                "suppliers": {
                    "mouser": {"summary": {"success": True, "ranked_count": 1}},
                    "lcsc": {"summary": {"success": True, "ranked_count": 1}},
                },
            }
        ],
        "parity_gaps": [],
    }
    candidate = {
        "intents": [
            {
                "intent_id": "LED_GREEN_0603",
                "category": "LED",
                "query": "green LED 0603",
                "suppliers": {
                    "mouser": {"summary": {"success": True, "ranked_count": 1}},
                    "lcsc": {"summary": {"success": False, "ranked_count": 0}},
                },
            }
        ],
        "parity_gaps": [
            {
                "intent_id": "LED_GREEN_0603",
                "impact": "high",
                "reason": "supplier_success_mismatch",
            }
        ],
    }

    report = compare_parity_payloads(baseline, candidate)

    assert report["summary"]["regressed_count"] == 1
    assert report["regressed"][0]["intent_id"] == "LED_GREEN_0603"
    assert report["regressed"][0]["reason"] == "supplier_success_regressed"


def test_write_parity_delta_artifacts_with_baseline_snapshot(tmp_path: Path) -> None:
    baseline_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "search_parity"
        / "baseline_issue_199"
        / "diagnostics.json"
    )
    candidate_payload = generate_search_parity_artifacts(max_results_per_supplier=30)
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(
        json.dumps(candidate_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    delta_json = tmp_path / "delta.json"
    delta_csv = tmp_path / "delta.csv"
    report = write_parity_delta_artifacts(
        baseline_diagnostics_path=baseline_path,
        candidate_diagnostics_path=candidate_path,
        delta_json_path=delta_json,
        delta_csv_path=delta_csv,
    )

    assert delta_json.exists()
    assert delta_csv.exists()

    loaded = json.loads(delta_json.read_text(encoding="utf-8"))
    assert loaded["contract_version"] == PARITY_DELTA_CONTRACT_VERSION
    assert loaded["summary"] == report["summary"]
    assert any(row["intent_id"] == "CON_HEADER_2X5_254" for row in loaded["improved"])
