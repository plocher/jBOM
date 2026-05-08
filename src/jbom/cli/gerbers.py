"""Gerbers command — standalone Gerber/drill/netlist generation.

``jbom gerbers`` is the correctness-validation path for KiCad Gerber generation:
it exercises :class:`~jbom.services.gerber_service.GerberExporter` in isolation
before the ``fab`` workflow calls it as part of a larger run.

It follows the same thin adapter pattern as ``bom.py`` and ``pos.py``:
argument parsing and output rendering only; all generation logic is in the
application/service layer.
"""

from __future__ import annotations

import sys
from pathlib import Path

from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_from_args,
)
from jbom.services.gerber_service import GerberExporter, GerberRequest, GerberResult
from jbom.services.project_file_resolver import ProjectFileResolver


def register_command(subparsers) -> None:  # type: ignore[type-arg]
    """Register the ``gerbers`` command with the argument parser."""
    parser = subparsers.add_parser(
        "gerbers",
        help="Generate Gerber/drill/netlist fabrication files from a KiCad PCB",
        description=(
            "Generate Gerber, drill, and IPC-D-356 netlist fabrication files "
            "from a KiCad PCB file using kicad-cli.  "
            "Requires KiCad with kicad-cli on the system PATH."
        ),
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help=(
            "Path to .kicad_pcb file, project directory, or base name "
            "(default: current directory)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        default=None,
        help=(
            "Output directory for Gerber/drill files "
            "(default: <project_dir>/gerbers/)"
        ),
    )
    parser.add_argument(
        "--no-drill",
        action="store_true",
        help="Skip drill file generation",
    )
    parser.add_argument(
        "--no-netlist",
        action="store_true",
        help="Skip IPC-D-356 netlist generation (default: netlist not generated)",
    )
    parser.add_argument(
        "--netlist",
        action="store_true",
        help="Also generate an IPC-D-356 netlist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check prerequisites (kicad-cli, PCB file) without generating files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    add_fabricator_arguments(parser)
    parser.set_defaults(handler=handle_gerbers)


def handle_gerbers(args) -> int:  # type: ignore[type-arg]
    """Handle the ``jbom gerbers`` command."""
    try:
        return _execute_gerbers_command(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _execute_gerbers_command(args) -> int:  # type: ignore[type-arg]
    """Resolve PCB file, build a GerberRequest, and call GerberExporter."""
    fabricator = resolve_fabricator_from_args(args)
    input_path = str(args.input or ".")
    include_drill = not bool(args.no_drill)
    include_netlist = bool(args.netlist) and not bool(args.no_netlist)
    dry_run = bool(args.dry_run)
    verbose = bool(args.verbose)

    # Resolve PCB file from the input path
    pcb_file, project_dir = _resolve_pcb_file(input_path, verbose=verbose)
    if pcb_file is None:
        print(
            f"Error: could not resolve a KiCad PCB file from '{input_path}'.",
            file=sys.stderr,
        )
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    elif project_dir is not None:
        output_dir = project_dir / "gerbers"
    else:
        output_dir = pcb_file.parent / "gerbers"

    if dry_run:
        print(f"Dry run: PCB file  : {pcb_file}")
        print(f"Dry run: Output dir: {output_dir}")
        print(f"Dry run: Fabricator: {fabricator}")
        print(f"Dry run: Drill     : {'yes' if include_drill else 'no'}")
        print(f"Dry run: Netlist   : {'yes' if include_netlist else 'no'}")
        # Check prerequisites without generating
        import shutil

        if shutil.which("kicad-cli") is None:
            print(
                "Warning: kicad-cli not found on PATH — "
                "Gerber generation would be skipped.",
                file=sys.stderr,
            )
            return 1
        if not pcb_file.exists():
            print(
                f"Warning: PCB file '{pcb_file}' does not exist — "
                "Gerber generation would be skipped.",
                file=sys.stderr,
            )
            return 1
        print("Dry run: Prerequisites OK.")
        return 0

    request = GerberRequest(
        pcb_file=pcb_file,
        output_directory=output_dir,
        fabricator=fabricator,
        include_drill=include_drill,
        include_netlist=include_netlist,
    )

    result = GerberExporter().generate(request)
    return _render_gerber_result(result, verbose=verbose)


def _render_gerber_result(result: GerberResult, *, verbose: bool) -> int:
    """Print GerberResult diagnostics and artifact paths; return exit code."""
    for diagnostic in result.diagnostics:
        print(diagnostic, file=sys.stderr)

    if result.skipped:
        print(
            f"Gerber generation skipped ({result.skip_reason}). " "See messages above.",
            file=sys.stderr,
        )
        return 1

    if not result.artifacts:
        print(
            "Warning: kicad-cli succeeded but no output files were found.",
            file=sys.stderr,
        )
        return 1

    for path in result.artifacts:
        print(f"Written: {path}")

    if verbose:
        print(f"\n{len(result.artifacts)} fabrication file(s) generated.")
    return 0


def _resolve_pcb_file(
    input_path: str,
    *,
    verbose: bool,
) -> tuple[Path | None, Path | None]:
    """Resolve the PCB file from an input path.

    Returns:
        ``(pcb_file, project_directory)`` — both ``None`` on failure.
    """
    try:
        resolver = ProjectFileResolver(prefer_pcb=True, target_file_type="pcb")
        resolved = resolver.resolve_input(input_path)
        if not resolved.is_pcb:
            resolved = resolver.resolve_for_wrong_file_type(resolved, "pcb")
        pcb_file = resolved.resolved_path
        project_dir: Path | None = None
        if resolved.project_context:
            project_dir = resolved.project_context.project_directory
        if project_dir is None:
            project_dir = pcb_file.parent
        return pcb_file, project_dir
    except Exception as exc:
        if verbose:
            print(f"Note: PCB resolution failed: {exc}", file=sys.stderr)
        return None, None
