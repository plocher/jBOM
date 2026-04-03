"""Typed heuristic signal contracts for search relevance evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from jbom.services.search.models import SearchResult

SignalEvaluator = Callable[[SearchResult], int]


@dataclass(frozen=True)
class SearchRelevanceSignal:
    """One named relevance signal contribution for a result."""

    key: str
    contribution: int

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable mapping."""

        return {
            "key": self.key,
            "contribution": self.contribution,
        }


@dataclass(frozen=True)
class SearchRelevanceEvaluation:
    """Aggregated relevance evaluation with per-signal explainability."""

    score: int
    signals: tuple[SearchRelevanceSignal, ...]


def evaluate_relevance_signals(
    result: SearchResult,
    *,
    evaluators: Iterable[tuple[str, SignalEvaluator]],
    include_zero_contributions: bool = False,
) -> SearchRelevanceEvaluation:
    """Evaluate and aggregate named relevance signals for one result."""

    signals: list[SearchRelevanceSignal] = []
    score = 0
    for key, evaluator in evaluators:
        contribution = int(evaluator(result))
        score += contribution
        if contribution != 0 or include_zero_contributions:
            signals.append(SearchRelevanceSignal(key=key, contribution=contribution))
    return SearchRelevanceEvaluation(score=score, signals=tuple(signals))


__all__ = [
    "SearchRelevanceEvaluation",
    "SearchRelevanceSignal",
    "evaluate_relevance_signals",
]
