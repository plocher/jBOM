"""
Search provider abstraction for external part search APIs.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class SearchResult:
    """Standardized search result item."""

    manufacturer: str
    mpn: str
    description: str
    datasheet: str
    distributor: str
    distributor_part_number: str
    availability: str
    price: str
    details_url: str
    raw_data: Dict[str, Any]

    # Enhanced fields
    lifecycle_status: str = "Unknown"
    min_order_qty: int = 1
    category: str = ""
    attributes: Dict[str, str] = None  # Parametric data (Resistance, Tolerance, etc.)
    stock_quantity: int = 0  # Numeric stock for sorting

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


class SearchProvider(ABC):
    """Abstract base class for part search providers."""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search for parts by keyword or part number."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
