"""Sophisticated inventory matching service interface.

Phase 1 goal (Task 1.5): define a clean, stable service contract for the
"sophisticated" matcher behavior being ported from legacy jBOM.

This module intentionally contains *no matching implementation yet*.

Design constraints:
- Constructor Configuration Pattern: operational knobs live on MatchingOptions.
- Domain-only: accepts domain objects, not file paths; performs no file I/O.
- Typed outputs: matching results are returned as dataclasses (no tuples/dicts).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from jbom.common.types import Component, InventoryItem


@dataclass(frozen=True)
class MatchingOptions:
    """Configuration for :class:`SophisticatedInventoryMatcher`.

    Attributes:
        include_debug_info: If True, matcher may populate :attr:`MatchResult.debug_info`.
            This should remain domain-safe diagnostic text (no printing).
    """

    include_debug_info: bool = False


@dataclass(frozen=True)
class MatchResult:
    """A single candidate match between a component and an inventory item."""

    inventory_item: InventoryItem
    score: int
    debug_info: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate result invariants."""

        if self.score < 0:
            raise ValueError("score must be >= 0")


class SophisticatedInventoryMatcher:
    """Matches a single :class:`~jbom.common.types.Component` against inventory.

    This service will eventually port the legacy multi-stage algorithm (primary
    filtering + scoring + priority ordering). For Phase 1 Task 1.5 we only define
    the interface.
    """

    def __init__(self, options: MatchingOptions):
        """Create a matcher with a fixed configuration."""

        self._options = options

    def find_matches(
        self, component: Component, inventory: List[InventoryItem]
    ) -> List[MatchResult]:
        """Find matching inventory items for a single component.

        Args:
            component: The schematic component to match.
            inventory: Candidate inventory items to consider.

        Returns:
            Matches sorted best-to-worst according to the legacy algorithm's
            ordering rules (priority, then score).

        Raises:
            NotImplementedError: Until Task 1.5b/1.5c ports the legacy behavior.
        """

        raise NotImplementedError(
            "SophisticatedInventoryMatcher is interface-only (Task 1.5). "
            "Implementation is introduced in Task 1.5b/1.5c."
        )


__all__ = [
    "MatchingOptions",
    "MatchResult",
    "SophisticatedInventoryMatcher",
]
