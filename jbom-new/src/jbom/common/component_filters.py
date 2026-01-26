"""Common component filtering functionality for all jBOM commands.

This module provides consistent filtering flags and logic across BOM, Parts, and POS commands
to eliminate DRY violations and ensure uniform behavior.
"""

import argparse
from typing import Dict, Any, List
from jbom.common.types import Component


def add_component_filter_arguments(
    parser: argparse.ArgumentParser, command_type: str = "full"
) -> None:
    """Add component filtering arguments to a CLI parser.

    Args:
        parser: The argument parser to add filtering options to
        command_type: Type of command ("full", "pos") to determine which flags to add
    """
    # Filtering options group
    filter_group = parser.add_argument_group("component filtering")

    # DNP filtering applies to all commands
    dnp_help = {
        "pos": (
            'Include "Do Not Populate" components in placement file '
            "(default: excluded since they are not placed during assembly)"
        ),
        "full": 'Include "Do Not Populate" components (default: excluded)',
    }

    filter_group.add_argument(
        "--include-dnp",
        action="store_true",
        help=dnp_help.get(command_type, dnp_help["full"]),
    )

    # BOM exclusion and virtual symbols only apply to BOM/Parts commands
    if command_type == "full":
        filter_group.add_argument(
            "--include-excluded",
            action="store_true",
            help="Include components excluded from BOM (default: excluded)",
        )

        filter_group.add_argument(
            "--include-all",
            action="store_true",
            help="Include all components (DNP, excluded from BOM, and virtual symbols)",
        )


def create_filter_config(
    args: argparse.Namespace, command_type: str = "full"
) -> Dict[str, Any]:
    """Create filter configuration from CLI arguments.

    Args:
        args: Parsed CLI arguments with filter flags
        command_type: Type of command ("full", "pos") to determine applicable filters

    Returns:
        Dictionary of filter parameters for service generators
    """
    if command_type == "pos":
        # POS shows components that get physically placed/populated during assembly
        # - DNP components are NOT placed by default (exclude_dnp=True)
        # - BOM-excluded components (mounting holes, logos) still need placement coordinates
        # - Virtual symbols never have physical placement coordinates
        return {
            "exclude_dnp": not getattr(
                args, "include_dnp", False
            ),  # Exclude DNP by default
            "include_only_bom": False,  # Include BOM-excluded (they still get placed)
            "include_virtual_symbols": False,  # Virtual symbols have no placement
        }
    else:
        # Full filtering for BOM/Parts commands
        # --include-all overrides individual flags
        if getattr(args, "include_all", False):
            return {
                "exclude_dnp": False,
                "include_only_bom": False,
                "include_virtual_symbols": True,
            }
        else:
            return {
                "exclude_dnp": not getattr(args, "include_dnp", False),
                "include_only_bom": not getattr(args, "include_excluded", False),
                "include_virtual_symbols": False,
            }


def apply_component_filters(
    components: List[Component], filters: Dict[str, Any]
) -> List[Component]:
    """Apply filtering criteria to component list.

    This provides common filtering logic used by all generators.

    Args:
        components: List of components to filter
        filters: Filter configuration from create_filter_config()

    Returns:
        Filtered list of components
    """
    filtered = []

    # Extract filter settings with defaults
    exclude_dnp = filters.get("exclude_dnp", True)
    include_only_bom = filters.get("include_only_bom", True)
    include_virtual_symbols = filters.get("include_virtual_symbols", False)

    for component in components:
        # Apply DNP filter
        if exclude_dnp and component.dnp:
            continue

        # Apply include only BOM components filter
        if include_only_bom and not component.in_bom:
            continue

        # Skip virtual symbols (references starting with #) unless explicitly included
        if not include_virtual_symbols and component.reference.startswith("#"):
            continue

        filtered.append(component)

    return filtered


def get_filter_summary(filters: Dict[str, Any]) -> str:
    """Generate human-readable summary of active filters.

    Args:
        filters: Filter configuration

    Returns:
        String describing what filters are active
    """
    parts = []

    if filters.get("exclude_dnp", True):
        parts.append("excluding DNP")
    if filters.get("include_only_bom", True):
        parts.append("excluding non-BOM")
    if not filters.get("include_virtual_symbols", False):
        parts.append("excluding virtual symbols")

    if not parts:
        return "including all components"
    else:
        return f"filtering: {', '.join(parts)}"
