from __future__ import annotations

import pytest

from jbom.config.providers import SearchProviderConfig, get_provider
from jbom.services.search.cache import InMemorySearchCache
from jbom.suppliers.lcsc.provider import JlcpcbProvider
from jbom.suppliers.mouser.provider import MouserProvider


def test_get_provider_unknown_type_raises() -> None:
    cfg = SearchProviderConfig(type="does_not_exist", extra={})
    with pytest.raises(ValueError, match=r"Unknown provider type"):
        get_provider(cfg, cache=InMemorySearchCache())


def test_get_provider_mouser_api_dispatches() -> None:
    cfg = SearchProviderConfig(type="mouser_api", extra={"api_key": "dummy"})
    provider = get_provider(cfg, cache=InMemorySearchCache())
    assert isinstance(provider, MouserProvider)


def test_get_provider_jlcpcb_api_dispatches() -> None:
    cfg = SearchProviderConfig(type="jlcpcb_api", extra={"rate_limit_seconds": 0})
    provider = get_provider(cfg, cache=InMemorySearchCache())
    assert isinstance(provider, JlcpcbProvider)


def test_get_provider_jlcparts_sqlite_unknown() -> None:
    """jlcparts_sqlite was retired; the registry should reject it."""
    cfg = SearchProviderConfig(
        type="jlcparts_sqlite",
        extra={"db_path": "~/.cache/jbom/jlcparts/components.db"},
    )
    with pytest.raises(ValueError, match=r"Unknown provider type"):
        get_provider(cfg, cache=InMemorySearchCache())
