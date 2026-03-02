from __future__ import annotations

import argparse

from jbom.cli.inventory_search import _build_cache as _build_inventory_cache
from jbom.services.search.cache import DiskSearchCache, InMemorySearchCache


def test_inventory_build_cache_no_cache_flag_returns_inmemory() -> None:
    args = argparse.Namespace(no_cache=True, clear_cache=False)
    cache = _build_inventory_cache("mouser", args)
    assert isinstance(cache, InMemorySearchCache)


def test_inventory_build_cache_clear_cache_flag_calls_clear_provider(
    monkeypatch,
) -> None:
    calls: dict[str, str] = {}

    def _clear_provider(provider_id: str, *, cache_root=None) -> None:
        calls["provider_id"] = provider_id

    monkeypatch.setattr(
        DiskSearchCache, "clear_provider", staticmethod(_clear_provider)
    )

    args = argparse.Namespace(no_cache=True, clear_cache=True)
    cache = _build_inventory_cache("mouser", args)
    assert isinstance(cache, InMemorySearchCache)
    assert calls["provider_id"] == "mouser"
