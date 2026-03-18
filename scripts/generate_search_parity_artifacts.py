#!/usr/bin/env python3
"""Generate deterministic search parity matrix + diagnostics artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repository root without installation.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from jbom.services.search.parity_artifacts import (  # noqa: E402
    DEFAULT_DIAGNOSTICS_JSON_RELATIVE_PATH,
    DEFAULT_MATRIX_CSV_RELATIVE_PATH,
    write_search_parity_artifacts,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=_ROOT / "tests" / "fixtures",
        help="Root fixture directory containing supplier fixture subdirectories.",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=_ROOT / DEFAULT_MATRIX_CSV_RELATIVE_PATH,
        help="Output CSV path for parity matrix artifact.",
    )
    parser.add_argument(
        "--diagnostics",
        type=Path,
        default=_ROOT / DEFAULT_DIAGNOSTICS_JSON_RELATIVE_PATH,
        help="Output JSON path for diagnostics evidence artifact.",
    )
    parser.add_argument(
        "--max-results-per-supplier",
        type=int,
        default=80,
        help="Cap parsed results per supplier fixture for deterministic artifact size.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    payload = write_search_parity_artifacts(
        matrix_path=args.matrix,
        diagnostics_path=args.diagnostics,
        fixture_root=args.fixture_root,
        max_results_per_supplier=args.max_results_per_supplier,
    )

    print(
        f"Wrote parity matrix: {args.matrix}\n"
        f"Wrote diagnostics: {args.diagnostics}\n"
        f"Intents: {len(payload.get('intents', []))}, "
        f"gaps: {len(payload.get('parity_gaps', []))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
