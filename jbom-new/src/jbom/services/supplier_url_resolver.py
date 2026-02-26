"""Supplier URL resolution service.

Phase 4S introduces supplier profiles which can generate:
- Direct product page URLs (when derivable)
- Search URLs (for browser/interactive lookup)

This service is intentionally small and stateless.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, quote_plus

from jbom.config.suppliers import SupplierConfig, resolve_supplier_by_id


@dataclass(frozen=True)
class SupplierUrlResolver:
    """Generate supplier URLs from a supplier profile and input strings."""

    encode: bool = True

    def resolve_url(self, supplier_id: str, part_number: str) -> Optional[str]:
        """Generate supplier product URL from part number.

        Returns None when:
        - supplier_id is unknown
        - supplier has no url_template
        - part_number is empty
        """

        supplier = resolve_supplier_by_id(supplier_id)
        if supplier is None:
            return None

        return self._resolve_url_for_supplier(supplier, part_number)

    def resolve_search_url(self, supplier_id: str, query: str) -> Optional[str]:
        """Generate supplier search URL."""

        supplier = resolve_supplier_by_id(supplier_id)
        if supplier is None:
            return None

        return self._resolve_search_url_for_supplier(supplier, query)

    def _resolve_url_for_supplier(
        self, supplier: SupplierConfig, part_number: str
    ) -> Optional[str]:
        template = (supplier.url_template or "").strip()
        if not template:
            return None

        pn = (part_number or "").strip()
        if not pn:
            return None

        if self.encode:
            pn = quote(pn, safe="")

        try:
            return template.format(pn=pn)
        except KeyError as e:
            raise ValueError(
                f"Supplier '{supplier.id}' url_template is missing required placeholders: {e}"
            ) from e

    def _resolve_search_url_for_supplier(
        self, supplier: SupplierConfig, query: str
    ) -> Optional[str]:
        template = (supplier.search_url_template or "").strip()
        if not template:
            return None

        q = (query or "").strip()
        if not q:
            return None

        if self.encode:
            q = quote_plus(q, safe="")

        try:
            return template.format(query=q)
        except KeyError as e:
            raise ValueError(
                f"Supplier '{supplier.id}' search_url_template is missing required placeholders: {e}"
            ) from e
