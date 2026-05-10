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

import pcbnew  # noqa: F401 — only imported inside KiCad, safe here


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
            self._run_impl()
        except Exception:  # pragma: no cover
            import sys
            import traceback

            traceback.print_exc(file=sys.stderr)

    def _run_impl(self) -> None:
        """Implementation body of Run(); separated for exception tracing."""
        board = pcbnew.GetBoard()
        pcb_path: str = board.GetFileName() if board else ""

        # Load persisted options to get the archive name template.
        from pathlib import Path

        from jbom.plugin.options import load_options

        options = load_options(Path(pcb_path)) if pcb_path else None
        template = options.archive_name_template if options else "${TITLE}_${REVISION}"

        # Expand template via file-based reads only.  The old path called
        # board.GetProject() / board.GetTitleBlock() via SWIG; in KiCad 10
        # the ActionPlugin toolbar framework marks the board modified before
        # Run() is called (confirmed: FT exhibits the same behaviour) so we
        # cannot prevent the dirty flag from that direction.  We still avoid
        # adding unnecessary SWIG reads on top of it.
        archive_name = self._expand_archive_template_from_file(pcb_path, template)

        from .dialog import JBOMFabricationDialog

        dlg = JBOMFabricationDialog(pcb_path=pcb_path, archive_name=archive_name)
        dlg.Show()

    @staticmethod
    def _expand_archive_template_from_file(pcb_path: str, template: str) -> str:
        """Expand the archive name template using file-based reads only.

        Reads title block metadata directly from the ``.kicad_pcb`` file via
        jBOM's S-expression parser, bypassing pcbnew SWIG bindings entirely.
        Standard title block tokens (``${TITLE}``, ``${REVISION}``,
        ``${DATE}``, ``${COMPANY}``, ``${CURRENT_DATE}``) are supported.
        Custom ``.kicad_pro`` project variables are not (those require
        ``pcbnew.ExpandTextVars``).

        Priority:
        1. jBOM :func:`~jbom.services.text_variable_expander.expand_text_variables`
           on the title block read from disk.
        2. PCB filename stem — when template expansion yields nothing.
        3. ``"(unknown)"`` — last resort.
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
            project_file = pcb_file.parent / f"{pcb_file.parent.name}.kicad_pro"
            metadata = create_metadata(project_file, pcb_file=pcb_file)
            meta = metadata.pcb_metadata
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
