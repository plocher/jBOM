"""Common fabricator CLI argument handling.

Provides reusable functions for fabricator argument registration and resolution
to eliminate code duplication between BOM and POS commands.
"""
from __future__ import annotations

import argparse

from jbom.config.fabricators import get_available_fabricators


def add_fabricator_arguments(parser: argparse.ArgumentParser) -> None:
    """Add standard fabricator selection arguments to argument parser.

    Adds both --fabricator parameter and individual preset flags (--jlc, --generic, etc.)
    used by BOM and POS commands.

    Args:
        parser: Argument parser to add fabricator arguments to
    """
    # Fabricator selection (for field presets / predictable output)
    parser.add_argument(
        "--fabricator",
        choices=get_available_fabricators(),
        help="Specify PCB fabricator for field presets (default: generic)",
    )

    # Individual fabricator preset flags
    parser.add_argument("--jlc", action="store_true", help="Use JLC preset")
    parser.add_argument("--pcbway", action="store_true", help="Use PCBWay preset")
    parser.add_argument("--seeed", action="store_true", help="Use Seeed preset")
    parser.add_argument("--generic", action="store_true", help="Use Generic preset")


def resolve_fabricator_from_args(args: argparse.Namespace) -> str:
    """Resolve effective fabricator from command line arguments.

    Handles both --fabricator parameter and individual preset flags,
    with fallback to "generic" if nothing specified.

    Args:
        args: Parsed command line arguments

    Returns:
        Effective fabricator ID (e.g., "jlc", "generic", "pcbway")

    Raises:
        ValueError: If multiple fabricator presets are specified
    """
    # Check for multiple fabricator preset conflicts
    preset_flags = []
    if getattr(args, "jlc", False):
        preset_flags.append("--jlc")
    if getattr(args, "pcbway", False):
        preset_flags.append("--pcbway")
    if getattr(args, "seeed", False):
        preset_flags.append("--seeed")
    if getattr(args, "generic", False):
        preset_flags.append("--generic")

    if len(preset_flags) > 1:
        raise ValueError(
            f"Cannot specify multiple fabricator presets: {', '.join(preset_flags)}"
        )

    # Resolve fabricator from arguments
    fabricator = getattr(args, "fabricator", None)

    if not fabricator:
        if getattr(args, "jlc", False):
            fabricator = "jlc"
        elif getattr(args, "pcbway", False):
            fabricator = "pcbway"
        elif getattr(args, "seeed", False):
            fabricator = "seeed"
        elif getattr(args, "generic", False):
            fabricator = "generic"

    # Default to generic if nothing specified
    if not fabricator:
        fabricator = "generic"

    return fabricator


def validate_fabricator_args(args: argparse.Namespace) -> None:
    """Validate fabricator-related arguments for consistency.

    Checks for conflicts between --fabricator parameter and individual preset flags.

    Args:
        args: Parsed command line arguments

    Raises:
        ValueError: If both --fabricator and individual preset flags are specified
    """
    fabricator_param = getattr(args, "fabricator", None)
    individual_flags = [
        getattr(args, "jlc", False),
        getattr(args, "pcbway", False),
        getattr(args, "seeed", False),
        getattr(args, "generic", False),
    ]

    if fabricator_param and any(individual_flags):
        active_flags = []
        if getattr(args, "jlc", False):
            active_flags.append("--jlc")
        if getattr(args, "pcbway", False):
            active_flags.append("--pcbway")
        if getattr(args, "seeed", False):
            active_flags.append("--seeed")
        if getattr(args, "generic", False):
            active_flags.append("--generic")

        raise ValueError(
            f"Cannot specify both --fabricator {fabricator_param} and "
            f"individual preset flags: {', '.join(active_flags)}"
        )
