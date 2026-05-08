"""Fabrication command — one-shot BOM + POS + Gerber generation.

``jbom fab`` is a convenience orchestrator equivalent to running::

    jbom bom   <project> --fabricator <fab>
    jbom pos   <project> --fabricator <fab>
    jbom gerbers <project> --fabricator <fab>

in sequence.  It delegates all generation logic to
:class:`~jbom.application.fabrication_orchestration.FabricationWorkflow`.

Field customisation is intentionally not supported here: ``--fabricator``
selects the profile and its configured default fields are used for both BOM
and POS.  Users who need per-field control should run ``jbom bom`` and
``jbom pos`` individually, or define a custom fabricator config.

This module imports ``_output_bom`` and ``_output_pos`` from the sibling CLI
modules to reuse their field-resolution and CSV-writing logic.  This coupling
is within the CLI adapter layer and is acceptable; the layering cleanup is
tracked in issue #237.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from jbom.application.fabrication_orchestration import (
    FabricationRequest,
    FabricationResult,
    FabricationWorkflow,
)
from jbom.application.jobs.contracts import (
    JobContext,
    JobDiagnosticSeverity,
    JobOutcome,
    JobRequest,
)
from jbom.application.jobs.runner import JobEventStream, JobRunPayload, JobRunner
from jbom.cli.bom import _output_bom
from jbom.cli.output import add_force_argument
from jbom.cli.pos import _output_pos
from jbom.common.cli_fabricator import (
    add_fabricator_arguments,
    resolve_fabricator_from_args,
)


def register_command(subparsers) -> None:  # type: ignore[type-arg]
    """Register the ``fab`` command with the argument parser."""
    parser = subparsers.add_parser(
        "fab",
        help="Generate BOM, placement, and Gerber fabrication files in one shot",
        description=(
            "Run BOM, POS (placement), and Gerber/drill generation for a KiCad "
            "project in one coordinated step.  "
            "Equivalent to running `jbom bom`, `jbom pos`, and `jbom gerbers` "
            "in sequence with the same fabricator profile.\n\n"
            "For per-field control use the individual commands.  "
            "For non-default field sets define a custom fabricator config "
            "(e.g. myspecialfab.yaml) and pass --fabricator myspecialfab."
        ),
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help=(
            "Path to KiCad project directory, .kicad_pro, .kicad_pcb, "
            "or .kicad_sch file (default: current directory)"
        ),
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        metavar="DIR",
        default=None,
        help=(
            "Override output directory for all generated files.  "
            "BOM and POS CSVs are written here; Gerbers go to <DIR>/gerbers/.  "
            "Default: project directory for BOM/POS, <project_dir>/gerbers/ for Gerbers."
        ),
    )
    add_force_argument(parser)

    # Step-skipping flags
    parser.add_argument(
        "--skip-bom",
        action="store_true",
        help="Skip BOM generation",
    )
    parser.add_argument(
        "--skip-pos",
        action="store_true",
        help="Skip POS (placement) generation",
    )
    parser.add_argument(
        "--skip-gerbers",
        action="store_true",
        help="Skip Gerber/drill generation",
    )

    # Gerber netlist opt-in
    parser.add_argument(
        "--netlist",
        action="store_true",
        help="Also generate an IPC-D-356 netlist during Gerber step",
    )

    # Inventory enhancement (forwarded to BOM)
    parser.add_argument(
        "--inventory",
        action="append",
        dest="inventory_files",
        metavar="FILE",
        help="Inventory CSV to enhance BOM (repeatable)",
    )

    # POS options (forwarded to POS orchestration)
    parser.add_argument(
        "--smd-only",
        action="store_true",
        help="Include only SMD components in POS output",
    )
    parser.add_argument(
        "--layer",
        choices=["TOP", "BOTTOM"],
        help="Include only components on specified layer in POS output",
    )
    parser.add_argument(
        "--origin",
        choices=["board", "aux"],
        default="board",
        help="Origin reference for POS coordinates (default: board)",
    )

    # Dry-run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Generate BOM/POS data but do not write files; "
            "skip Gerber generation entirely"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    add_fabricator_arguments(parser)
    parser.set_defaults(handler=handle_fab)


def handle_fab(args) -> int:  # type: ignore[type-arg]
    """Handle the ``jbom fab`` command through the shared job runner."""
    request = _build_fab_job_request(args)
    context = JobContext(
        adapter_id="cli",
        session_id="local-process",
        capabilities={
            "event_stream": True,
            "diagnostics": True,
            "cancellation": False,
        },
    )
    runner = JobRunner()

    def _execute(events: JobEventStream) -> JobRunPayload:
        events.progress(
            phase="resolve",
            message="Resolving project input and fabrication plan",
        )
        exit_code = _execute_fab_command(args)
        if exit_code == 0:
            events.progress(phase="emit", message="Fabrication outputs emitted")
        else:
            events.diagnostic(
                severity=JobDiagnosticSeverity.ERROR,
                message="Fabrication command execution failed",
                code="fab_execution_failed",
                details={"exit_code": exit_code},
            )
        return JobRunPayload(
            outcome=JobOutcome.SUCCEEDED if exit_code == 0 else JobOutcome.FAILED,
            artifacts=(),
            metadata={"exit_code": exit_code, "command": "fab"},
        )

    result = runner.run(request=request, context=context, execute=_execute)
    if result.outcome == JobOutcome.CANCELLED:
        return 130
    return int(result.metadata.get("exit_code", 1))


def _build_fab_job_request(args) -> JobRequest:  # type: ignore[type-arg]
    """Build adapter-neutral JobRequest for fab execution."""
    fabricator = resolve_fabricator_from_args(args)
    return JobRequest(
        job_type="fab",
        intent="generate_fabrication_artifacts",
        project_ref=str(args.input or "."),
        options={
            "input": str(args.input or "."),
            "fabricator": fabricator,
            "skip_bom": bool(args.skip_bom),
            "skip_pos": bool(args.skip_pos),
            "skip_gerbers": bool(args.skip_gerbers),
            "dry_run": bool(args.dry_run),
        },
        metadata={"adapter": "cli"},
    )


def _execute_fab_command(args) -> int:  # type: ignore[type-arg]
    """Build FabricationRequest, run FabricationWorkflow, write outputs."""
    try:
        fabricator = resolve_fabricator_from_args(args)
        output_dir: Optional[Path] = Path(args.output_dir) if args.output_dir else None
        dry_run = bool(args.dry_run)
        force = bool(args.force)

        request = FabricationRequest(
            input_path=str(args.input or "."),
            fabricator=fabricator,
            output_directory=str(output_dir) if output_dir else "",
            skip_bom=bool(args.skip_bom),
            skip_pos=bool(args.skip_pos),
            skip_gerbers=bool(args.skip_gerbers),
            verbose=bool(args.verbose),
            dry_run=dry_run,
            inventory_files=tuple(str(p) for p in (args.inventory_files or [])),
            smd_only=bool(args.smd_only),
            pos_layer=str(args.layer or ""),
            pos_origin=str(args.origin or "board"),
        )

        # Create output directory if explicitly specified
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)

        result = FabricationWorkflow().run(request)

        # Emit diagnostics
        for diag in result.diagnostics:
            print(diag, file=sys.stderr)

        exit_code = 0

        # --- Write BOM ---
        if not request.skip_bom:
            exit_code = max(
                exit_code,
                _write_bom_output(result, fabricator, output_dir, dry_run, force),
            )

        # --- Write POS ---
        if not request.skip_pos:
            exit_code = max(
                exit_code,
                _write_pos_output(result, output_dir, dry_run, force),
            )

        # --- Report Gerbers ---
        if not request.skip_gerbers and not dry_run:
            _report_gerber_output(result)

        return exit_code

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _write_bom_output(
    result: FabricationResult,
    fabricator: str,
    output_dir: Optional[Path],
    dry_run: bool,
    force: bool,
) -> int:
    """Write the BOM CSV from a FabricationResult payload."""
    if result.bom_result is None or result.bom_result.generation is None:
        print("Note: BOM generation produced no output.", file=sys.stderr)
        return 0

    gen = result.bom_result.generation
    bom_output: Optional[str] = None
    if output_dir is not None:
        bom_output = str(output_dir / gen.default_output_path.name)

    if dry_run:
        dest = bom_output or str(gen.default_output_path)
        print(f"Dry run: BOM would be written to {dest}")
        return 0

    return _output_bom(
        gen.bom_data,
        bom_output,
        list(gen.selected_fields),
        fabricator,
        default_output_path=gen.default_output_path,
        force=force,
    )


def _write_pos_output(
    result: FabricationResult,
    output_dir: Optional[Path],
    dry_run: bool,
    force: bool,
) -> int:
    """Write the POS CSV from a FabricationResult payload."""
    if result.pos_result is None or result.pos_result.generation is None:
        print("Note: POS generation produced no output.", file=sys.stderr)
        return 0

    gen = result.pos_result.generation
    pos_output: Optional[str] = None
    if output_dir is not None:
        pos_output = str(output_dir / gen.default_output_path.name)

    if dry_run:
        dest = pos_output or str(gen.default_output_path)
        print(f"Dry run: POS would be written to {dest}")
        return 0

    return _output_pos(
        list(gen.pos_data),
        pos_output,
        selected_fields=list(gen.selected_fields),
        headers=list(gen.headers),
        fabricator=gen.fabricator,
        fabricator_config=gen.fabricator_config,
        default_output_path=gen.default_output_path,
        force=force,
    )


def _report_gerber_output(result: FabricationResult) -> None:
    """Print Gerber artifact paths or skip reason to stdout/stderr."""
    if result.gerber_result is None:
        print(
            "Note: Gerber generation produced no result. " "Check diagnostics above.",
            file=sys.stderr,
        )
        return

    if result.gerber_result.skipped:
        print(
            f"Note: Gerber generation skipped "
            f"({result.gerber_result.skip_reason}). "
            "Check diagnostics above.",
            file=sys.stderr,
        )
        return

    for artifact in result.artifacts:
        if artifact.artifact_type in ("gerber", "drill", "netlist"):
            print(f"Gerber: {artifact.path}")
