"""Pytest configuration for jBOM.

This repo expects imports from the local `src/` tree (e.g. `import jbom`).
In many developer workflows this is provided via PYTHONPATH, but tests should be
runnable without external environment configuration.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest


_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_TESTS_DIR = Path(__file__).resolve().parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"


@pytest.fixture(autouse=True)
def _hermetic_datasheet_staging(monkeypatch: pytest.MonkeyPatch):
    """Prevent any test from touching real network.

    jBOM#355's always-on staging fetch rides ``jbom search`` / ``jbom
    inventory --supplier``, but is inert by design unless a
    ``datasheet_staging.staging_dir`` is explicitly configured (there is no
    code-level fallback path -- see ``jbom.services.datasheet_staging``).
    So the only residual risk is a test that configures a staging_dir
    without also injecting a fake fetch: this fixture makes
    :func:`jbom.services.datasheet_staging.default_fetch` raise immediately
    instead of making a real HTTP request in that case, so a forgotten
    fixture/mock fails loudly and fast rather than silently reaching out.

    Individual tests that want to exercise real staging behavior inject
    their own ``fetch`` callable or ``fetch_fixtures_manifest``, which take
    precedence over this fixture.
    """

    import jbom.services.datasheet_staging as datasheet_staging

    def _forbidden_fetch(url: str, *, timeout: float = 20.0) -> bytes:
        raise RuntimeError(
            f"Real network fetch attempted in tests (url={url!r}); inject a "
            "fake `fetch` callable or configure fetch_fixtures_manifest instead."
        )

    monkeypatch.setattr(datasheet_staging, "default_fetch", _forbidden_fetch)


def load_mouser_fixture(name: str) -> dict[str, Any]:
    """Load a named fixture from tests/fixtures/mouser/."""

    filename = name if name.endswith(".json") else f"{name}.json"
    fixture_path = _FIXTURES_DIR / "mouser" / filename
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"Fixture {fixture_path} must contain a JSON object, got {type(data).__name__}"
        )

    return data


def load_lcsc_fixture(name: str) -> dict[str, Any]:
    """Load a named fixture from tests/fixtures/lcsc/."""

    filename = name if name.endswith(".json") else f"{name}.json"
    fixture_path = _FIXTURES_DIR / "lcsc" / filename
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"Fixture {fixture_path} must contain a JSON object, got {type(data).__name__}"
        )

    return data
