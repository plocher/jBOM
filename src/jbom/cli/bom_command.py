"""BOM command implementation."""
from __future__ import annotations
import argparse
from pathlib import Path

from jbom.api import generate_bom, BOMOptions
from jbom.common.fields import parse_fields_argument
from jbom.common.output import resolve_output_path
from jbom.cli.commands import Command, OutputMode
from jbom.cli.common import apply_jlc_flag
from jbom.cli.formatting import print_bom_table

__all__ = ["BOMCommand"]


class BOMCommand(Command):
    """Generate Bill of Materials from KiCad schematic"""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Setup BOM-specific arguments"""
        parser.description = (
            "Generate Bill of Materials (BOM) from KiCad schematic "
            "with inventory matching"
        )
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
        parser.epilog = """Examples:
  jbom bom project/ -i inventory.csv                    # Generate BOM with default fields
  jbom bom project/ -i inventory.csv -o console         # Display formatted table
  jbom bom project/ -i inventory.csv -o - | grep LCSC   # CSV to stdout for piping
  jbom bom project/ -i inventory.csv --jlc              # Use JLCPCB field preset
  jbom bom project/ -i inventory.csv -f +jlc,Tolerance  # Mix preset with custom fields
  jbom bom project/ -i inventory.csv -v                 # Include match quality scores
  jbom bom project/ -i inventory.csv --smd-only         # Only surface-mount components
"""

        # Positional arguments
        parser.add_argument(
            "project", help="Path to KiCad project directory or .kicad_sch file"
        )
        parser.add_argument(
            "-i",
            "--inventory",
            required=True,
            metavar="FILE",
            help="Inventory file containing component data (.csv, .xlsx, .xls, or .numbers format)",
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
    +standard - Reference, Quantity, Description, Value, Footprint, LCSC, Datasheet, SMD (default)
    +jlc      - Reference, Quantity, Value, Package, LCSC, SMD (JLCPCB format)
    +minimal  - Reference, Quantity, Value, LCSC
    +all      - All available fields
  Custom fields: Reference,Value,LCSC,Manufacturer,I:Tolerance
  Mixed: +jlc,I:Voltage,C:Tolerance
  Use I: prefix for inventory fields, C: for component fields"""
        self.add_jlc_field_args(parser, field_help)

        # Filters and options
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help=(
                "Include verbose output: add Match_Quality and Priority "
                "columns showing match scores"
            ),
        )
        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            help="Enable debug mode: add detailed matching diagnostics to Notes column",
        )
        parser.add_argument(
            "--smd-only",
            action="store_true",
            help="Filter output to only include surface-mount (SMD) components",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute BOM generation"""
        # Generate BOM using v3.0 API
        opts = BOMOptions(
            verbose=args.verbose, debug=args.debug, smd_only=args.smd_only, fields=None
        )
        result = generate_bom(
            input=args.project, inventory=args.inventory, options=opts
        )

        # Process fields
        any_notes = any(((e.notes or "").strip()) for e in result["bom_entries"])
        fields_arg = apply_jlc_flag(args.fields, args.jlc)

        if fields_arg:
            fields = parse_fields_argument(
                fields_arg,
                result["available_fields"],
                include_verbose=args.verbose,
                any_notes=any_notes,
            )
        else:
            fields = parse_fields_argument(
                "+standard",
                result["available_fields"],
                include_verbose=args.verbose,
                any_notes=any_notes,
            )

        # Handle output
        output_mode, output_path = self.determine_output_mode(args.output)

        if output_mode == OutputMode.CONSOLE:
            print_bom_table(
                result["bom_entries"], verbose=args.verbose, include_mfg=False
            )
        elif output_mode == OutputMode.STDOUT:
            # Use generator from result dict
            bom_gen = result["generator"]
            bom_gen.write_bom_csv(result["bom_entries"], Path("-"), fields)
        else:
            # File output
            if output_path:
                out = output_path
            else:
                out = resolve_output_path(
                    Path(args.project), args.output, args.outdir, "_bom.csv"
                )
            # Use generator from result dict
            bom_gen = result["generator"]
            bom_gen.write_bom_csv(result["bom_entries"], out, fields)

        return 0
