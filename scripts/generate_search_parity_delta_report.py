#!/usr/bin/env python3
"""Generate baseline-vs-candidate search parity delta report artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repository root without installation.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from jbom.services.search.parity_delta import (  # noqa: E402
    write_parity_delta_artifacts,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-diagnostics",
        type=Path,
        default=_ROOT
        / "tests"
        / "fixtures"
        / "search_parity"
        / "baseline_issue_199"
        / "diagnostics.json",
        help="Baseline diagnostics JSON artifact path (issue #199 baseline).",
    )
    parser.add_argument(
        "--candidate-diagnostics",
        type=Path,
        default=_ROOT / "tests" / "fixtures" / "search_parity" / "diagnostics.json",
        help="Candidate diagnostics JSON artifact path (current branch run).",
    )
    parser.add_argument(
        "--delta-json",
        type=Path,
        default=_ROOT / "tests" / "fixtures" / "search_parity" / "delta_issue_200.json",
        help="Output JSON parity delta report path.",
    )
    parser.add_argument(
        "--delta-csv",
        type=Path,
        default=_ROOT / "tests" / "fixtures" / "search_parity" / "delta_issue_200.csv",
        help="Output CSV parity delta report path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    report = write_parity_delta_artifacts(
        baseline_diagnostics_path=args.baseline_diagnostics,
        candidate_diagnostics_path=args.candidate_diagnostics,
        delta_json_path=args.delta_json,
        delta_csv_path=args.delta_csv,
    )
    summary = report.get("summary", {})
    print(
        f"Wrote parity delta JSON: {args.delta_json}\n"
        f"Wrote parity delta CSV: {args.delta_csv}\n"
        f"Buckets -> improved: {summary.get('improved_count', 0)}, "
        f"unchanged: {summary.get('unchanged_count', 0)}, "
        f"regressed: {summary.get('regressed_count', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
