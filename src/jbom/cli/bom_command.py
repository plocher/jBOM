"""BOM command implementation."""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Optional

from jbom.api import generate_bom, BOMOptions
from jbom.common.output import resolve_output_path
from jbom.cli.commands import Command, OutputMode
from jbom.cli.formatting import print_bom_table
from jbom.common.config_fabricators import (
    get_fabricator_by_cli_flag,
    get_fabricator_by_preset,
    get_fabricator_registry,
)

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
            required=False,
            action="append",
            metavar="FILE",
            help=(
                "Inventory file(s) containing component data (.csv, .xlsx, .xls, or .numbers format). "
                "Can be specified multiple times. "
                "If omitted, inventory is generated from project components."
            ),
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
        self.add_fabricator_field_args(parser, field_help)

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
            "--fabricator",
            choices=sorted(get_fabricator_registry().list_fabricators()),
            help="Specify PCB fabricator for part number lookup (e.g. jlc, seeed)",
        )
        parser.add_argument(
            "--smd-only",
            action="store_true",
            help="Filter output to only include surface-mount (SMD) components",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute BOM generation"""
        # Apply fabricator flags to fields first
        fields_arg = self._apply_fabricator_flags_to_fields(args)

        # Determine fabricator using config-driven approach
        fabricator = self._determine_fabricator(args, fields_arg)

        # Generate BOM using v3.0 API
        opts = BOMOptions(
            verbose=args.verbose,
            debug=args.debug,
            smd_only=args.smd_only,
            fields=None,
            fabricator=fabricator,
        )
        result = generate_bom(
            input=args.project, inventory=args.inventory, options=opts
        )

        # Print debug diagnostics if enabled
        if args.debug and result.get("debug_diagnostics"):
            import sys

            print("\n--- Match Diagnostics ---", file=sys.stderr)
            for diag in result["debug_diagnostics"]:
                # Use generator to format if possible, else print raw
                if "generator" in result and hasattr(
                    result["generator"], "_generate_diagnostic_message"
                ):
                    msg = result["generator"]._generate_diagnostic_message(
                        diag, "console"
                    )
                    print(msg, file=sys.stderr)
                else:
                    print(f"Diagnostic: {diag}", file=sys.stderr)

        # Process fields
        any_notes = any(((e.notes or "").strip()) for e in result["bom_entries"])
        bom_gen = result["generator"]

        if fields_arg:
            fields = bom_gen.parse_fields_argument(
                fields_arg,
                result["available_fields"],
                include_verbose=args.verbose,
                any_notes=any_notes,
            )
        else:
            fields = bom_gen.parse_fields_argument(
                "+default",
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

    def _determine_fabricator(
        self, args: argparse.Namespace, fields_arg: str
    ) -> Optional[str]:
        """Determine fabricator ID using config-driven approach."""
        # 1. Explicit --fabricator argument takes precedence
        if args.fabricator:
            return args.fabricator

        # 2. Check for dynamic fabricator flags (fabricator_jlc, fabricator_pcbway, etc.)
        for attr_name in dir(args):
            if attr_name.startswith("fabricator_") and getattr(args, attr_name):
                # Convert fabricator_jlc -> --jlc
                flag_name = attr_name.replace("fabricator_", "--")
                fab = get_fabricator_by_cli_flag(flag_name)
                if fab:
                    return fab.config.id

        # 3. Check for fabricator-specific presets in fields_arg
        if fields_arg:
            for preset in fields_arg.split(","):
                preset = preset.strip()
                if preset.startswith("+"):
                    fab = get_fabricator_by_preset(preset)
                    if fab:
                        return fab.config.id

        # 4. No fabricator specified - will use default
        return None

    def _apply_fabricator_flags_to_fields(
        self, args: argparse.Namespace
    ) -> Optional[str]:
        """Apply fabricator flags to fields argument.

        Converts fabricator flags (fabricator_jlc, etc.) into field presets.

        Args:
            args: Parsed command-line arguments

        Returns:
            Modified fields argument with fabricator presets prepended if needed
        """
        fields_arg = args.fields

        # Find any active fabricator flags
        for attr_name in dir(args):
            if attr_name.startswith("fabricator_") and getattr(args, attr_name):
                # Convert fabricator_jlc -> +jlc
                preset_name = attr_name.replace("fabricator_", "+")

                # If no fields specified, just use the preset
                if not fields_arg:
                    fields_arg = preset_name
                elif preset_name not in fields_arg.split(","):
                    # Prepend preset to existing fields
                    fields_arg = f"{preset_name},{fields_arg}"

        return fields_arg
