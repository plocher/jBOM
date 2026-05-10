"""KiCad ActionPlugin subclass for jBOM Fabrication.

This module is **only** imported from ``__init__.py`` when ``pcbnew`` is
already present in ``sys.modules`` (i.e. we are running inside KiCad's
embedded Python interpreter).  Top-level ``import pcbnew`` is therefore safe
here — it will never execute in a CLI or test environment.

Session A: minimal stub that registers a toolbar button and opens a stub
dialog.  The full fabrication dialog (fabricator selection, inventory picker,
progress view) is implemented in Session B.
"""

from __future__ import annotations
import sys

import pcbnew  # noqa: F401 — only imported inside KiCad, safe here


_TRACE_LOG = "/tmp/jbom_trace.log"


def _trace(label: str, board: object | None = None) -> None:  # pragma: no cover
    """Diagnostic trace — REMOVE before production."""
    modified = ""
    if board is not None:
        try:
            modified = f"  IsModified={board.IsModified()}"
        except Exception as exc:
            modified = f"  IsModified=ERR({exc})"
    msg = f"[jBOM-TRACE] {label}{modified}"
    print(msg, flush=True)
    try:
        with open(_TRACE_LOG, "a") as _f:
            _f.write(msg + "\n")
    except Exception:
        pass


class JBOMFabricationPlugin(pcbnew.ActionPlugin):
    """KiCad ActionPlugin that surfaces jBOM fabrication from the PCB toolbar.

    KiCad calls ``defaults()`` once at plugin load time to read metadata,
    then calls ``Run()`` each time the user activates the toolbar button.
    """

    def defaults(self) -> None:
        """Register plugin metadata with KiCad's plugin manager."""
        self.name = "jBOM Fabrication"
        self.category = "Fabrication"
        self.description = (
            "Generate BOM, pick-and-place, and Gerber files for fabrication. "
            "Supports JLC, PCBWay, Seeed Studio, and generic fabricators."
        )
        self.show_toolbar_button = True
        # Toolbar icon (24×24 PNG) lives next to this file.
        # Empty string → KiCad uses a generic script icon.
        self.icon_file_name = ""

    def Run(self) -> None:  # noqa: N802 — KiCad API name
        """Open the jBOM Fabrication dialog."""
        try:
            _board = pcbnew.GetBoard()
            _trace("Run() entry", _board)
            self._run_impl()
            _trace("Run() exit (dialog shown)", _board)
        except Exception:  # pragma: no cover
            import traceback

            traceback.print_exc(file=sys.stderr)

    def _run_impl(self) -> None:
        """Implementation body of Run(); separated for exception tracing."""
        board = pcbnew.GetBoard()
        pcb_path: str = board.GetFileName() if board else ""
        _trace("_run_impl() after GetBoard/GetFileName", board)

        # Load persisted options to get the archive name template.
        from pathlib import Path

        from jbom.plugin.options import load_options

        options = load_options(Path(pcb_path)) if pcb_path else None
        template = options.archive_name_template if options else "${TITLE}_${REVISION}"
        _trace("_run_impl() after load_options", board)

        # Expand the template using FILE-BASED reads only.
        # The old _expand_archive_template(board, ...) called board.GetProject() and
        # board.GetTitleBlock() via SWIG, which KiCad 10 registers as a modification
        # and sets the board dirty flag even though no data was changed.
        # _expand_archive_template_from_file() reads the same data directly from the
        # .kicad_pcb file, bypassing the SWIG binding entirely.
        _trace("_run_impl() before _expand_archive_template_from_file", board)
        archive_name = self._expand_archive_template_from_file(pcb_path, template)
        _trace(
            f"_run_impl() after _expand_archive_template_from_file → '{archive_name}'",
            board,
        )

        from .dialog import JBOMFabricationDialog

        dlg = JBOMFabricationDialog(pcb_path=pcb_path, archive_name=archive_name)
        _trace("_run_impl() before dlg.Show()", board)
        dlg.Show()
        _trace("_run_impl() after dlg.Show() (returns immediately — modeless)", board)

    @staticmethod
    def _expand_archive_template_from_file(pcb_path: str, template: str) -> str:
        """Expand the archive name template using file-based reads only.

        Reads title block metadata from the ``.kicad_pcb`` file directly via
        jBOM's ``DefaultKiCadReaderService``, completely bypassing the pcbnew
        SWIG bindings.  This prevents ``board.GetProject()`` /
        ``board.GetTitleBlock()`` SWIG reads from setting the board's modified
        flag as a side-effect.

        Priority:
        1. jBOM :func:`~jbom.services.text_variable_expander.expand_text_variables`
           on PCB title block read from disk.
        2. PCB filename stem — when template expansion yields nothing.
        3. ``"(unknown)"`` — last resort.

        Note: Custom project-level variables (defined in ``.kicad_pro`` and
        resolved by ``pcbnew.ExpandTextVars``) are NOT supported by this path.
        Standard title block tokens (``${TITLE}``, ``${REVISION}``, ``${DATE}``,
        ``${COMPANY}``, ``${CURRENT_DATE}``) are supported.
        """
        import re
        from pathlib import Path

        def _normalise(s: str) -> str:
            """Strip characters unsuitable for a filename."""
            return re.sub(r"[^\w.-]", "_", s).strip("_")

        try:
            from jbom.services.project_metadata import create_metadata
            from jbom.services.text_variable_expander import expand_text_variables

            pcb_file = Path(pcb_path)
            # Look for the .kicad_pro in the same directory, named after the dir.
            project_file = pcb_file.parent / f"{pcb_file.parent.name}.kicad_pro"
            metadata = create_metadata(project_file, pcb_file=pcb_file)
            meta = metadata.pcb_metadata  # TitleBlockMetadata | None
            if meta is not None:
                expanded = expand_text_variables(template, meta)
                cleaned = _normalise(expanded)
                if cleaned:
                    return cleaned
        except Exception:
            pass

        # Fallback: PCB filename stem.
        try:
            if pcb_path:
                stem = _normalise(Path(pcb_path).stem)
                if stem:
                    return stem
        except Exception:
            pass

        return "(unknown)"
