"""Shared PCB-as-row-set plumbing for adapter-neutral workflows.

This module centralizes the resolve-PCB-input / load-board / collect-project-
graph sequence that BOM and POS each used to open-code.  Both workflows
should call these helpers so:

* their diagnostic text stays identical (`Note: <artifact> requires a PCB
  file. Found <suffix> file, trying to find matching PCB.` and friends);
* PCB reading goes through one path (``DefaultKiCadReaderService``);
* hierarchical-schematic enumeration uses one filter (existing
  ``.kicad_sch`` files only);
* the canonical project graph used by ``ComponentMergeService`` (and any
  future per-reference ``FieldContext`` builder) is produced once.

Per-artifact contract:

* ``parts`` -> schematic-driven (does not use this module).
* ``bom``, ``pos``, ``cpl``, ``gerbers`` -> PCB-driven; ``board.footprints``
  is the canonical row set; the schematic is loaded only for enrichment.
* ``inventory`` -> either source, by user input.

Schematic-only references (symbols without PCB footprints) are invisible
by design and intentionally not surfaced as warnings here; ERC/DRC is the
right tool for catching them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from jbom.common.options import GeneratorOptions
from jbom.common.pcb_types import BoardModel
from jbom.common.types import Diagnostic
from jbom.services.pcb_reader import DefaultKiCadReaderService
from jbom.services.project_component_collector import (
    ProjectComponentCollector,
    ProjectComponentGraph,
)
from jbom.services.project_context import ProjectContext
from jbom.services.project_file_resolver import (
    ProjectFileResolver,
    ResolvedInput,
)
from jbom.services.schematic_reader import SchematicReader


@dataclass(frozen=True)
class ResolvedPcbProject:
    """Result of resolving a user input path to a PCB project.

    Bundles the resolver's ``ResolvedInput``, the canonical ``.kicad_pcb``
    path, and any informational diagnostics emitted during resolution
    (typically the ``Note: <artifact> requires a PCB file\u2026 / found
    matching PCB\u2026 / Using PCB\u2026`` trio when the user input pointed at
    something other than a PCB).
    """

    resolved_input: ResolvedInput
    pcb_path: Path
    project_context: ProjectContext
    diagnostics: tuple[Diagnostic, ...] = ()


def resolve_pcb_input(
    input_path: str,
    *,
    artifact_name: str = "BOM",
    options: GeneratorOptions | None = None,
) -> ResolvedPcbProject:
    """Resolve *input_path* to a PCB project, emitting consistent diagnostics.

    Args:
        input_path: Whatever the user passed -- a project directory, a base
            name, a ``.kicad_pcb`` path, a ``.kicad_sch`` path, or a
            ``.kicad_pro`` path.
        artifact_name: Short name of the calling artifact (``"BOM"``,
            ``"POS"``, ``"Gerber"``) used in the user-visible diagnostic
            text.  Wording is identical across artifacts modulo this label.
        options: Optional ``GeneratorOptions`` passed through to the
            resolver for verbose-mode formatting.

    Returns:
        ``ResolvedPcbProject`` carrying the resolved input, the PCB path,
        the discovered project context, and any ``info`` diagnostics.

    Raises:
        ValueError: When the resolver cannot establish a project context
            (e.g. the user pointed at a stray file with no sibling
            ``.kicad_pro``).
    """

    diagnostics: list[Diagnostic] = []
    resolver = ProjectFileResolver(
        prefer_pcb=True,
        target_file_type="pcb",
        options=options or GeneratorOptions(),
    )
    resolved = resolver.resolve_input(input_path)

    if not resolved.is_pcb:
        diagnostics.append(
            Diagnostic(
                "info",
                f"Note: {artifact_name} generation requires a PCB file. "
                f"Found {resolved.resolved_path.suffix} file, "
                "trying to find matching PCB.",
            )
        )
        resolved = resolver.resolve_for_wrong_file_type(resolved, "pcb")
        diagnostics.append(
            Diagnostic(
                "info",
                f"found matching PCB {resolved.resolved_path.name}",
            )
        )
        diagnostics.append(
            Diagnostic(
                "info",
                f"Using PCB: {resolved.resolved_path.name}",
            )
        )

    if resolved.project_context is None:
        raise ValueError("No project context available")

    return ResolvedPcbProject(
        resolved_input=resolved,
        pcb_path=resolved.resolved_path,
        project_context=resolved.project_context,
        diagnostics=tuple(diagnostics),
    )


def load_board(pcb_path: Path) -> BoardModel:
    """Read a KiCad PCB file into a :class:`BoardModel`.

    Thin wrapper around ``DefaultKiCadReaderService().read_pcb_file(...)``
    so call sites do not need to repeat the reader instantiation.
    """

    return DefaultKiCadReaderService().read_pcb_file(pcb_path)


def list_hierarchical_schematic_files(
    project_context: ProjectContext,
) -> list[Path]:
    """Return existing ``.kicad_sch`` files for *project_context*.

    Best-effort: returns ``[]`` when the project context cannot enumerate
    hierarchical files (the schematic is optional for PCB-driven flows).
    """

    try:
        candidates = list(project_context.get_hierarchical_schematic_files())
    except Exception:
        return []
    return [
        file_path
        for file_path in candidates
        if file_path.suffix.lower() == ".kicad_sch" and file_path.exists()
    ]


def load_schematic_components(
    schematic_files: Sequence[Path],
    *,
    options: GeneratorOptions | None = None,
    verbose: bool = False,
) -> tuple[list[Any], tuple[Diagnostic, ...]]:
    """Load components from every schematic file, accumulating warnings.

    The schematic is enrichment data for PCB-driven artifacts.  Failure to
    load any single schematic is non-fatal; verbose mode surfaces a warning
    diagnostic per failed file.  Returns an empty list when
    *schematic_files* is empty.
    """

    if not schematic_files:
        return [], tuple()

    reader = SchematicReader(options)
    diagnostics: list[Diagnostic] = []
    components: list[Any] = []
    for schematic_file in schematic_files:
        try:
            components.extend(reader.load_components(schematic_file))
        except Exception as exc:
            if verbose:
                diagnostics.append(
                    Diagnostic(
                        "warning",
                        "Warning: skipping schematic source for merge enrichment "
                        f"({schematic_file}): {exc}",
                    )
                )
    return components, tuple(diagnostics)


def collect_project_graph(
    *,
    board: BoardModel,
    schematic_components: Sequence[Any],
    schematic_files: Sequence[Path],
    pcb_file: Path,
) -> ProjectComponentGraph:
    """Build the canonical reference-keyed graph for *board* + *schematic*.

    Delegates to :class:`ProjectComponentCollector`; centralizes the call
    so both BOM and POS receive identical metadata.  PCB footprints come
    from ``board.footprints`` (the canonical row set).
    """

    return ProjectComponentCollector().collect(
        schematic_components=list(schematic_components),
        pcb_components=list(board.footprints),
        schematic_files=list(schematic_files),
        pcb_file=pcb_file,
    )


__all__ = [
    "ResolvedPcbProject",
    "collect_project_graph",
    "list_hierarchical_schematic_files",
    "load_board",
    "load_schematic_components",
    "resolve_pcb_input",
]
