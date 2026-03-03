"""Search provider configuration and registry.

Supplier profiles (YAML) declare an ordered list of provider configurations under
`search.providers`. Each entry is a typed bag of provider-specific keys.

This module provides:
- A small typed wrapper for provider configs (SearchProviderConfig)
- A registry mapping provider type strings to implementations
- A factory (get_provider) to instantiate providers from config

Note: Provider selection is user-facing by supplier ID (e.g. "mouser", "lcsc").
Provider *types* are internal (e.g. "mouser_api", "jlcparts_sqlite").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jbom.services.search.cache import SearchCache
    from jbom.services.search.provider import SearchProvider


@dataclass(frozen=True)
class SearchProviderConfig:
    """Typed bag of provider configuration.

    Attributes:
        type: Provider type string used for registry dispatch.
        extra: Provider-specific keys (provider implementation owns this schema).
    """

    type: str
    extra: dict[str, Any] = field(default_factory=dict)

    def with_extra(self, updates: dict[str, Any]) -> "SearchProviderConfig":
        """Return a copy with extra keys merged in.

        This is useful for injecting CLI overrides (e.g. `--api-key`) without
        mutating parsed YAML structures.
        """

        merged = dict(self.extra)
        merged.update(dict(updates or {}))
        return SearchProviderConfig(type=self.type, extra=merged)


def _registry() -> dict[str, type["SearchProvider"]]:
    # Lazily import providers to avoid config<->service circular imports.
    from jbom.services.search.jlcparts_provider import JlcpartsProvider
    from jbom.services.search.jlcpcb_provider import JlcpcbProvider
    from jbom.services.search.mouser_provider import MouserProvider

    return {
        "mouser_api": MouserProvider,
        "jlcpcb_api": JlcpcbProvider,
        "jlcparts_sqlite": JlcpartsProvider,
    }


def get_provider(
    cfg: SearchProviderConfig, *, cache: "SearchCache"
) -> "SearchProvider":
    """Instantiate a SearchProvider from its config.

    Args:
        cfg: Provider configuration from supplier YAML.
        cache: Cache implementation (runtime concern, not owned by providers).

    Raises:
        ValueError: If the provider type is unknown.

    Returns:
        Instantiated provider.
    """

    provider_type = (cfg.type or "").strip()
    if not provider_type:
        raise ValueError("Provider config missing non-empty 'type'")

    provider_cls = _registry().get(provider_type)
    if provider_cls is None:
        raise ValueError(f"Unknown provider type: {provider_type}")

    return provider_cls.from_config(cfg, cache=cache)


def list_searchable_suppliers() -> list[str]:
    """Return supplier IDs that declare at least one search provider, sorted.

    Used to populate --provider choices in CLI commands.
    """

    from jbom.config.suppliers import list_suppliers, load_supplier

    out: list[str] = []
    for sid in list_suppliers():
        try:
            supplier = load_supplier(sid)
        except ValueError:
            continue
        if supplier.search_providers:
            out.append(supplier.id)
    return sorted(set(out))


__all__ = ["SearchProviderConfig", "get_provider", "list_searchable_suppliers"]
