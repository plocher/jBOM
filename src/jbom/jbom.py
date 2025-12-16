#!/usr/bin/env python3
"""
jBOM - KiCad Bill of Materials Generator

Takes a KiCad project and inventory file (CSV/Excel/Numbers) to generate a bill of materials.
Matches components to inventory entries based on type, value, and attributes.
"""

import re
import sys
import csv
import argparse
import warnings
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from sexpdata import Symbol

# Import data classes, constants, and utilities from common modules
from jbom.common.types import (
    DEFAULT_PRIORITY,
    Component,
    InventoryItem,
    BOMEntry,
)
from jbom.common.constants import (
    ComponentType,
    DiagnosticIssue,
    CommonFields,
    SMDType,
    ScoreWeights,
    PRECISION_THRESHOLD,
    DEFAULT_CATEGORY_FIELDS,
    CATEGORY_FIELDS,
    VALUE_INTERPRETATION,
    COMPONENT_TYPE_MAPPING,
)
from jbom.common.packages import PackageType
from jbom.common.fields import normalize_field_name, field_to_header

# Suppress specific Numbers version warning
warnings.filterwarnings(
    "ignore", message="Numbers version 14.3 not tested with this version"
)

# Optional imports for spreadsheet support
try:
    import openpyxl

    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

try:
    from numbers_parser import Document as NumbersDocument

    NUMBERS_SUPPORT = True
except ImportError:
    NUMBERS_SUPPORT = False


# Import schematic parsing and type detection from sch module (backward compatibility)
# All schematic parsing logic now lives in jbom.sch.parser and jbom.sch.types
# Import schematic loading, BOM generation, and type detection from sch module
from jbom.sch import SchematicLoader, BOMGenerator

# Import InventoryMatcher from inventory module
from jbom.inventory import InventoryMatcher


# Import file discovery functions from common.utils
from .common.utils import (
    find_best_schematic,
    is_hierarchical_schematic,
    extract_sheet_files,
    process_hierarchical_schematic,
)


def print_debug_diagnostics(diagnostics: List[dict]):
    """Print debug diagnostics in a concise, user-friendly format."""
    if not diagnostics:
        return

    print()
    print("Warnings:")
    print("=" * 60)

    for i, diagnostic_data in enumerate(diagnostics, 1):
        formatted_message = _format_diagnostic_for_console(diagnostic_data)
        print(f"{i:2d}. {formatted_message}")
        if i < len(
            diagnostics
        ):  # Add blank line between diagnostics except after the last one
            print()

    print()


def _format_diagnostic_for_console(diagnostic_data: dict) -> str:
    """Format structured diagnostic data for console output."""
    # Use the same instance method that handles console formatting
    # Need to create a temporary instance since this is a standalone function
    # Create a minimal BOMGenerator instance for method access
    temp_generator = BOMGenerator([], None)
    return temp_generator._generate_diagnostic_message(diagnostic_data, "console")


def _shorten_url(url: str, max_length: int = 30) -> str:
    """Shorten URLs for better table display."""
    if not url or len(url) <= max_length:
        return url

    # For HTTPS URLs, show domain + path start + end
    if url.startswith("https://"):
        # Extract domain and path
        parts = url[8:].split("/", 1)  # Remove https://
        domain = parts[0]
        path = "/" + parts[1] if len(parts) > 1 else ""

        if len(domain) > max_length - 6:  # 6 chars for "..." + some path
            return domain[: max_length - 3] + "..."

        if len(domain + path) <= max_length:
            return domain + path

        # Show domain + start/end of path
        remaining = max_length - len(domain) - 6  # 6 for "/.../"
        if remaining > 0:
            path_start = (
                path[1 : remaining // 2]
                if path.startswith("/")
                else path[: remaining // 2]
            )
            path_end = path[-(remaining // 2) :] if remaining // 2 > 0 else ""
            return f"{domain}/.../{path_end}" if path_end else f"{domain}/..."
        else:
            return domain + "/..."

    # For other URLs, just truncate with ellipsis
    return url[: max_length - 3] + "..." if len(url) > max_length else url


def _wrap_text(text: str, width: int) -> List[str]:
    """Wrap text to fit within specified width, breaking at word boundaries when possible."""
    if not text or width <= 0:
        return [""]

    if len(text) <= width:
        return [text]

    lines = []
    words = text.split()
    current_line = ""

    for word in words:
        # Truncate word if it's too long to fit in any line
        if len(word) > width:
            word = word[: width - 3] + "..."

        # If adding this word would exceed width
        if current_line and len(current_line + " " + word) > width:
            # If current line has content, save it and start new line
            lines.append(current_line)
            current_line = word
        else:
            # Add word to current line
            if current_line:
                current_line += " " + word
            else:
                current_line = word

    # Add any remaining content
    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def print_bom_table(
    bom_entries: List[BOMEntry], verbose: bool = False, include_mfg: bool = False
):
    """Print BOM entries as a formatted console table with word wrapping and URL shortening."""
    if not bom_entries:
        print("No BOM entries to display.")
        return

    # Determine columns to display
    headers = ["Reference", "Qty", "Value", "Footprint", "LCSC"]
    if include_mfg:
        headers.extend(["Manufacturer", "MFGPN"])
    headers.extend(["Datasheet", "SMD"])
    if verbose:
        headers.extend(["Match_Quality", "Priority"])

    # Check if any entries have notes
    any_notes = any((e.notes or "").strip() for e in bom_entries)
    if any_notes:
        headers.append("Notes")

    # Set maximum column widths for better table layout
    max_widths = {
        "Reference": 60,  # Allow long reference lists
        "Qty": 5,
        "Value": 12,
        "Footprint": 20,
        "LCSC": 10,
        "Manufacturer": 15,
        "MFGPN": 18,
        "Datasheet": 35,  # URLs get special handling
        "SMD": 4,
        "Match_Quality": 15,
        "Priority": 8,
        "Notes": 50,  # Allow reasonable space for notes
    }

    # Calculate optimal column widths
    col_widths = {}
    for header in headers:
        col_widths[header] = len(header)

    # Calculate widths based on data, respecting maximums
    for entry in bom_entries:
        col_widths["Reference"] = min(
            max_widths["Reference"], max(col_widths["Reference"], len(entry.reference))
        )
        col_widths["Qty"] = min(
            max_widths["Qty"], max(col_widths["Qty"], len(str(entry.quantity)))
        )
        col_widths["Value"] = min(
            max_widths["Value"], max(col_widths["Value"], len(entry.value))
        )
        col_widths["Footprint"] = min(
            max_widths["Footprint"], max(col_widths["Footprint"], len(entry.footprint))
        )
        col_widths["LCSC"] = min(
            max_widths["LCSC"], max(col_widths["LCSC"], len(entry.lcsc))
        )
        if include_mfg:
            col_widths["Manufacturer"] = min(
                max_widths["Manufacturer"],
                max(col_widths["Manufacturer"], len(entry.manufacturer)),
            )
            col_widths["MFGPN"] = min(
                max_widths["MFGPN"], max(col_widths["MFGPN"], len(entry.mfgpn))
            )
        # Datasheet width based on shortened URLs
        shortened_url = _shorten_url(entry.datasheet, max_widths["Datasheet"])
        col_widths["Datasheet"] = min(
            max_widths["Datasheet"], max(col_widths["Datasheet"], len(shortened_url))
        )
        col_widths["SMD"] = min(
            max_widths["SMD"], max(col_widths["SMD"], len(entry.smd))
        )
        if verbose:
            col_widths["Match_Quality"] = min(
                max_widths["Match_Quality"],
                max(col_widths["Match_Quality"], len(entry.match_quality)),
            )
            col_widths["Priority"] = min(
                max_widths["Priority"],
                max(col_widths["Priority"], len(str(entry.priority))),
            )
        if any_notes:
            # Notes width based on first line of wrapped text
            notes_lines = _wrap_text(entry.notes or "", max_widths["Notes"])
            first_line_len = len(notes_lines[0]) if notes_lines else 0
            col_widths["Notes"] = min(
                max_widths["Notes"], max(col_widths["Notes"], first_line_len)
            )

    # Print header
    header_line = ""
    separator_line = ""
    for i, header in enumerate(headers):
        width = col_widths[header]
        header_line += f"{header:<{width}}"
        separator_line += "-" * width
        if i < len(headers) - 1:
            header_line += " | "
            separator_line += "-+-"

    print()
    print("BOM Table:")
    print("=" * min(120, len(header_line)))
    print(header_line)
    print(separator_line)

    # Print entries with word wrapping support
    for entry in bom_entries:
        # Prepare all cell content with wrapping
        cell_lines = {}
        max_lines = 1

        for header in headers:
            width = col_widths[header]

            if header == "Reference":
                lines = _wrap_text(entry.reference, width)
            elif header == "Qty":
                lines = [str(entry.quantity)]
            elif header == "Value":
                lines = _wrap_text(entry.value, width)
            elif header == "Footprint":
                lines = _wrap_text(entry.footprint, width)
            elif header == "LCSC":
                lines = [entry.lcsc]
            elif header == "Manufacturer":
                lines = _wrap_text(entry.manufacturer, width)
            elif header == "MFGPN":
                lines = _wrap_text(entry.mfgpn, width)
            elif header == "Datasheet":
                shortened = _shorten_url(entry.datasheet, width)
                lines = [shortened]
            elif header == "SMD":
                lines = [entry.smd]
            elif header == "Match_Quality":
                lines = _wrap_text(entry.match_quality, width)
            elif header == "Priority":
                lines = [str(entry.priority)]
            elif header == "Notes":
                lines = _wrap_text(entry.notes or "", width)
            else:
                lines = [""]

            cell_lines[header] = lines
            max_lines = max(max_lines, len(lines))

        # Print each line of the row
        for line_num in range(max_lines):
            row_line = ""
            for i, header in enumerate(headers):
                width = col_widths[header]
                # Get the content for this line, or empty string if no more lines
                content = (
                    cell_lines[header][line_num]
                    if line_num < len(cell_lines[header])
                    else ""
                )
                row_line += f"{content:<{width}}"
                if i < len(headers) - 1:
                    row_line += " | "
            print(row_line)

    print()


def print_formatted_summary(
    file_info: List[tuple],
    inventory_path: Path,
    inventory_count: int,
    output_path: Path,
    bom_count: int,
    is_smd_only: bool = False,
    smd_excluded_count: int = 0,
    console_output: bool = False,
):
    """Print a nicely formatted summary of the BOM generation process."""

    # Schematic section
    if len(file_info) > 1:
        print("Hierarchical schematic set:")
        total_components = 0

        for count, file_path, warning in file_info:
            total_components += count
            warning_text = f" ({warning})" if warning else ""
            print(f"   {count:2d} Components      {file_path.name}{warning_text}")

        print("  ==============")
        print(
            f"   {total_components:2d} Components found in {len(file_info)} schematic files"
        )
    else:
        count, file_path, warning = file_info[0]
        warning_text = f" ({warning})" if warning else ""
        print(f"Schematic: {count} Components from {file_path.name}{warning_text}")

    print()

    # Inventory section
    print("Inventory:")
    print(f"   {inventory_count:2d} Items       {inventory_path}")
    print()

    # BOM section
    if console_output:
        print("BOM:")
        smd_text = ""
        if is_smd_only:
            smd_text = " (SMD items only)"
            if smd_excluded_count > 0:
                smd_text += f" - excluded {smd_excluded_count} non-SMD entries"
        print(f"   {bom_count:2d} Entries     Console Table{smd_text}")
    else:
        print("BOM:")
        smd_text = ""
        if is_smd_only:
            smd_text = " (SMD items only)"
            if smd_excluded_count > 0:
                smd_text += f" - excluded {smd_excluded_count} non-SMD entries"
        print(f"   {bom_count:2d} Entries     {output_path}{smd_text}")


# ---- Library API (no prints/exits) -------------------------------------------------


@dataclass
class GenerateOptions:
    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None


def generate_bom_api(
    project_path: Union[str, Path],
    inventory_path: Union[str, Path],
    options: Optional[GenerateOptions] = None,
):
    """
    Library API to generate a BOM without printing or exiting the process.

    Returns a dict with keys:
      - file_info: List[Tuple[count:int, file_path:Path, warning:Optional[str]]]
      - inventory_count: int
      - bom_entries: List[BOMEntry]
      - smd_excluded_count: int
      - debug_diagnostics: List[dict]
      - components: List[Component]
      - available_fields: Dict[str, str]
    """
    options = options or GenerateOptions()

    proj_path = Path(project_path)
    inv_path = Path(inventory_path)

    if not inv_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {inv_path}")

    file_extension = inv_path.suffix.lower()
    if file_extension not in [".csv", ".xlsx", ".xls", ".numbers"]:
        raise ValueError(f"Unsupported inventory file format: {file_extension}")
    if file_extension in [".xlsx", ".xls"] and not EXCEL_SUPPORT:
        raise ImportError(
            "Excel support requires openpyxl. Install with: pip install openpyxl"
        )
    if file_extension == ".numbers" and not NUMBERS_SUPPORT:
        raise ImportError(
            "Numbers support requires numbers-parser. Install with: pip install numbers-parser"
        )

    # Determine schematic file(s)
    if proj_path.suffix == ".kicad_sch":
        if not proj_path.exists():
            raise FileNotFoundError(f"Schematic file not found: {proj_path}")
        schematic_path = proj_path
        search_dir = proj_path.parent
    else:
        search_dir = proj_path
        schematic_path = find_best_schematic(search_dir)
        if schematic_path is None:
            raise FileNotFoundError("No .kicad_sch file found in project directory")

    # Parse components (hierarchical aware)
    components: List[Component] = []
    file_info: List[Tuple[int, Path, Optional[str]]] = []

    processed_files = process_hierarchical_schematic(schematic_path, search_dir)
    for file_path in processed_files:
        parser_obj = SchematicLoader(file_path)
        file_components = parser_obj.parse()
        components.extend(file_components)
        warning = (
            "Warning: autosave file may be incomplete!"
            if file_path.name.startswith("_autosave-")
            else None
        )
        file_info.append((len(file_components), file_path, warning))

    # Match inventory and generate BOM
    matcher = InventoryMatcher(inv_path)
    bom_generator = BOMGenerator(components, matcher)
    bom_entries, smd_excluded_count, debug_diagnostics = bom_generator.generate_bom(
        verbose=options.verbose, debug=options.debug, smd_only=options.smd_only
    )

    # Validate optional fields if provided
    if options.fields:
        available_fields = bom_generator.get_available_fields(components)
        invalid = [f for f in options.fields if f not in available_fields]
        if invalid:
            raise ValueError(f"Unknown fields: {', '.join(invalid)}")

    return {
        "file_info": file_info,
        "inventory_count": len(matcher.inventory),
        "bom_entries": bom_entries,
        "smd_excluded_count": smd_excluded_count,
        "debug_diagnostics": debug_diagnostics,
        "components": components,
        "available_fields": bom_generator.get_available_fields(components),
    }


# ---- CLI entrypoint -------------------------------------------------------------

# Import field parsing from common (proper layered architecture)
from jbom.common.fields import (
    FIELD_PRESETS,
    preset_fields as _preset_fields,
    parse_fields_argument as _parse_fields_argument,
)


def main():
    parser = argparse.ArgumentParser(
        description="jBOM - Generate BOM from KiCad project"
    )
    parser.add_argument("project_path", help="Path to KiCad project directory")
    parser.add_argument(
        "-i",
        "--inventory",
        required=True,
        help="Path to inventory file (.csv, .xlsx, .xls, or .numbers)",
    )
    parser.add_argument("-o", "--output", help="Output CSV file path")
    parser.add_argument(
        "--outdir",
        help="Directory for output files (used when --output is not provided)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include Match_Quality and Priority columns. Shows detailed scoring information",
    )
    parser.add_argument(
        "-f",
        "--fields",
        help="Field selection: use preset with + prefix (+standard, +jlc, +minimal, +all) or comma-separated field list. Mix both: +jlc,CustomField. Use --list-fields to see available fields",
    )
    parser.add_argument(
        "--multi-format",
        help="Comma-separated list of formats to emit in one run (e.g., jlc,standard)",
    )
    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="List all available fields from inventory and component data, then exit",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Add detailed matching information to Notes column for debugging",
    )
    parser.add_argument(
        "--smd",
        action="store_true",
        help="Include only SMD (Surface Mount Device) components in BOM output",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-essential output (useful for CI)",
    )
    parser.add_argument(
        "--json-report",
        help="Write a JSON report with run statistics to the given path",
    )

    args = parser.parse_args()

    project_path = Path(args.project_path)
    inventory_path = Path(args.inventory)

    # Validate inventory file exists and format is supported
    if not inventory_path.exists():
        print(f"Inventory file not found: {inventory_path}")
        sys.exit(1)

    file_extension = inventory_path.suffix.lower()
    if file_extension not in [".csv", ".xlsx", ".xls", ".numbers"]:
        print(f"Unsupported inventory file format: {file_extension}")
        print("Supported formats: .csv, .xlsx, .xls, .numbers")
        sys.exit(1)

    # Check for required packages
    if file_extension in [".xlsx", ".xls"] and not EXCEL_SUPPORT:
        print(f"Excel support ({file_extension}) requires openpyxl package.")
        print("Install with: pip install openpyxl")
        sys.exit(1)

    if file_extension == ".numbers" and not NUMBERS_SUPPORT:
        print(f"Numbers support ({file_extension}) requires numbers-parser package.")
        print("Install with: pip install numbers-parser")
        sys.exit(1)

    # Detect console output options
    console_output = False
    if args.output:
        output_str = args.output.lower()
        if output_str in ["-", "console", "stdout"]:
            console_output = True
            output_path = Path("-")  # Placeholder for console output
        else:
            output_path = Path(args.output)
    else:
        # If project_path points to a directory, we infer name from it; otherwise from parent
        out_base = project_path.name if project_path.is_dir() else project_path.stem
        base_dir = (
            Path(args.outdir)
            if args.outdir
            else (project_path if project_path.is_dir() else project_path.parent)
        )
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        output_path = base_dir / f"{out_base}_bom.csv"

    # Collect file information for formatted output
    file_info = []

    # Determine schematic file(s) to process
    if project_path.suffix == ".kicad_sch":
        # Specific file provided
        if not project_path.exists():
            print(f"Schematic file not found: {project_path}")
            sys.exit(1)
        schematic_path = project_path
        search_dir = project_path.parent
    else:
        # Directory provided - find schematic files
        search_dir = project_path
        schematic_path = find_best_schematic(search_dir)
        if schematic_path is None:
            sys.exit(1)

    # Process schematic(s) - handle hierarchical designs
    all_components = []
    processed_files = process_hierarchical_schematic(schematic_path, search_dir)

    for file_path in processed_files:
        parser_obj = SchematicLoader(file_path)
        file_components = parser_obj.parse()
        all_components.extend(file_components)

        # Check for warnings
        warning = None
        if file_path.name.startswith("_autosave-"):
            warning = "Warning: autosave file may be incomplete!"

        file_info.append((len(file_components), file_path, warning))

    components = all_components

    # Load inventory and match components
    matcher = InventoryMatcher(inventory_path)

    # Generate BOM
    bom_generator = BOMGenerator(components, matcher)
    bom_entries, smd_excluded_count, debug_diagnostics = bom_generator.generate_bom(
        verbose=args.verbose, debug=args.debug, smd_only=args.smd
    )

    # Handle field listing
    if args.list_fields:
        available_fields = bom_generator.get_available_fields(components)

        # Group fields by category
        standard_fields = {}
        inventory_fields = {}
        component_fields = {}

        for field, description in available_fields.items():
            if description.startswith("Inventory field:"):
                inventory_fields[field] = description
            elif description.startswith("Component property:"):
                component_fields[field] = description
            elif description.startswith("Ambiguous field:"):
                standard_fields[
                    field
                ] = description  # Put ambiguous fields with standard fields
            else:
                standard_fields[field] = description

        print("Available fields for BOM output:")
        print("=" * 60)

        # Standard BOM fields
        print("\nSTANDARD BOM FIELDS:")
        print("-" * 30)
        for field, description in sorted(standard_fields.items()):
            print(f"{field:<25} - {description}")

        # Inventory fields
        print("\nINVENTORY FIELDS:")
        print("-" * 30)
        for field, description in sorted(inventory_fields.items()):
            # Remove the "Inventory field: " prefix and show both prefixed and unprefixed versions
            clean_desc = description.replace("Inventory field: ", "")
            display_field = (
                field.replace("I:", "", 1) if field.startswith("I:") else field
            )
            print(f"{display_field:<25} - {clean_desc} (use: {field})")

        # Component properties
        if component_fields:
            print("\nCOMPONENT PROPERTIES:")
            print("-" * 30)
            for field, description in sorted(component_fields.items()):
                # Remove the "Component property: " prefix and the "C:" prefix from field name
                clean_desc = description.replace("Component property: ", "")
                display_field = (
                    field.replace("C:", "", 1) if field.startswith("C:") else field
                )
                print(f"{display_field:<25} - {clean_desc} (use: {field})")

        print("\nExample usage (custom fields):")
        print(
            f"  python {sys.argv[0]} project.kicad_sch -i inventory.csv -f Reference,Quantity,Value,LCSC"
        )
        print(f"\nExample usage (preset expansion):")
        print(f"  python {sys.argv[0]} project.kicad_sch -i inventory.xlsx -f +jlc")
        print(f"  python {sys.argv[0]} project.kicad_sch -i inventory.csv -f +standard")
        print(f"\nExample usage (mixed preset + custom):")
        print(
            f"  python {sys.argv[0]} project.kicad_sch -i inventory.csv -f +jlc,I:Tolerance,C:Voltage"
        )
        return

    # Define default fields and parse custom fields if provided
    any_notes = any((e.notes or "").strip() for e in bom_entries)
    available_fields = bom_generator.get_available_fields(components)

    # Parse --fields argument (supports presets with + prefix or custom field lists)
    try:
        fields = _parse_fields_argument(
            args.fields, available_fields, args.verbose, any_notes
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    # JSON report (optional)
    if args.json_report:
        try:
            unmatched = sum(1 for e in bom_entries if not (e.lcsc or "").strip())
            report = {
                "project": str(project_path),
                "inventory": str(inventory_path),
                "bom_entries": len(bom_entries),
                "unmatched": unmatched,
                "smd_excluded": smd_excluded_count,
                "format": "console" if console_output else "csv",
                "output": "-" if console_output else str(output_path),
                "verbose": args.verbose,
                "debug": args.debug,
                "smd_only": args.smd,
            }
            with open(args.json_report, "w", encoding="utf-8") as jf:
                json.dump(report, jf, indent=2)
        except Exception:
            pass

    if console_output:
        # Console output mode - don't write CSV file, just show table and summary
        if not args.quiet:
            print_formatted_summary(
                file_info,
                inventory_path,
                len(matcher.inventory),
                output_path,
                len(bom_entries),
                args.smd,
                smd_excluded_count,
                console_output=True,
            )
            # Print debug diagnostics first if enabled
            if args.debug and debug_diagnostics:
                print_debug_diagnostics(debug_diagnostics)
            # Print BOM table
            print_bom_table(bom_entries, verbose=args.verbose, include_mfg=False)
    else:
        # Normal CSV output mode
        if args.multi_format:
            formats = [
                f.strip().lower() for f in args.multi_format.split(",") if f.strip()
            ]
        else:
            formats = ["standard"]

        # Determine base name and directory
        out_base = (
            output_path.stem[:-4]
            if output_path.name.endswith("_bom.csv")
            else output_path.stem
        )
        out_dir = output_path.parent
        for fmt in formats:
            # If --fields was specified, use it as-is; otherwise use preset for that format
            fmt_fields = (
                fields if args.fields else _preset_fields(fmt, args.verbose, any_notes)
            )
            out_file = (
                output_path
                if len(formats) == 1
                else out_dir / f"{out_base}_bom.{fmt}.csv"
            )
            bom_generator.write_bom_csv(bom_entries, out_file, fmt_fields)

        # Print formatted summary
        if not args.quiet:
            print_formatted_summary(
                file_info,
                inventory_path,
                len(matcher.inventory),
                output_path,
                len(bom_entries),
                args.smd,
                smd_excluded_count,
                console_output=False,
            )
            # Print debug diagnostics if debug mode is enabled and there are diagnostics
            if args.debug and debug_diagnostics:
                print_debug_diagnostics(debug_diagnostics)

    # Exit with 2 when there are unmatched entries (warning state), else 0
    try:
        unmatched_exit = sum(1 for e in bom_entries if not (e.lcsc or "").strip())
        if unmatched_exit > 0:
            sys.exit(2)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        # Hard error
        sys.exit(1)
