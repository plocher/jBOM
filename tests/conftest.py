"""Pytest configuration for jbom-new.

This repo expects imports from the local `src/` tree (e.g. `import jbom`).
In many developer workflows this is provided via PYTHONPATH, but tests should be
runnable without external environment configuration.
"""

from __future__ import annotations

import sys
from pathlib import Path


_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
