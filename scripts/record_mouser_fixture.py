#!/usr/bin/env python3
"""Record raw Mouser keyword search responses as JSON fixtures.

This script is a developer tool intended to be run manually (not by pytest).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence


BASE_URL = "https://api.mouser.com/api/v1/search"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a raw Mouser keyword search response to a fixture JSON file."
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Keyword search query to send to Mouser (e.g. '10K resistor 0603').",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output JSON path (e.g. tests/fixtures/mouser/keyword_resistor_10k_0603.json).",
    )
    return parser


def _fetch_keyword_search(*, api_key: str, query: str) -> dict[str, Any]:
    try:
        import requests  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "This script requires 'requests'. Install it with: pip install requests"
        ) from exc

    url = f"{BASE_URL}/keyword"
    payload = {
        "SearchByKeywordRequest": {
            "keyword": query,
            "records": 100,
            "startingRecord": 0,
            "searchOptions": "None",
            "searchWithYourSignUpLanguage": "English",
        }
    }

    response = requests.post(
        url,
        params={"apiKey": api_key},
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object response, got {type(data).__name__}")

    return data


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    api_key = os.environ.get("MOUSER_API_KEY")
    if not api_key:
        parser.error(
            "MOUSER_API_KEY environment variable is required to record fixtures"
        )

    try:
        data = _fetch_keyword_search(api_key=api_key, query=args.query)
    except Exception as exc:
        print(f"Failed to record Mouser fixture: {exc}", file=sys.stderr)
        return 1

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
