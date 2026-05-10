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


def _trace(label: str, board: object | None = None) -> None:  # pragma: no cover
    """Diagnostic trace — REMOVE before production."""
    modified = ""
    if board is not None:
        try:
            modified = f"  IsModified={board.IsModified()}"
        except Exception as exc:
            modified = f"  IsModified=ERR({exc})"
    print(f"[jBOM-TRACE] {label}{modified}", flush=True)


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

        # Expand the template using pcbnew's own variable expander so that
        # custom project-level variables (defined in .kicad_pro) are honoured
        # in addition to the standard title block variables.
        _trace("_run_impl() before _expand_archive_template", board)
        archive_name = self._expand_archive_template(board, template)
        _trace(f"_run_impl() after _expand_archive_template → '{archive_name}'", board)

        from .dialog import JBOMFabricationDialog

        dlg = JBOMFabricationDialog(pcb_path=pcb_path, archive_name=archive_name)
        _trace("_run_impl() before dlg.Show()", board)
        dlg.Show()
        _trace("_run_impl() after dlg.Show() (returns immediately — modeless)", board)

    @staticmethod
    def _expand_archive_template(board: object, template: str) -> str:
        """Expand the archive name template for the given board.

        Priority:
        1. ``pcbnew.ExpandTextVars(template, project)`` — resolves all KiCad
           text variables including custom project-level variables.
        2. jBOM :func:`~jbom.services.text_variable_expander.expand_text_variables`
           — fallback resolving the standard title block subset.
        3. PCB filename stem — used when both produce an empty result.
        4. ``"(unknown)"`` — last resort.
        """
        import re
        from pathlib import Path

        def _normalise(s: str) -> str:
            """Strip characters unsuitable for a filename."""
            return re.sub(r"[^\w.-]", "_", s).strip("_")

        try:
            # Attempt pcbnew.ExpandTextVars first for full variable support.
            _trace("  _expand: before GetProject", board)
            project = board.GetProject()  # type: ignore[union-attr]
            _trace("  _expand: after GetProject", board)
            expanded = pcbnew.ExpandTextVars(template, project)
            _trace("  _expand: after ExpandTextVars", board)
        except Exception:
            expanded = template

        # Fallback: apply jBOM's own expander for the title block subset.
        try:
            from jbom.common.types import TitleBlockMetadata
            from jbom.services.text_variable_expander import expand_text_variables

            _trace("  _expand: before GetTitleBlock", board)
            tb = board.GetTitleBlock()  # type: ignore[union-attr]
            _trace("  _expand: after GetTitleBlock", board)
            meta = TitleBlockMetadata(
                title=(tb.GetTitle() or "").strip(),
                revision=(tb.GetRevision() or "").strip(),
                date=(tb.GetDate() or "").strip(),
                company=(tb.GetCompany() or "").strip(),
            )
            expanded = expand_text_variables(expanded, meta)
        except Exception:
            pass

        cleaned = _normalise(expanded)
        if cleaned:
            return cleaned

        # Final fallback: PCB filename stem.
        try:
            pcb_path: str = board.GetFileName()  # type: ignore[union-attr]
            if pcb_path:
                stem = _normalise(Path(pcb_path).stem)
                if stem:
                    return stem
        except Exception:
            pass

        return "(unknown)"
