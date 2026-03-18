"""Deterministic cross-supplier parity artifact generation for search.

This module intentionally uses committed fixtures (not live supplier APIs) so
evidence generation is reproducible and test-friendly.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.diagnostics import (
    SEARCH_DIAGNOSTICS_CONTRACT_VERSION,
    SearchPipelineDiagnostics,
    run_search_pipeline_with_diagnostics,
)
from jbom.services.search.filtering import search_result_id
from jbom.services.search.models import SearchResult
from jbom.suppliers.lcsc.provider import JlcpcbProvider
from jbom.suppliers.mouser.provider import MouserProvider


PARITY_SUPPLIERS: tuple[str, ...] = ("mouser", "lcsc")
DEFAULT_MATRIX_CSV_RELATIVE_PATH = Path("tests/fixtures/search_parity/matrix.csv")
DEFAULT_DIAGNOSTICS_JSON_RELATIVE_PATH = Path(
    "tests/fixtures/search_parity/diagnostics.json"
)


@dataclass(frozen=True)
class ParityIntentSpec:
    """Fixture-backed query intent to include in parity evidence."""

    intent_id: str
    category: str
    query: str
    mouser_fixture: str
    lcsc_fixture: str


PARITY_INTENTS: tuple[ParityIntentSpec, ...] = (
    ParityIntentSpec(
        intent_id="RES_10K_0603",
        category="RES",
        query="10k resistor 0603",
        mouser_fixture="keyword_resistor_10k_0603.json",
        lcsc_fixture="keyword_resistor_10k_0603.json",
    ),
    ParityIntentSpec(
        intent_id="CAP_1UF_0805",
        category="CAP",
        query="1uF capacitor 0805",
        mouser_fixture="keyword_capacitor_1uf_0805.json",
        lcsc_fixture="keyword_capacitor_1uf_0805.json",
    ),
    ParityIntentSpec(
        intent_id="IND_100UH",
        category="IND",
        query="100uH inductor",
        mouser_fixture="keyword_inductor_100uh.json",
        lcsc_fixture="keyword_inductor_100uh.json",
    ),
    ParityIntentSpec(
        intent_id="LED_GREEN_0603",
        category="LED",
        query="green LED 0603",
        mouser_fixture="keyword_led_green_0603.json",
        lcsc_fixture="keyword_led_green_0603.json",
    ),
    ParityIntentSpec(
        intent_id="CON_HEADER_2X5_254",
        category="CON",
        query="2x5 2.54mm header connector",
        mouser_fixture="keyword_connector_header_2x5_254.json",
        lcsc_fixture="keyword_connector_header_2x5_254.json",
    ),
)


def generate_search_parity_artifacts(
    *,
    fixture_root: Path | None = None,
    max_results_per_supplier: int = 80,
) -> dict[str, Any]:
    """Generate matrix rows + diagnostics payload from deterministic fixtures."""

    root = fixture_root if fixture_root is not None else _default_fixture_root()
    result_cap = max(1, int(max_results_per_supplier))

    matrix_rows: list[dict[str, Any]] = []
    intents_payload: list[dict[str, Any]] = []

    for intent in PARITY_INTENTS:
        supplier_payload: dict[str, Any] = {}
        for supplier in PARITY_SUPPLIERS:
            fixture_filename = _fixture_filename_for_supplier(intent, supplier=supplier)
            fixture_path = root / supplier / fixture_filename
            payload = _load_fixture_payload(fixture_path)
            raw_results = _parse_fixture_results(supplier=supplier, payload=payload)[
                :result_cap
            ]

            ranked, diagnostics = run_search_pipeline_with_diagnostics(
                raw_results,
                query=intent.query,
                category=intent.category,
            )
            summary = _build_summary(ranked=ranked, diagnostics=diagnostics)

            matrix_rows.append(
                {
                    "intent_id": intent.intent_id,
                    "category": intent.category,
                    "query": intent.query,
                    "supplier": supplier,
                    **summary,
                }
            )

            supplier_payload[supplier] = {
                "fixture": str(fixture_path.relative_to(root)),
                "summary": summary,
                "diagnostics": diagnostics.to_dict(),
            }

        intents_payload.append(
            {
                "intent_id": intent.intent_id,
                "category": intent.category,
                "query": intent.query,
                "suppliers": supplier_payload,
            }
        )

    parity_gaps = _summarize_parity_gaps(intents_payload)
    return {
        "contract_version": SEARCH_DIAGNOSTICS_CONTRACT_VERSION,
        "suppliers": list(PARITY_SUPPLIERS),
        "intents": intents_payload,
        "matrix_rows": matrix_rows,
        "parity_gaps": parity_gaps,
    }


def write_search_parity_artifacts(
    *,
    matrix_path: Path,
    diagnostics_path: Path,
    fixture_root: Path | None = None,
    max_results_per_supplier: int = 80,
) -> dict[str, Any]:
    """Generate and write parity matrix CSV + diagnostics JSON artifacts."""

    payload = generate_search_parity_artifacts(
        fixture_root=fixture_root,
        max_results_per_supplier=max_results_per_supplier,
    )
    matrix_rows = payload.get("matrix_rows", [])

    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostics_path.parent.mkdir(parents=True, exist_ok=True)

    _write_matrix_csv(matrix_path, matrix_rows)
    diagnostics_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _default_fixture_root() -> Path:
    return Path(__file__).resolve().parents[4] / "tests" / "fixtures"


def _fixture_filename_for_supplier(intent: ParityIntentSpec, *, supplier: str) -> str:
    if supplier == "mouser":
        return intent.mouser_fixture
    if supplier == "lcsc":
        return intent.lcsc_fixture
    raise ValueError(f"Unsupported supplier for parity artifacts: {supplier}")


def _load_fixture_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Search parity fixture not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"Fixture {path} must contain a JSON object, got {type(payload).__name__}"
        )
    return payload


def _parse_fixture_results(
    *, supplier: str, payload: dict[str, Any]
) -> list[SearchResult]:
    if supplier == "mouser":
        provider = MouserProvider(api_key="fixture")
        return provider._parse_results(payload)
    if supplier == "lcsc":
        provider = JlcpcbProvider(cache=InMemorySearchCache(), rate_limit_seconds=0.0)
        return provider._parse_results(payload)
    raise ValueError(f"Unsupported supplier parser for parity artifacts: {supplier}")


def _build_summary(
    *,
    ranked: list[SearchResult],
    diagnostics: SearchPipelineDiagnostics,
) -> dict[str, Any]:
    top = ranked[0] if ranked else None
    return {
        "raw_count": diagnostics.raw_count,
        "default_filtered_count": diagnostics.default_filtered_count,
        "query_filtered_count": diagnostics.query_filtered_count,
        "ranked_count": diagnostics.ranked_count,
        "success": bool(top),
        "top_result_id": search_result_id(top) if top else "",
        "top_distributor_part_number": (top.distributor_part_number if top else ""),
        "top_mpn": (top.mpn if top else ""),
        "top_manufacturer": (top.manufacturer if top else ""),
        "top_price": (top.price if top else ""),
        "top_stock_quantity": (top.stock_quantity if top else 0),
    }


def _summarize_parity_gaps(
    intents_payload: list[dict[str, Any]]
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for intent in intents_payload:
        suppliers = intent.get("suppliers", {})
        mouser_summary = (
            suppliers.get("mouser", {}).get("summary", {})
            if isinstance(suppliers, dict)
            else {}
        )
        lcsc_summary = (
            suppliers.get("lcsc", {}).get("summary", {})
            if isinstance(suppliers, dict)
            else {}
        )

        mouser_success = bool(mouser_summary.get("success"))
        lcsc_success = bool(lcsc_summary.get("success"))

        if mouser_success != lcsc_success:
            gaps.append(
                {
                    "intent_id": str(intent.get("intent_id", "")),
                    "impact": "high",
                    "reason": "supplier_success_mismatch",
                }
            )
            continue

        if not mouser_success and not lcsc_success:
            gaps.append(
                {
                    "intent_id": str(intent.get("intent_id", "")),
                    "impact": "high",
                    "reason": "both_suppliers_no_ranked_result",
                }
            )
            continue

        mouser_mpn = str(mouser_summary.get("top_mpn", "")).strip().upper()
        lcsc_mpn = str(lcsc_summary.get("top_mpn", "")).strip().upper()
        if mouser_mpn and lcsc_mpn and mouser_mpn != lcsc_mpn:
            gaps.append(
                {
                    "intent_id": str(intent.get("intent_id", "")),
                    "impact": "medium",
                    "reason": "top_result_mpn_mismatch",
                }
            )

    impact_priority = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        gaps,
        key=lambda gap: (
            impact_priority.get(gap.get("impact", "low"), 99),
            gap.get("intent_id", ""),
            gap.get("reason", ""),
        ),
    )


def _write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "intent_id",
        "category",
        "query",
        "supplier",
        "raw_count",
        "default_filtered_count",
        "query_filtered_count",
        "ranked_count",
        "success",
        "top_result_id",
        "top_distributor_part_number",
        "top_mpn",
        "top_manufacturer",
        "top_price",
        "top_stock_quantity",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


__all__ = [
    "DEFAULT_DIAGNOSTICS_JSON_RELATIVE_PATH",
    "DEFAULT_MATRIX_CSV_RELATIVE_PATH",
    "PARITY_INTENTS",
    "PARITY_SUPPLIERS",
    "ParityIntentSpec",
    "generate_search_parity_artifacts",
    "write_search_parity_artifacts",
]
