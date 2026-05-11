"""Fabrication command — one-shot BOM + POS + Gerber generation.

``jbom fab`` is a convenience orchestrator equivalent to running::

    jbom bom   <project> --fabricator <fab>
    jbom pos   <project> --fabricator <fab>
    jbom gerbers <project> --fabricator <fab>

in sequence. It delegates generation, file writing, gerber packaging, and
backup archive creation to
:class:`~jbom.application.fabrication_orchestration.FabricationWorkflow`.

Field customisation is intentionally not supported here: ``--fabricator``
selects the profile and its configured default fields are used for both BOM
and POS. Users who need per-field control should run ``jbom bom`` and
``jbom pos`` individually, or define a custom fabricator config."""

from __future__ import annotations

import sys

from jbom.application.fabrication_orchestration import (
    FabricationRequest,
    FabricationWorkflow,
)
from jbom.application.jobs.contracts import (
    JobContext,
    JobDiagnosticSeverity,
    JobOutcome,
    JobRequest,
)
from jbom.application.jobs.runner import JobEventStream, JobRunPayload, JobRunner
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
            "Parent directory for the generated production/ folder. "
            "Default: project directory."
        ),
    )

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

    # Designators opt-in
    parser.add_argument(
        "--designators",
        action="store_true",
        default=False,
        help=(
            "Generate designators.csv listing all PCB reference designators "
            "(REF:COUNT format).  Default is set by the fabricator config "
            "(generic: off)."
        ),
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
        "--debug",
        action="store_true",
        help="Keep the intermediate gerber directory after packaging",
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


def _resolve_generate_designators(args) -> bool:  # type: ignore[type-arg]
    """Return effective generate_designators flag: CLI arg or fabricator config default."""
    if bool(getattr(args, "designators", False)):
        return True
    # Fall back to fabricator config default
    try:
        from jbom.config.fabricators import load_fabricator

        fab_config = load_fabricator(resolve_fabricator_from_args(args))
        return fab_config.generate_designators
    except Exception:
        return False


def _execute_fab_command(args) -> int:  # type: ignore[type-arg]
    """Build FabricationRequest, run FabricationWorkflow, and report outputs."""
    try:
        request = FabricationRequest(
            input_path=str(args.input or "."),
            fabricator=resolve_fabricator_from_args(args),
            production_root=str(args.output_dir or ""),
            skip_bom=bool(args.skip_bom),
            skip_pos=bool(args.skip_pos),
            skip_gerbers=bool(args.skip_gerbers),
            verbose=bool(args.verbose),
            dry_run=bool(args.dry_run),
            inventory_files=tuple(str(p) for p in (args.inventory_files or [])),
            smd_only=bool(args.smd_only),
            pos_layer=str(args.layer or ""),
            pos_origin=str(args.origin or "board"),
            debug=bool(args.debug),
            generate_designators=_resolve_generate_designators(args),
        )

        result = FabricationWorkflow().run(request)
        for d in result.diagnostics:
            if d.severity == "info" and not bool(getattr(args, "verbose", False)):
                continue
            print(d.message, file=sys.stderr)
        if result.production_dir is not None:
            print(f"Production directory: {result.production_dir}")
        if result.backup_archive is not None:
            print(f"Backup archive: {result.backup_archive}")
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
