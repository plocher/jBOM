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


_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_TESTS_DIR = Path(__file__).resolve().parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"


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
