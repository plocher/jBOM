"""Test-only network-fixture escape hatch (jBOM#372).

Both datasheet staging and ``jbom audit --check-urls`` can redirect HTTP
fetches to a local ``{url: file_path}`` JSON manifest via the profile keys:

* ``defaults.datasheet_staging.fetch_fixtures_manifest``
* ``defaults.check_urls.fetch_fixtures_manifest``

Those keys are **not** a production feature. This module is the single gate
that keeps them from silently taking effect in normal user invocations:

1. A non-empty manifest path is honored only when the process environment
   explicitly allows it (``JBOM_ALLOW_FETCH_FIXTURES`` set to a truthy value
   such as ``1`` / ``true`` / ``yes`` / ``on``).
2. If a profile sets the key without that allow flag, resolution fails
   loudly — never falls through to fixture bytes, never silently uses the
   network while pretending fixtures are active.
3. Whenever fixtures *are* active, a one-line notice is written to stderr
   so no run can silently substitute fixture payloads for real fetches.

The sanctioned Behave harness enables the allow flag only for scenarios
that register a fixture manifest (see ``features/steps/*_steps.py``).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable, Final

ALLOW_FETCH_FIXTURES_ENV: Final[str] = "JBOM_ALLOW_FETCH_FIXTURES"

_TRUTHY: Final[frozenset[str]] = frozenset({"1", "true", "yes", "on"})


class FetchFixturesNotAllowedError(RuntimeError):
    """Raised when a fixtures manifest is configured without the allow env."""


def fetch_fixtures_allowed() -> bool:
    """Return True when the process may honor a fixtures-manifest profile key."""

    raw = os.environ.get(ALLOW_FETCH_FIXTURES_ENV, "")
    return raw.strip().lower() in _TRUTHY


def require_fetch_fixtures_manifest(manifest: str) -> str:
    """Gate a configured fixtures-manifest path.

    Args:
        manifest: Raw profile value (path string). Empty/whitespace means
            fixtures are not requested.

    Returns:
        The stripped manifest path when fixtures are requested **and**
        allowed. Empty string when fixtures are not requested.

    Raises:
        FetchFixturesNotAllowedError: The profile requests fixtures but
            :func:`fetch_fixtures_allowed` is False.
    """

    path = (manifest or "").strip()
    if not path:
        return ""
    if not fetch_fixtures_allowed():
        raise FetchFixturesNotAllowedError(
            "fetch_fixtures_manifest is set in the active profile "
            f"({path!r}) but {ALLOW_FETCH_FIXTURES_ENV} is not enabled. "
            "This key is test-only and cannot silently replace network "
            "fetches in production profiles. Enable it only from the test "
            f"harness (export {ALLOW_FETCH_FIXTURES_ENV}=1), or remove the "
            "key from your profile."
        )
    _emit_fixtures_active_notice(path)
    return path


def fetch_from_fixture_manifest(url: str, manifest_path: Path) -> bytes:
    """Resolve *url* to local fixture bytes via a ``{url: file_path}`` manifest."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_path = manifest.get(url)
    if not file_path:
        raise RuntimeError(f"No fixture registered for URL {url!r} in {manifest_path}")
    return Path(file_path).read_bytes()


def resolve_fixture_fetch(
    fetch_fixtures_manifest: str,
) -> Callable[[str], bytes] | None:
    """Return a fixture-backed fetch callable, or ``None`` for network default.

    Applies :func:`require_fetch_fixtures_manifest`. Callers that receive
    ``None`` should fall back to their real network ``default_fetch``.
    """

    path = require_fetch_fixtures_manifest(fetch_fixtures_manifest)
    if not path:
        return None

    manifest_path = Path(path)

    def _fixture_fetch(url: str) -> bytes:
        return fetch_from_fixture_manifest(url, manifest_path)

    return _fixture_fetch


def _emit_fixtures_active_notice(manifest_path: str) -> None:
    """Print a prominent stderr notice that fixture fetches are active."""

    print(
        "WARNING: test-only fetch fixtures are ACTIVE "
        f"(manifest={manifest_path}; "
        f"{ALLOW_FETCH_FIXTURES_ENV} is set). "
        "Network fetches are redirected to local fixture files.",
        file=sys.stderr,
    )


__all__ = [
    "ALLOW_FETCH_FIXTURES_ENV",
    "FetchFixturesNotAllowedError",
    "fetch_fixtures_allowed",
    "fetch_from_fixture_manifest",
    "require_fetch_fixtures_manifest",
    "resolve_fixture_fetch",
]
