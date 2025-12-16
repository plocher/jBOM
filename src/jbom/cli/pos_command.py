"""POS command implementation."""
from __future__ import annotations
import argparse
from pathlib import Path

from jbom.generators.pos import POSGenerator, PlacementOptions, print_pos_table
from jbom.common.output import resolve_output_path
from jbom.cli.commands import Command, OutputMode
from jbom.cli.common import apply_jlc_flag

__all__ = ["POSCommand"]


class POSCommand(Command):
    """Generate component placement file from KiCad PCB"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Setup POS-specific arguments"""
        parser.description = (
            "Generate component placement (POS/CPL) file from "
            "KiCad PCB for pick-and-place assembly"
        )
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.epilog = """Examples:
  jbom pos board.kicad_pcb                              # Generate POS with default fields
  jbom pos board.kicad_pcb -o console                   # Display formatted table
  jbom pos board.kicad_pcb -o - | wc -l                 # CSV to stdout for piping
  jbom pos board.kicad_pcb --jlc                        # Use JLCPCB field preset
  jbom pos board.kicad_pcb -f +standard,datasheet       # Add custom fields
  jbom pos board.kicad_pcb --units inch --origin aux    # Imperial units with aux origin
  jbom pos board.kicad_pcb --layer TOP                  # Only top-side components
"""

        # Positional arguments
        parser.add_argument(
            "board", help="Path to KiCad project directory or .kicad_pcb file"
        )

        # Output arguments
        self.add_common_output_args(parser)
        parser.add_argument(
            "--outdir",
            metavar="DIR",
            help="Output directory for generated files (only used if -o not specified)",
        )

        # Field selection
        field_help = """Field selection: comma-separated list of fields or presets.
  Presets (use + prefix):
    +standard - Reference, X, Y, Rotation, Side, Footprint, SMD (default)
    +jlc      - Reference, Side, X, Y, Rotation, Package, SMD (JLCPCB format)
    +minimal  - Reference, X, Y, Side
    +all      - All available fields
  Available fields: reference, x, y, rotation, side, footprint, package, datasheet, version, smd
  Custom: Reference,X,Y,Rotation,SMD
  Mixed: +standard,datasheet,version"""
        self.add_jlc_field_args(parser, field_help)

        # Coordinate options
        parser.add_argument(
            "--units",
            choices=["mm", "inch"],
            default="mm",
            help="Coordinate units for X/Y positions (default: mm)",
        )
        parser.add_argument(
            "--origin",
            choices=["board", "aux"],
            default="board",
            help="""Coordinate origin:
  board - Use board origin (lower-left corner, typically 0,0)
  aux   - Use auxiliary axis origin (user-defined in PCB)
  (default: board)""",
        )

        # Filters
        parser.add_argument(
            "--smd-only",
            action="store_true",
            default=True,
            help="Include only surface-mount components (default: enabled)",
        )
        parser.add_argument(
            "--layer",
            choices=["TOP", "BOTTOM"],
            metavar="SIDE",
            help="Filter to only components on specified layer (TOP or BOTTOM)",
        )

        # Loader mode
        parser.add_argument(
            "--loader",
            choices=["auto", "pcbnew", "sexp"],
            default="auto",
            help="""PCB loading method:
  auto   - Try pcbnew API, fallback to S-expression parser (default)
  pcbnew - Use KiCad pcbnew Python API (requires KiCad Python environment)
  sexp   - Use built-in S-expression parser (works without KiCad)""",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute POS generation"""
        # Create placement options
        opts = PlacementOptions(
            units=args.units,
            origin=args.origin,
            smd_only=args.smd_only,
            layer_filter=args.layer,
            loader_mode=args.loader,
        )

        # Process fields
        fields_arg = apply_jlc_flag(args.fields, args.jlc)
        if fields_arg:
            opts.fields = POSGenerator(opts).parse_fields_argument(fields_arg)

        gen = POSGenerator(opts)

        # Handle output
        output_mode, output_path = self.determine_output_mode(args.output)
        board_path_input = Path(args.board)

        if output_mode == OutputMode.CONSOLE:
            # Need to run first to load data
            gen.run(input=args.board)
            fields = opts.fields or gen.parse_fields_argument("+standard")
            print_pos_table(gen, fields)
        elif output_mode == OutputMode.STDOUT:
            # Run with stdout output
            fields = opts.fields or gen.parse_fields_argument("+standard")
            opts.fields = fields
            gen.options = opts  # Update options
            gen.run(input=args.board, output="-")
        else:
            # File output
            if output_path:
                out = output_path
            else:
                out = resolve_output_path(
                    board_path_input, args.output, args.outdir, "_pos.csv"
                )
            fields = opts.fields or gen.parse_fields_argument("+standard")
            opts.fields = fields
            gen.options = opts  # Update options
            gen.run(input=args.board, output=out)

        return 0
