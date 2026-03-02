from __future__ import annotations

import pytest

from jbom.config.providers import SearchProviderConfig, get_provider
from jbom.services.search.cache import InMemorySearchCache
from jbom.services.search.jlcparts_provider import JlcpartsProvider
from jbom.services.search.mouser_provider import MouserProvider


def test_get_provider_unknown_type_raises() -> None:
    cfg = SearchProviderConfig(type="does_not_exist", extra={})
    with pytest.raises(ValueError, match=r"Unknown provider type"):
        get_provider(cfg, cache=InMemorySearchCache())


def test_get_provider_mouser_api_dispatches() -> None:
    cfg = SearchProviderConfig(type="mouser_api", extra={"api_key": "dummy"})
    provider = get_provider(cfg, cache=InMemorySearchCache())
    assert isinstance(provider, MouserProvider)


def test_get_provider_jlcparts_sqlite_dispatches() -> None:
    cfg = SearchProviderConfig(
        type="jlcparts_sqlite",
        extra={"db_path": "~/.cache/jbom/jlcparts/components.db"},
    )
    provider = get_provider(cfg, cache=InMemorySearchCache())
    assert isinstance(provider, JlcpartsProvider)
    assert provider.available() is False
    assert "not yet implemented" in provider.unavailable_reason().lower()
