"""Baseline-vs-candidate parity delta reporting for search evidence artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

PARITY_DELTA_CONTRACT_VERSION = "1.0"


def compare_parity_payloads(
    baseline_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
) -> dict[str, Any]:
    """Compare baseline and candidate parity payloads into bucketed deltas."""

    baseline_intents = _intent_map(baseline_payload)
    candidate_intents = _intent_map(candidate_payload)
    baseline_gap_map = _gap_reason_map(baseline_payload)
    candidate_gap_map = _gap_reason_map(candidate_payload)

    all_intent_ids = sorted(set(baseline_intents) | set(candidate_intents))
    improved: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    regressed: list[dict[str, Any]] = []

    for intent_id in all_intent_ids:
        baseline_intent = baseline_intents.get(intent_id)
        candidate_intent = candidate_intents.get(intent_id)
        delta_row = _build_intent_delta(
            intent_id=intent_id,
            baseline_intent=baseline_intent,
            candidate_intent=candidate_intent,
            baseline_gap_reasons=baseline_gap_map.get(intent_id, []),
            candidate_gap_reasons=candidate_gap_map.get(intent_id, []),
        )
        status = delta_row["status"]
        if status == "improved":
            improved.append(delta_row)
        elif status == "regressed":
            regressed.append(delta_row)
        else:
            unchanged.append(delta_row)

    contract_mismatches = [
        {
            "intent_id": row["intent_id"],
            "category": row["category"],
            "baseline_gap_reasons": row["baseline_gap_reasons"],
            "candidate_gap_reasons": row["candidate_gap_reasons"],
            "gap_reasons_changed": row["gap_reasons_changed"],
        }
        for row in improved + unchanged + regressed
        if row["candidate_gap_reasons"] or row["baseline_gap_reasons"]
    ]

    return {
        "contract_version": PARITY_DELTA_CONTRACT_VERSION,
        "summary": {
            "total_intents": len(all_intent_ids),
            "improved_count": len(improved),
            "unchanged_count": len(unchanged),
            "regressed_count": len(regressed),
        },
        "improved": improved,
        "unchanged": unchanged,
        "regressed": regressed,
        "contract_mismatches": contract_mismatches,
    }


def write_parity_delta_artifacts(
    *,
    baseline_diagnostics_path: Path,
    candidate_diagnostics_path: Path,
    delta_json_path: Path,
    delta_csv_path: Path,
) -> dict[str, Any]:
    """Compare baseline/candidate diagnostics and write JSON + CSV delta artifacts."""

    baseline_payload = _read_payload(baseline_diagnostics_path)
    candidate_payload = _read_payload(candidate_diagnostics_path)
    report = compare_parity_payloads(baseline_payload, candidate_payload)

    delta_json_path.parent.mkdir(parents=True, exist_ok=True)
    delta_csv_path.parent.mkdir(parents=True, exist_ok=True)
    delta_json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_delta_csv(delta_csv_path, report)
    return report


def _build_intent_delta(
    *,
    intent_id: str,
    baseline_intent: dict[str, Any] | None,
    candidate_intent: dict[str, Any] | None,
    baseline_gap_reasons: list[str],
    candidate_gap_reasons: list[str],
) -> dict[str, Any]:
    baseline_exists = baseline_intent is not None
    candidate_exists = candidate_intent is not None

    category = str(
        (candidate_intent or baseline_intent or {}).get("category", "")
    ).strip()
    query = str((candidate_intent or baseline_intent or {}).get("query", "")).strip()
    baseline_summary = _supplier_summary_map(baseline_intent)
    candidate_summary = _supplier_summary_map(candidate_intent)

    baseline_success = {
        supplier: bool(summary.get("success"))
        for supplier, summary in baseline_summary.items()
    }
    candidate_success = {
        supplier: bool(summary.get("success"))
        for supplier, summary in candidate_summary.items()
    }

    baseline_ranked_total = sum(
        int(summary.get("ranked_count", 0)) for summary in baseline_summary.values()
    )
    candidate_ranked_total = sum(
        int(summary.get("ranked_count", 0)) for summary in candidate_summary.values()
    )

    baseline_top_mpn = {
        supplier: str(summary.get("top_mpn", ""))
        for supplier, summary in baseline_summary.items()
    }
    candidate_top_mpn = {
        supplier: str(summary.get("top_mpn", ""))
        for supplier, summary in candidate_summary.items()
    }

    status = "unchanged"
    reason = "equivalent_outcome"
    gap_changed = sorted(set(baseline_gap_reasons)) != sorted(
        set(candidate_gap_reasons)
    )

    if not baseline_exists and candidate_exists:
        status = "improved"
        reason = "new_intent_added"
    elif baseline_exists and not candidate_exists:
        status = "regressed"
        reason = "intent_removed"
    else:
        suppliers = sorted(set(baseline_success) | set(candidate_success))
        if any(
            baseline_success.get(supplier, False)
            and not candidate_success.get(supplier, False)
            for supplier in suppliers
        ):
            status = "regressed"
            reason = "supplier_success_regressed"
        elif any(
            not baseline_success.get(supplier, False)
            and candidate_success.get(supplier, False)
            for supplier in suppliers
        ):
            status = "improved"
            reason = "supplier_success_improved"
        elif len(candidate_gap_reasons) < len(baseline_gap_reasons):
            status = "improved"
            reason = "contract_mismatch_reduced"
        elif len(candidate_gap_reasons) > len(baseline_gap_reasons):
            status = "regressed"
            reason = "contract_mismatch_increased"
        elif candidate_ranked_total > baseline_ranked_total:
            status = "improved"
            reason = "ranked_candidate_count_increased"
        elif candidate_ranked_total < baseline_ranked_total:
            status = "regressed"
            reason = "ranked_candidate_count_decreased"

    return {
        "intent_id": intent_id,
        "category": category,
        "query": query,
        "status": status,
        "reason": reason,
        "baseline_exists": baseline_exists,
        "candidate_exists": candidate_exists,
        "baseline_success_by_supplier": baseline_success,
        "candidate_success_by_supplier": candidate_success,
        "baseline_ranked_total": baseline_ranked_total,
        "candidate_ranked_total": candidate_ranked_total,
        "baseline_top_mpn_by_supplier": baseline_top_mpn,
        "candidate_top_mpn_by_supplier": candidate_top_mpn,
        "baseline_gap_reasons": sorted(set(baseline_gap_reasons)),
        "candidate_gap_reasons": sorted(set(candidate_gap_reasons)),
        "gap_reasons_changed": gap_changed,
    }


def _intent_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    intents = payload.get("intents", [])
    if not isinstance(intents, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for intent in intents:
        if not isinstance(intent, dict):
            continue
        intent_id = str(intent.get("intent_id", "")).strip()
        if intent_id:
            out[intent_id] = intent
    return out


def _gap_reason_map(payload: dict[str, Any]) -> dict[str, list[str]]:
    gaps = payload.get("parity_gaps", [])
    if not isinstance(gaps, list):
        return {}
    out: dict[str, list[str]] = {}
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        intent_id = str(gap.get("intent_id", "")).strip()
        reason = str(gap.get("reason", "")).strip()
        if not intent_id:
            continue
        out.setdefault(intent_id, [])
        if reason:
            out[intent_id].append(reason)
    return out


def _supplier_summary_map(intent: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if intent is None:
        return {}
    suppliers = intent.get("suppliers", {})
    if not isinstance(suppliers, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for supplier, payload in suppliers.items():
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary", {})
        if isinstance(summary, dict):
            out[str(supplier)] = summary
    return out


def _read_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            f"Parity diagnostics payload at {path} must be a JSON object, got {type(payload).__name__}"
        )
    return payload


def _write_delta_csv(path: Path, report: dict[str, Any]) -> None:
    rows = (
        list(report.get("improved", []))
        + list(report.get("unchanged", []))
        + list(report.get("regressed", []))
    )
    fieldnames = [
        "intent_id",
        "category",
        "status",
        "reason",
        "baseline_exists",
        "candidate_exists",
        "baseline_ranked_total",
        "candidate_ranked_total",
        "baseline_gap_reasons",
        "candidate_gap_reasons",
        "gap_reasons_changed",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "intent_id": row.get("intent_id", ""),
                    "category": row.get("category", ""),
                    "status": row.get("status", ""),
                    "reason": row.get("reason", ""),
                    "baseline_exists": row.get("baseline_exists", False),
                    "candidate_exists": row.get("candidate_exists", False),
                    "baseline_ranked_total": row.get("baseline_ranked_total", 0),
                    "candidate_ranked_total": row.get("candidate_ranked_total", 0),
                    "baseline_gap_reasons": "|".join(
                        row.get("baseline_gap_reasons", [])
                    ),
                    "candidate_gap_reasons": "|".join(
                        row.get("candidate_gap_reasons", [])
                    ),
                    "gap_reasons_changed": row.get("gap_reasons_changed", False),
                }
            )


__all__ = [
    "PARITY_DELTA_CONTRACT_VERSION",
    "compare_parity_payloads",
    "write_parity_delta_artifacts",
]
