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
    """No-op: component filter flags have been removed.

    BOM/Parts use fixed contract-correct defaults (DNP included, exclude_from_bom
    excluded, virtual symbols excluded).  POS always drops DNP rows.
    This function is retained as a no-op to avoid import churn at call sites.
    """


def create_filter_config(
    args: argparse.Namespace, command_type: str = "full"
) -> Dict[str, Any]:
    """Return fixed contract-correct filter configuration.

    Args:
        args: Parsed CLI arguments (no filter flags are read; kept for call-site compat)
        command_type: Type of command ("full" for BOM/Parts, "pos" for placement)

    Returns:
        Dictionary of filter parameters for service generators
    """
    if command_type == "pos":
        # POS: only physically-placed components. DNP = Do Not Place.
        return {
            "exclude_dnp": True,
            "include_only_bom": False,  # BOM-excluded parts (logos, mounting holes) still get placed
            "include_virtual_symbols": False,
        }
    # BOM/Parts: enumerate all design components. DNP rows are included and marked.
    return {
        "exclude_dnp": False,
        "include_only_bom": True,
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
    exclude_dnp = filters.get("exclude_dnp", False)
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
