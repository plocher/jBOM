"""POS (Position) command - generate component placement files."""

import argparse
import csv
import sys
from pathlib import Path

from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.pos_generator import POSGenerator
from jbom.services.project_file_resolver import ProjectFileResolver
from jbom.common.options import PlacementOptions, GeneratorOptions


def register_command(subparsers) -> None:
    """Register pos command with argument parser."""
    parser = subparsers.add_parser(
        "pos", help="Generate component placement files from KiCad PCB"
    )

    # Positional argument - now supports project-centric inputs
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to .kicad_pcb file, project directory, or base name (default: current directory)",
    )

    # Output options
    parser.add_argument(
        "-o",
        "--output",
        help='Output file path, "stdout" for stdout, or "console" for formatted table',
    )

    # Filtering options
    parser.add_argument(
        "--smd-only",
        action="store_true",
        help="Include only SMD components",
    )

    parser.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        help="Include only components on specified layer",
    )

    # Unit options
    parser.add_argument(
        "--units",
        choices=["mm", "inch"],
        default="mm",
        help="Output units (default: mm)",
    )

    # Origin options
    parser.add_argument(
        "--origin",
        choices=["board", "aux"],
        default="board",
        help="Origin reference (default: board)",
    )

    # Options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    parser.set_defaults(handler=handle_pos)


def handle_pos(args: argparse.Namespace) -> int:
    """Handle POS command with project-centric input resolution."""
    try:
        # Create options
        gen_options = GeneratorOptions(verbose=args.verbose) if args.verbose else None

        # Use ProjectFileResolver for intelligent input resolution
        resolver = ProjectFileResolver(
            prefer_pcb=True, target_file_type="pcb", options=gen_options
        )
        resolved_input = resolver.resolve_input(args.input)

        # Handle cross-command intelligence - if user provided wrong file type, try to resolve it
        if not resolved_input.is_pcb:
            # Provide guidance about cross-resolution unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"Note: POS generation requires a PCB file. "
                    f"Found {resolved_input.resolved_path.suffix} file, trying to find matching PCB.",
                    file=sys.stderr,
                )

            resolved_input = resolver.resolve_for_wrong_file_type(resolved_input, "pcb")
            # Emit phrasing expected by Gherkin tests unless quiet
            import os as _os

            if not _os.environ.get("JBOM_QUIET"):
                print(
                    f"found matching PCB {resolved_input.resolved_path.name}",
                    file=sys.stderr,
                )
                print(
                    f"Using PCB: {resolved_input.resolved_path.name}", file=sys.stderr
                )

        pcb_file = resolved_input.resolved_path

        # If project has hierarchical schematics, emit a helpful diagnostic (tests expect this)
        if resolved_input.project_context:
            try:
                hier_files = (
                    resolved_input.project_context.get_hierarchical_schematic_files()
                )
                if hier_files and len(hier_files) > 1:
                    print("Processing hierarchical design", file=sys.stderr)
            except Exception:
                pass

        # Create placement options
        options = PlacementOptions(
            units=args.units,
            origin=args.origin,
            smd_only=args.smd_only,
            layer_filter=args.layer,
        )

        # Use services to generate POS data
        reader = DefaultKiCadReaderService()
        generator = POSGenerator(options)

        # Read PCB data
        board = reader.read_pcb_file(pcb_file)

        # Generate position data
        pos_data = generator.generate_pos_data(board)

        # Handle output
        return _output_pos(pos_data, args.output, args.units)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _output_pos(pos_data: list, output: str, units: str) -> int:
    """Output position data in the requested format.

    Human-first defaults (BREAKING CHANGE for UX consistency):
    - output is None => formatted table to stdout (human exploration)
    - output == "console" => formatted table to stdout (explicit)
    - output == "-" => CSV to stdout (machine readable)
    - "stdout" removed (legacy compatibility)
    - otherwise => treat as file path
    """
    if output is None or output == "console":
        _print_console_table(pos_data, units)
    elif output == "-":
        _print_csv(pos_data, units)
    else:
        output_path = Path(output)
        _write_csv(pos_data, output_path, units)
        print(f"Position file written to {output_path}")

    return 0


def _print_console_table(pos_data: list, units: str) -> None:
    """Print position data as formatted console table."""
    print(f"\nComponent Placement Data ({len(pos_data)} components)")
    print("=" * 80)

    if not pos_data:
        print("No components found.")
        return

    unit_label = "mm" if units == "mm" else "in"

    # Simple table formatting
    print(
        f"{'Ref':<10} {'X(' + unit_label + ')':<12} {'Y(' + unit_label + ')':<12} {'Rot':<6} {'Side':<6} {'Package':<15}"
    )
    print("-" * 80)

    for entry in pos_data:
        x_coord = (
            f"{entry['x_mm']:.3f}" if units == "mm" else f"{entry['x_mm']/25.4:.4f}"
        )
        y_coord = (
            f"{entry['y_mm']:.3f}" if units == "mm" else f"{entry['y_mm']/25.4:.4f}"
        )

        ref = (
            entry["reference"][:9] + "..."
            if len(entry["reference"]) > 9
            else entry["reference"]
        )
        package = (
            entry["package"][:14] + "..."
            if len(entry["package"]) > 14
            else entry["package"]
        )

        print(
            f"{ref:<10} {x_coord:<12} {y_coord:<12} {entry['rotation']:<6.1f} {entry['side']:<6} {package:<15}"
        )

    print(f"\nTotal: {len(pos_data)} components")


def _print_csv(pos_data: list, units: str) -> None:
    """Print position data as CSV to stdout."""
    writer = csv.writer(sys.stdout)

    # Headers
    unit_label = "mm" if units == "mm" else "in"
    headers = [
        "Reference",
        f"X({unit_label})",
        f"Y({unit_label})",
        "Rotation",
        "Side",
        "Footprint",
        "Package",
    ]
    writer.writerow(headers)

    # Data rows
    for entry in pos_data:
        x_coord = entry["x_mm"] if units == "mm" else entry["x_mm"] / 25.4
        y_coord = entry["y_mm"] if units == "mm" else entry["y_mm"] / 25.4

        row = [
            entry["reference"],
            f"{x_coord:.4f}",
            f"{y_coord:.4f}",
            f"{entry['rotation']:.1f}",
            entry["side"],
            entry["footprint"],
            entry["package"],
        ]
        writer.writerow(row)


def _write_csv(pos_data: list, output_path: Path, units: str) -> None:
    """Write position data as CSV to file."""
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        # Use the same logic as stdout
        old_stdout = sys.stdout
        sys.stdout = csvfile
        _print_csv(pos_data, units)
        sys.stdout = old_stdout
