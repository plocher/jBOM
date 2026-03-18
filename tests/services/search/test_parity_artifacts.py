from __future__ import annotations

import json

from jbom.services.search.diagnostics import SEARCH_DIAGNOSTICS_CONTRACT_VERSION
from jbom.services.search.parity_artifacts import (
    PARITY_SUPPLIERS,
    generate_search_parity_artifacts,
    write_search_parity_artifacts,
)


def test_parity_artifact_generation_covers_required_categories_and_suppliers() -> None:
    payload = generate_search_parity_artifacts(max_results_per_supplier=40)

    assert payload["suppliers"] == list(PARITY_SUPPLIERS)

    intents = payload["intents"]
    categories = {intent["category"] for intent in intents}
    assert categories == {"RES", "CAP", "IND", "LED"}

    matrix_rows = payload["matrix_rows"]
    assert len(matrix_rows) == len(intents) * len(PARITY_SUPPLIERS)

    for intent in intents:
        assert set(intent["suppliers"].keys()) == set(PARITY_SUPPLIERS)
        for supplier in PARITY_SUPPLIERS:
            summary = intent["suppliers"][supplier]["summary"]
            assert summary["raw_count"] >= summary["ranked_count"]
            assert summary["default_filtered_count"] >= summary["ranked_count"]


def test_search_diagnostics_contract_shape_regression() -> None:
    payload = generate_search_parity_artifacts(max_results_per_supplier=20)
    first_intent = payload["intents"][0]
    first_supplier = PARITY_SUPPLIERS[0]
    diagnostics = first_intent["suppliers"][first_supplier]["diagnostics"]

    assert diagnostics["contract_version"] == SEARCH_DIAGNOSTICS_CONTRACT_VERSION
    assert set(diagnostics.keys()) == {
        "contract_version",
        "query",
        "category",
        "raw_count",
        "default_filtered_count",
        "query_filtered_count",
        "ranked_count",
        "final_result_ids",
        "default_filter_decisions",
        "query_filter_decisions",
        "rank_decisions",
    }

    default_decision = diagnostics["default_filter_decisions"][0]
    assert set(default_decision.keys()) == {"result_id", "kept", "reasons"}

    query_decision = diagnostics["query_filter_decisions"][0]
    assert set(query_decision.keys()) == {"result_id", "kept", "reasons"}

    rank_decision = diagnostics["rank_decisions"][0]
    assert set(rank_decision.keys()) == {
        "result_id",
        "included",
        "rank",
        "passive_stock_gate_kept",
        "relevance_score",
        "price_value",
        "canonical_value",
        "component_library_tier",
    }


def test_write_search_parity_artifacts_emits_expected_files(tmp_path) -> None:
    matrix_path = tmp_path / "matrix.csv"
    diagnostics_path = tmp_path / "diagnostics.json"

    payload = write_search_parity_artifacts(
        matrix_path=matrix_path,
        diagnostics_path=diagnostics_path,
        max_results_per_supplier=25,
    )

    assert matrix_path.exists()
    assert diagnostics_path.exists()

    loaded = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    assert loaded["contract_version"] == payload["contract_version"]
    assert loaded["parity_gaps"] == payload["parity_gaps"]
