"""jBOM CLI (breaking v2): subcommands 'bom' and 'pos'.

- bom: generate BOM from schematic (existing algorithm)
- pos: generate placement/CPL from PCB
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

from jbom.jbom import (
    GenerateOptions,
    generate_bom_api,
    _parse_fields_argument,
    print_bom_table,
)
from jbom.pcb.board_loader import load_board
from jbom.pcb.position import PositionGenerator, PlacementOptions, print_pos_table
from jbom.common.utils import find_best_pcb
from jbom.common.output import resolve_output_path
from jbom.cli.common import apply_jlc_flag


def _cmd_bom(argv: List[str]) -> int:
    """BOM command handler with exception handling."""
    try:
        return _cmd_bom_impl(argv)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, ImportError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def _cmd_bom_impl(argv: List[str]) -> int:
    """BOM command implementation."""
    p = argparse.ArgumentParser(
        prog="jbom bom",
        description="Generate Bill of Materials (BOM) from KiCad schematic with inventory matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  jbom bom project/ -i inventory.csv                    # Generate BOM with default fields
  jbom bom project/ -i inventory.csv -o console         # Display formatted table
  jbom bom project/ -i inventory.csv -o - | grep LCSC   # CSV to stdout for piping
  jbom bom project/ -i inventory.csv --jlc              # Use JLCPCB field preset
  jbom bom project/ -i inventory.csv -f +jlc,Tolerance  # Mix preset with custom fields
  jbom bom project/ -i inventory.csv -v                 # Include match quality scores
  jbom bom project/ -i inventory.csv --smd-only         # Only surface-mount components
""",
    )
    p.add_argument("project", help="Path to KiCad project directory or .kicad_sch file")
    p.add_argument(
        "-i",
        "--inventory",
        required=True,
        metavar="FILE",
        help="Inventory file containing component data (.csv, .xlsx, .xls, or .numbers format)",
    )
    p.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="""Output destination:
  filename.csv  - Write to file
  -             - CSV to stdout (pipeline-friendly)
  stdout        - CSV to stdout (pipeline-friendly)
  console       - Formatted table to console (human-readable)
  (default: PROJECT_bom.csv in project directory)""",
    )
    p.add_argument(
        "--outdir",
        metavar="DIR",
        help="Output directory for generated files (only used if -o not specified)",
    )
    p.add_argument(
        "-f",
        "--fields",
        metavar="FIELDS",
        help="""Field selection: comma-separated list of fields or presets.
  Presets (use + prefix):
    +standard - Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet, SMD (default)
    +jlc      - Reference, Quantity, Value, Package, LCSC, SMD (JLCPCB format)
    +minimal  - Reference, Quantity, Value, LCSC
    +all      - All available fields
  Custom fields: Reference,Value,LCSC,Manufacturer,I:Tolerance
  Mixed: +jlc,I:Voltage,C:Tolerance
  Use I: prefix for inventory fields, C: for component fields""",
    )
    p.add_argument(
        "--jlc",
        action="store_true",
        help="Use JLCPCB field preset (+jlc): optimized for JLCPCB assembly service",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Include verbose output: add Match_Quality and Priority columns showing match scores",
    )
    p.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode: add detailed matching diagnostics to Notes column",
    )
    p.add_argument(
        "--smd-only",
        action="store_true",
        help="Filter output to only include surface-mount (SMD) components",
    )
    args = p.parse_args(argv)

    opts = GenerateOptions(
        verbose=args.verbose, debug=args.debug, smd_only=args.smd_only, fields=None
    )
    result = generate_bom_api(args.project, args.inventory, options=opts)

    # Compute fields (apply --jlc implication using shared utility)
    any_notes = any(((e.notes or "").strip()) for e in result["bom_entries"])
    fields_arg = apply_jlc_flag(args.fields, args.jlc)
    if fields_arg:
        fields = _parse_fields_argument(
            fields_arg,
            result["available_fields"],
            include_verbose=args.verbose,
            any_notes=any_notes,
        )
    else:
        fields = _parse_fields_argument(
            "+standard",
            result["available_fields"],
            include_verbose=args.verbose,
            any_notes=any_notes,
        )

    # Check output mode: CSV to stdout vs formatted console table
    output_str = args.output.lower() if args.output else ""
    csv_to_stdout = output_str in ("-", "stdout")
    formatted_console = output_str == "console"

    if formatted_console:
        # Formatted table output to console (human-readable)
        print_bom_table(result["bom_entries"], verbose=args.verbose, include_mfg=False)
    elif csv_to_stdout:
        # CSV output to stdout (pipeline-friendly)
        from jbom.jbom import InventoryMatcher, BOMGenerator

        matcher = InventoryMatcher(Path(args.inventory))
        bom_gen = BOMGenerator(result["components"], matcher)
        bom_gen.write_bom_csv(result["bom_entries"], Path("-"), fields)
    else:
        # Determine output path using shared utility
        out = resolve_output_path(
            Path(args.project), args.output, args.outdir, "_bom.csv"
        )

        # Write via BOMGenerator (recreate matcher)
        from jbom.jbom import InventoryMatcher, BOMGenerator

        matcher = InventoryMatcher(Path(args.inventory))
        bom_gen = BOMGenerator(result["components"], matcher)
        bom_gen.write_bom_csv(result["bom_entries"], out, fields)

    return 0


def _cmd_pos(argv: List[str]) -> int:
    """POS command handler with exception handling."""
    try:
        return _cmd_pos_impl(argv)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, ImportError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def _cmd_pos_impl(argv: List[str]) -> int:
    """POS command implementation."""
    p = argparse.ArgumentParser(
        prog="jbom pos",
        description=(
            "Generate component placement (POS/CPL) file from "
            "KiCad PCB for pick-and-place assembly"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  jbom pos board.kicad_pcb                              # Generate POS with default fields
  jbom pos board.kicad_pcb -o console                   # Display formatted table
  jbom pos board.kicad_pcb -o - | wc -l                 # CSV to stdout for piping
  jbom pos board.kicad_pcb --jlc                        # Use JLCPCB field preset
  jbom pos board.kicad_pcb -f +standard,datasheet       # Add custom fields
  jbom pos board.kicad_pcb --units inch --origin aux    # Imperial units with aux origin
  jbom pos board.kicad_pcb --layer TOP                  # Only top-side components
""",
    )
    p.add_argument("board", help="Path to KiCad project directory or .kicad_pcb file")
    p.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="""Output destination:
  filename.csv  - Write to file
  -             - CSV to stdout (pipeline-friendly)
  stdout        - CSV to stdout (pipeline-friendly)
  console       - Formatted table to console (human-readable)
  (default: BOARD_pos.csv in board directory)""",
    )
    p.add_argument(
        "-f",
        "--fields",
        metavar="FIELDS",
        help="""Field selection: comma-separated list of fields or presets.
  Presets (use + prefix):
    +standard - Reference, X, Y, Rotation, Side, Footprint, SMD (default)
    +jlc      - Reference, Side, X, Y, Rotation, Package, SMD (JLCPCB format)
    +minimal  - Reference, X, Y, Side
    +all      - All available fields
  Available fields: reference, x, y, rotation, side, footprint, package, datasheet, version, smd
  Custom: Reference,X,Y,Rotation,SMD
  Mixed: +standard,datasheet,version""",
    )
    p.add_argument(
        "--jlc",
        action="store_true",
        help="Use JLCPCB field preset (+jlc): optimized for JLCPCB assembly service",
    )
    p.add_argument(
        "--units",
        choices=["mm", "inch"],
        default="mm",
        help="Coordinate units for X/Y positions (default: mm)",
    )
    p.add_argument(
        "--origin",
        choices=["board", "aux"],
        default="board",
        help="""Coordinate origin:
  board - Use board origin (lower-left corner, typically 0,0)
  aux   - Use auxiliary axis origin (user-defined in PCB)
  (default: board)""",
    )
    p.add_argument(
        "--smd-only",
        action="store_true",
        default=True,
        help="Include only surface-mount components (default: enabled)",
    )
    p.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        metavar="SIDE",
        help="Filter to only components on specified layer (TOP or BOTTOM)",
    )
    p.add_argument(
        "--loader",
        choices=["auto", "pcbnew", "sexp"],
        default="auto",
        help="""PCB loading method:
  auto   - Try pcbnew API, fallback to S-expression parser (default)
  pcbnew - Use KiCad pcbnew Python API (requires KiCad Python environment)
  sexp   - Use built-in S-expression parser (works without KiCad)""",
    )
    args = p.parse_args(argv)

    # Find PCB file (auto-detect if directory)
    board_path_input = Path(args.board)
    board_path = find_best_pcb(board_path_input)
    if not board_path:
        print(f"Error: Could not find PCB file in {board_path_input}", file=sys.stderr)
        return 1

    board = load_board(board_path, mode=args.loader)
    opts = PlacementOptions(
        units=args.units,
        origin=args.origin,
        smd_only=args.smd_only,
        layer_filter=args.layer,
    )
    gen = PositionGenerator(board, opts)

    # Apply --jlc flag using shared utility
    fields_arg = apply_jlc_flag(args.fields, args.jlc)
    fields = (
        gen.parse_fields_argument(fields_arg)
        if fields_arg
        else gen.parse_fields_argument("+standard")
    )

    # Check output mode: CSV to stdout vs formatted console table
    output_str = args.output.lower() if args.output else ""
    csv_to_stdout = output_str in ("-", "stdout")
    formatted_console = output_str == "console"

    if formatted_console:
        # Formatted table output to console (human-readable)
        print_pos_table(gen, fields)
    elif csv_to_stdout:
        # CSV output to stdout (pipeline-friendly)
        gen.write_csv(Path("-"), fields)
    else:
        # Determine output path using shared utility
        out = resolve_output_path(
            board_path_input,
            args.output,
            None,  # pos command doesn't have --outdir
            "_pos.csv",
        )
        gen.write_csv(out, fields)

    return 0


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Handle --version flag
    if argv and argv[0] in ("-V", "--version"):
        from jbom.__version__ import __version__

        print(f"jBOM version {__version__}")
        return 0

    if not argv or argv[0] in ("-h", "--help"):
        print(
            """jBOM - KiCad Bill of Materials and Placement File Generator

Usage:
  jbom bom PROJECT -i INVENTORY [options]    Generate BOM from schematic
  jbom pos BOARD [options]                   Generate placement file from PCB
  jbom --version                             Show version information

Commands:
  bom    Generate Bill of Materials with inventory matching
  pos    Generate component placement (POS/CPL) file for pick-and-place

Get help on specific commands:
  jbom bom --help
  jbom pos --help

Examples:
  jbom bom project/ -i inventory.csv                    # Generate BOM
  jbom bom project/ -i inventory.csv -o console         # Show formatted table
  jbom bom project/ -i inventory.csv --jlc              # JLCPCB format
  jbom pos board.kicad_pcb                              # Generate placement file
  jbom pos board.kicad_pcb -o console                   # Show formatted table
  jbom pos board.kicad_pcb -f +kicad_pos,smd,datasheet  # Custom fields
"""
        )
        return 0
    cmd, *rest = argv
    if cmd == "bom":
        return _cmd_bom(rest)
    if cmd == "pos":
        return _cmd_pos(rest)
    print(f"Unknown command: {cmd}. Use 'bom' or 'pos'.", file=sys.stderr)
    return 2
