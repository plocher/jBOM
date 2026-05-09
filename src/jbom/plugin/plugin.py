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
        board = pcbnew.GetBoard()
        pcb_path: str = board.GetFileName() if board else ""

        # Resolve the archive name from project title block.
        archive_name = self._resolve_archive_name(pcb_path)

        import wx  # noqa: PLC0415

        from .dialog import JBOMFabricationDialog

        # Attach to the KiCad main window if discoverable; otherwise free.
        parent = wx.FindWindowByName("PcbFrame") or None
        dlg = JBOMFabricationDialog(
            parent, pcb_path=pcb_path, archive_name=archive_name
        )
        dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def _resolve_archive_name(pcb_path: str) -> str:
        """Derive a display archive name from the project title block.

        Returns a string like ``"MyProject_1.0"`` if metadata is available,
        or ``"(unknown)"`` when the PCB path is empty or project files are absent.
        """
        if not pcb_path:
            return "(unknown)"
        try:
            from pathlib import Path

            from jbom.services.project_metadata import (
                create_metadata,
                normalize_archive_stem,
            )

            pcb_file = Path(pcb_path)
            project_dir = pcb_file.parent
            project_file = project_dir / f"{project_dir.name}.kicad_pro"
            metadata = create_metadata(project_file, pcb_file=pcb_file)
            stem = normalize_archive_stem(metadata.project_name)
            if metadata.revision:
                return f"{stem}_{metadata.revision}"
            return stem
        except Exception:
            return "(unknown)"
