"""Provider factory for search providers.

This module is the service-layer home for provider instantiation logic,
extracted from the retired ``jbom.cli.inventory_search`` CLI module so that
other service modules (e.g. ``audit_service``) can create providers without
depending on CLI code.
"""

from __future__ import annotations

import argparse
from typing import Optional

from jbom.config.providers import get_provider
from jbom.config.suppliers import load_supplier
from jbom.services.search.cache import DiskSearchCache, InMemorySearchCache, SearchCache
from jbom.services.search.provider import SearchProvider


def create_search_provider(
    supplier_id: str,
    *,
    api_key: Optional[str] = None,
    cache: Optional[SearchCache] = None,
) -> SearchProvider:
    """Instantiate and validate a :class:`SearchProvider` for the given supplier.

    Args:
        supplier_id: Supplier identifier string (e.g. ``'mouser'``, ``'lcsc'``).
        api_key: Optional API key override; injected into the provider config
            when present.
        cache: Optional :class:`SearchCache` instance.  Defaults to
            :class:`DiskSearchCache` keyed to *supplier_id*.

    Returns:
        An available :class:`SearchProvider`.

    Raises:
        ValueError: When the supplier has no configured search providers.
        RuntimeError: When the provider reports itself as unavailable.
    """
    if cache is None:
        cache = DiskSearchCache(supplier_id)

    supplier = load_supplier(supplier_id)
    if not supplier.search_providers:
        raise ValueError(f"Supplier '{supplier_id}' has no configured search providers")

    cfg = supplier.search_providers[0]
    if api_key:
        cfg = cfg.with_extra({"api_key": api_key})

    provider = get_provider(cfg, cache=cache)
    if not provider.available():
        raise RuntimeError(provider.unavailable_reason())

    return provider


def build_search_cache(supplier_id: str, args: argparse.Namespace) -> SearchCache:
    """Build a :class:`SearchCache` from CLI namespace flags.

    Reads the ``no_cache`` and ``clear_cache`` attributes from *args*.

    Args:
        supplier_id: Supplier ID used for :class:`DiskSearchCache` scoping and
            clearing.
        args: Parsed :class:`argparse.Namespace` containing ``no_cache``
            (bool) and ``clear_cache`` (bool) attributes.

    Returns:
        An :class:`InMemorySearchCache` when ``--no-cache`` is set, otherwise a
        :class:`DiskSearchCache`.
    """
    if getattr(args, "clear_cache", False):
        DiskSearchCache.clear_provider(supplier_id)
    if getattr(args, "no_cache", False):
        return InMemorySearchCache()
    return DiskSearchCache(supplier_id)


__all__ = [
    "create_search_provider",
    "build_search_cache",
]
