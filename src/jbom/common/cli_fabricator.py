"""Common fabricator CLI argument handling.

Provides reusable functions for fabricator argument registration and resolution
to eliminate code duplication between BOM and POS commands.
"""
from __future__ import annotations

import argparse
from functools import lru_cache

from jbom.config.fabricators import get_available_fabricators, load_fabricator


def _flag_dest(fabricator_id: str) -> str:
    """Return argparse dest name for a dynamic fabricator shorthand flag."""

    token = (fabricator_id or "").strip().replace("-", "_")
    return f"fabricator_flag_{token}"


def add_fabricator_arguments(parser: argparse.ArgumentParser) -> None:
    """Add standard fabricator selection arguments to an argument parser.

    Adds both --fabricator and per-fabricator shorthand flags (e.g. --jlc).

    Flags are generated dynamically from the discovered built-in fabricator
    profiles so the CLI help output stays accurate as profiles are added.

    Args:
        parser: Argument parser to add fabricator arguments to.
    """

    metadata = _fabricator_argument_metadata()
    available = [fabricator_id for fabricator_id, _display_name in metadata]

    # Fabricator selection (for field presets / predictable output)
    parser.add_argument(
        "--fabricator",
        choices=available,
        default=None,
        help="Specify PCB fabricator for field presets (default: generic)",
    )

    # Individual fabricator shorthand flags (e.g. --jlc).
    for fid, display_name in metadata:
        parser.add_argument(
            f"--{fid}",
            action="store_true",
            dest=_flag_dest(fid),
            help=f"Use {display_name} preset",
        )


def resolve_fabricator_selection_from_args(
    args: argparse.Namespace,
) -> tuple[str, bool]:
    """Resolve fabricator selection from CLI args.

    Returns:
        (fabricator_id, is_explicit)

    is_explicit is True only when the user provided --fabricator or a shorthand
    flag, rather than falling back to the default.

    Raises:
        ValueError: when conflicting fabricator arguments are provided.
    """

    available = _available_fabricator_ids()

    shorthand_selected: list[str] = []
    for fid in available:
        if getattr(args, _flag_dest(fid), False):
            shorthand_selected.append(fid)

    if len(shorthand_selected) > 1:
        raise ValueError(
            f"Cannot specify multiple fabricator presets: {', '.join('--' + f for f in shorthand_selected)}"
        )

    fabricator_param = getattr(args, "fabricator", None)
    if fabricator_param and shorthand_selected:
        raise ValueError(
            f"Cannot specify both --fabricator {fabricator_param} and "
            f"individual preset flags: {', '.join('--' + f for f in shorthand_selected)}"
        )

    if fabricator_param:
        return str(fabricator_param), True

    if shorthand_selected:
        return shorthand_selected[0], True

    return "generic", False


def resolve_fabricator_from_args(args: argparse.Namespace) -> str:
    """Resolve effective fabricator from command line arguments.

    Handles both --fabricator parameter and individual shorthand flags,
    with fallback to "generic" if nothing specified.
    """

    fid, _explicit = resolve_fabricator_selection_from_args(args)
    return fid


def validate_fabricator_args(args: argparse.Namespace) -> None:
    """Validate fabricator-related arguments for consistency."""

    # This is implemented by resolve_fabricator_selection_from_args.
    resolve_fabricator_selection_from_args(args)


@lru_cache(maxsize=1)
def _fabricator_argument_metadata() -> tuple[tuple[str, str], ...]:
    metadata: list[tuple[str, str]] = []
    for fid in get_available_fabricators():
        try:
            display_name = load_fabricator(fid).name
        except Exception:
            display_name = fid
        metadata.append((fid, display_name))
    return tuple(metadata)


def _available_fabricator_ids() -> list[str]:
    return [
        fabricator_id
        for fabricator_id, _display_name in _fabricator_argument_metadata()
    ]


def clear_fabricator_argument_cache() -> None:
    """Clear cached parser-time fabricator argument metadata."""

    _fabricator_argument_metadata.cache_clear()
