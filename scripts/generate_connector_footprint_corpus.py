#!/usr/bin/env python3
"""Generate a deterministic connector-footprint corpus fixture from KiCad libs.

The corpus is intentionally schema-stable and can be used as a practical baseline
for tests before connector-matching heuristic work begins.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_KICAD_FOOTPRINT_ROOT = Path(
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
)
DEFAULT_OUTPUT_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "connector_footprints"
    / "kicad_connector_footprint_corpus.json"
)

_CONNECTOR_LIB_PREFIX = "Connector"
_CONNECTOR_LIB_SUFFIX = ".pretty"
_KNOWN_SERIES_PREFIXES = (
    "JST_PH",
    "JST_XH",
    "JST_GH",
    "JST_SH",
    "JST_ZH",
    "PinHeader",
    "Molex",
    "USB",
    "RJ",
)

_PITCH_STRICT_RE = re.compile(r"(?i)(?:^|[_-])P(?P<pitch>\d+(?:[.,]\d+)?)mm(?:$|[_-])")
_PITCH_BROAD_RE = re.compile(r"(?i)(?P<pitch>\d+(?:[.,]\d+)?)mm")
_PIN_GRID_RE = re.compile(r"(?<!\d)(?P<rows>\d+)[xX](?P<cols>\d+)(?!\d)")
_PAD_RE = re.compile(r"\(pad\s+\"?[^\s\"]+\"?\s")


@dataclass(frozen=True)
class ConnectorFootprintRecord:
    """Structured footprint signals extracted from a single .kicad_mod entry."""

    library: str
    footprint_name: str
    footprint_full: str
    pitch_mm_strict: str
    pitch_mm_broad: str
    pin_grid: str
    pins_from_name: int | None
    pad_count: int
    orientation: str
    series_prefix: str


def _normalize_pitch_token(raw: str) -> str:
    """Normalize pitch token text to a deterministic canonical form."""

    token = (raw or "").strip().replace(",", ".")
    if not token:
        return ""
    # Keep compact decimal rendering while preserving integral values as integers.
    if "." in token:
        token = token.rstrip("0").rstrip(".")
    return token


def _extract_pitch_strict(name: str) -> str:
    """Extract pitch in mm from KiCad-style P{value}mm fragments."""

    match = _PITCH_STRICT_RE.search(name or "")
    if not match:
        return ""
    return _normalize_pitch_token(match.group("pitch"))


def _extract_pitch_broad(name: str) -> str:
    """Extract any mm token from name as a broader fallback signal."""

    match = _PITCH_BROAD_RE.search(name or "")
    if not match:
        return ""
    return _normalize_pitch_token(match.group("pitch"))


def _extract_pin_grid(name: str) -> tuple[str, int | None]:
    """Extract NxM grid and computed total pins from footprint name."""

    match = _PIN_GRID_RE.search(name or "")
    if not match:
        return "", None
    rows = int(match.group("rows"))
    cols = int(match.group("cols"))
    return f"{rows}x{cols}", rows * cols


def _extract_orientation(name: str) -> str:
    """Extract coarse orientation token from footprint name."""

    text = (name or "").lower()
    if "rightangle" in text or "right_angle" in text or "right-angle" in text:
        return "right_angle"
    if "vertical" in text:
        return "vertical"
    if "horizontal" in text:
        return "horizontal"
    if "inverted" in text:
        return "inverted"
    return ""


def _extract_series_prefix(name: str) -> str:
    """Detect known connector series prefix from footprint entry name."""

    for prefix in _KNOWN_SERIES_PREFIXES:
        if (name or "").startswith(prefix):
            return prefix
    return ""


def _count_pads(mod_text: str) -> int:
    """Count pad declarations in .kicad_mod text."""

    return len(_PAD_RE.findall(mod_text or ""))


def _iter_connector_libs(footprint_root: Path) -> Iterable[Path]:
    """Yield Connector*.pretty libraries in deterministic order."""

    for lib in sorted(footprint_root.iterdir()):
        if not lib.is_dir():
            continue
        if not lib.name.startswith(_CONNECTOR_LIB_PREFIX):
            continue
        if not lib.name.endswith(_CONNECTOR_LIB_SUFFIX):
            continue
        yield lib


def _scan_connector_footprints(footprint_root: Path) -> list[ConnectorFootprintRecord]:
    """Scan Connector* libraries and return extracted records."""

    records: list[ConnectorFootprintRecord] = []
    for lib in _iter_connector_libs(footprint_root):
        for mod_path in sorted(lib.glob("*.kicad_mod")):
            footprint_name = mod_path.stem
            mod_text = mod_path.read_text(errors="ignore")
            pin_grid, pins_from_name = _extract_pin_grid(footprint_name)
            record = ConnectorFootprintRecord(
                library=lib.name,
                footprint_name=footprint_name,
                footprint_full=f"{lib.stem}:{footprint_name}",
                pitch_mm_strict=_extract_pitch_strict(footprint_name),
                pitch_mm_broad=_extract_pitch_broad(footprint_name),
                pin_grid=pin_grid,
                pins_from_name=pins_from_name,
                pad_count=_count_pads(mod_text),
                orientation=_extract_orientation(footprint_name),
                series_prefix=_extract_series_prefix(footprint_name),
            )
            records.append(record)
    return records


def _build_summary(records: list[ConnectorFootprintRecord]) -> dict[str, int | float]:
    """Build aggregate corpus metrics for quick quality inspection."""

    total = len(records)
    with_pitch_strict = sum(1 for r in records if r.pitch_mm_strict)
    with_pitch_broad = sum(1 for r in records if r.pitch_mm_broad)
    with_pin_grid = sum(1 for r in records if r.pin_grid)
    with_pin_count = sum(1 for r in records if r.pins_from_name is not None)
    with_series_prefix = sum(1 for r in records if r.series_prefix)
    with_orientation = sum(1 for r in records if r.orientation)
    with_pads = sum(1 for r in records if r.pad_count > 0)

    paired_pin_pad = [
        r for r in records if r.pins_from_name is not None and r.pad_count > 0
    ]
    exact_pin_pad = sum(1 for r in paired_pin_pad if r.pins_from_name == r.pad_count)

    return {
        "libraries": len({r.library for r in records}),
        "footprints": total,
        "with_pitch_strict": with_pitch_strict,
        "with_pitch_broad": with_pitch_broad,
        "with_pin_grid": with_pin_grid,
        "with_pin_count": with_pin_count,
        "with_series_prefix": with_series_prefix,
        "with_orientation": with_orientation,
        "with_pad_count": with_pads,
        "pin_pad_pairs": len(paired_pin_pad),
        "pin_pad_exact_matches": exact_pin_pad,
        "pin_pad_exact_ratio": (
            round(exact_pin_pad / len(paired_pin_pad), 4) if paired_pin_pad else 0.0
        ),
    }


def write_connector_footprint_corpus(
    *,
    footprint_root: Path,
    output_path: Path,
) -> dict[str, object]:
    """Generate and write the connector footprint corpus fixture payload."""

    records = _scan_connector_footprints(footprint_root)
    payload: dict[str, object] = {
        "schema_version": 1,
        "source_root": str(footprint_root),
        "summary": _build_summary(records),
        "records": [asdict(record) for record in records],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for corpus generation script."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--footprint-root",
        type=Path,
        default=DEFAULT_KICAD_FOOTPRINT_ROOT,
        help="KiCad footprints root containing Connector*.pretty directories.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output JSON fixture path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.footprint_root.exists():
        parser.error(f"Footprint root does not exist: {args.footprint_root}")

    payload = write_connector_footprint_corpus(
        footprint_root=args.footprint_root,
        output_path=args.output,
    )
    summary = payload["summary"]
    print(
        f"Wrote connector corpus: {args.output}\n"
        f"Libraries: {summary['libraries']}, footprints: {summary['footprints']}, "
        f"pin/pad exact ratio: {summary['pin_pad_exact_ratio']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
