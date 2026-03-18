"""Search pipeline diagnostics helpers.

This module exposes a deterministic, test-friendly diagnostics contract for:
- default result filtering decisions
- query-derived parametric filtering decisions
- ranking decisions (including passive-stock gate impact)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jbom.services.search.filtering import (
    SearchFilter,
    SearchFilterDecision,
    SearchRankDecision,
    SearchSorter,
    apply_default_filters,
    describe_default_filter_decisions,
    describe_query_filter_decisions,
    describe_rank_decisions,
    search_result_id,
)
from jbom.services.search.models import SearchResult

SEARCH_DIAGNOSTICS_CONTRACT_VERSION = "1.0"


@dataclass(frozen=True)
class SearchPipelineDiagnostics:
    """Structured diagnostics for one query run through the search pipeline."""

    contract_version: str
    query: str
    category: str
    raw_count: int
    default_filtered_count: int
    query_filtered_count: int
    ranked_count: int
    final_result_ids: tuple[str, ...]
    default_filter_decisions: tuple[SearchFilterDecision, ...]
    query_filter_decisions: tuple[SearchFilterDecision, ...]
    rank_decisions: tuple[SearchRankDecision, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable diagnostics payload."""

        return {
            "contract_version": self.contract_version,
            "query": self.query,
            "category": self.category,
            "raw_count": self.raw_count,
            "default_filtered_count": self.default_filtered_count,
            "query_filtered_count": self.query_filtered_count,
            "ranked_count": self.ranked_count,
            "final_result_ids": list(self.final_result_ids),
            "default_filter_decisions": [
                decision.to_dict() for decision in self.default_filter_decisions
            ],
            "query_filter_decisions": [
                decision.to_dict() for decision in self.query_filter_decisions
            ],
            "rank_decisions": [decision.to_dict() for decision in self.rank_decisions],
        }


def run_search_pipeline_with_diagnostics(
    raw_results: Iterable[SearchResult], *, query: str, category: str = ""
) -> tuple[list[SearchResult], SearchPipelineDiagnostics]:
    """Run the search pipeline and return both ranked results and diagnostics."""

    raw = list(raw_results)
    default_decisions = describe_default_filter_decisions(raw)
    default_filtered = apply_default_filters(raw)

    query_decisions = describe_query_filter_decisions(
        default_filtered, query, category=category
    )
    query_filtered = SearchFilter.filter_by_query(
        default_filtered, query, category=category
    )

    ranked = SearchSorter.rank(query_filtered, category=category, query=query)
    rank_decisions = describe_rank_decisions(
        query_filtered, category=category, query=query
    )

    diagnostics = SearchPipelineDiagnostics(
        contract_version=SEARCH_DIAGNOSTICS_CONTRACT_VERSION,
        query=query,
        category=category,
        raw_count=len(raw),
        default_filtered_count=len(default_filtered),
        query_filtered_count=len(query_filtered),
        ranked_count=len(ranked),
        final_result_ids=tuple(search_result_id(result) for result in ranked),
        default_filter_decisions=tuple(default_decisions),
        query_filter_decisions=tuple(query_decisions),
        rank_decisions=tuple(rank_decisions),
    )
    return ranked, diagnostics


def build_search_pipeline_diagnostics(
    raw_results: Iterable[SearchResult], *, query: str, category: str = ""
) -> SearchPipelineDiagnostics:
    """Build diagnostics only for one search query."""

    _ranked, diagnostics = run_search_pipeline_with_diagnostics(
        raw_results, query=query, category=category
    )
    return diagnostics


__all__ = [
    "SEARCH_DIAGNOSTICS_CONTRACT_VERSION",
    "SearchPipelineDiagnostics",
    "build_search_pipeline_diagnostics",
    "run_search_pipeline_with_diagnostics",
]
