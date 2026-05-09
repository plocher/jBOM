"""jBOM Fabrication dialog (Session B — full storyboard implementation).

This module is imported only inside KiCad's embedded Python interpreter, so
top-level ``import wx`` is safe here — KiCad bundles wxPython.

Dialog has two panels that swap on Generate:

1. **Input panel** — fabricator dropdown, inventory file picker, option
   checkboxes (SMD only, Exclude DNP, Fill zones, Create backup, Open folder,
   Apply corrections [grayed/pending #249], Debug mode).  A Generate button
   and a Cancel button sit at the bottom.

2. **Progress panel** — four :class:`wx.Gauge` widgets for BOM, CPL, Gerbers,
   and Backup, driven by step callbacks via :func:`wx.CallAfter` from the
   background thread.

Completion behaviour:

- **Success, debug=False** — dialog closes automatically; Finder/Explorer
  opens on the production folder.
- **Success, debug=True** — dialog stays open showing diagnostics.
- **Error** — dialog stays open showing error message.

Options are loaded from :func:`~jbom.plugin.options.load_options` when the
dialog opens and persisted by :func:`~jbom.plugin.options.save_options` when
Generate is pressed.

Orchestration (Blocker 1 + 3 from issue #227):
The background ``_worker`` directly sequences:

1. ``BOMWorkflow().run()`` → ``BOMWriter`` → ``production/jbom.csv``
2. ``POSWorkflow().run()`` → ``POSWriter`` → ``production/cpl.csv``
3. ``PcbnewGerberGenerator(board).generate()`` → ``GerberPackager``
   → ``production/{stem}.zip``
4. ``BackupService().backup()``
   → ``production/backups/{stem}_{timestamp}.zip``

``FabricationWorkflow`` is intentionally **not** used from the plugin: its
internal ``kicad-cli`` subprocess path hangs inside KiCad, and its backup
runs before plugin-generated Gerbers are available.  Plugin knowledge stays
in the plugin layer.  The CLI path (``GerberExporter`` / ``kicad-cli``)
is unchanged.

wx.Dialog + Show() (Blocker 2 from issue #227):
``ShowModal()`` blocks ``Run()`` and KiCad does not re-enable the toolbar
button after it returns.  Using ``wx.Dialog.Show()`` (modeless) returns
immediately: ``Run()`` returns, KiCad re-enables the button, and the dialog
owns its lifecycle until ``self.Destroy()`` is called.  Parent is explicitly
``None`` — KiCad's C++ dialog tracking triggers the toolbar re-enable when
the ``wxDialog`` C++ object is destroyed, regardless of Python parent.

Reference: ``docs/dev/development_notes/active/plugin_ux_storyboard.md``
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import types
from pathlib import Path

import wx

try:
    from jbom import __version__ as _jbom_version
except ImportError:  # pragma: no cover
    _jbom_version = "unknown"

# Steps in display order — matches storyboard progress panel.
_STEPS: list[str] = ["bom", "pos", "gerbers", "backup"]
_STEP_LABELS: dict[str, str] = {
    "bom": "BOM",
    "pos": "CPL",
    "gerbers": "Gerbers",
    "backup": "Backup",
}


class JBOMFabricationDialog(wx.Dialog):
    """Full storyboard fabrication dialog (Session B).

    Uses ``wx.Dialog`` with ``Show()`` (modeless) so that ``plugin.Run()``
    returns immediately and the KiCad toolbar button can be re-activated
    (Blocker 2, issue #227).  Parent is always ``None``: KiCad's dialog
    tracking re-enables the toolbar button when the underlying ``wxDialog``
    C++ object is destroyed, and a ``None`` parent avoids any window-hierarchy
    interference from the KiCad main frame.

    Args:
        pcb_path: Filesystem path of the active PCB file, or empty string.
        archive_name: Human-readable archive stem from the project title block
            (e.g. ``"MyProject_1.0"``).  Shown as a read-only label.
    """

    def __init__(
        self,
        *,
        pcb_path: str = "",
        archive_name: str = "",
    ) -> None:
        super().__init__(
            None,  # parent=None — required for correct KiCad toolbar re-enable
            title="jBOM Fabrication",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self._pcb_path = pcb_path
        self._archive_name = archive_name or "(unknown)"
        self._cancel_requested = threading.Event()
        self._fab_ids: list[str] = []
        self._gauges: dict[str, wx.Gauge] = {}
        self._status_texts: dict[str, wx.StaticText] = {}
        # _archive_preview is set by _build_input_panel; updated when template changes
        self._archive_preview: wx.StaticText | None = None

        # Load persisted options; fall back to defaults when absent.
        from jbom.plugin.options import PluginOptions, load_options

        self._options: PluginOptions = (
            load_options(Path(pcb_path)) if pcb_path else PluginOptions()
        )

        # Build UI
        outer = wx.BoxSizer(wx.VERTICAL)
        self._input_panel = self._build_input_panel()
        self._progress_panel = self._build_progress_panel()
        self._progress_panel.Hide()

        outer.Add(self._input_panel, flag=wx.EXPAND)
        outer.Add(self._progress_panel, flag=wx.EXPAND)

        self.SetSizer(outer)
        outer.Fit(self)
        self.Centre()

        # EVT_CLOSE fires when the user clicks the X button.  The default
        # wx.Dialog behaviour is Show(False) (hide); we override it to Destroy.
        self.Bind(wx.EVT_CLOSE, self._on_close)

    # ------------------------------------------------------------------
    # Input panel
    # ------------------------------------------------------------------

    def _build_input_panel(self) -> wx.Panel:
        """Build and return the input-form panel."""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # -- Header -------------------------------------------------------
        header = wx.StaticText(panel, label=f"jBOM  v{_jbom_version}  —  Fabrication")
        font = header.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        header.SetFont(font)
        sizer.Add(header, flag=wx.ALL, border=10)
        sizer.Add(wx.StaticLine(panel), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=8)

        # -- Project info grid -------------------------------------------
        grid = wx.FlexGridSizer(rows=4, cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1, 1)

        # Archive template (editable) + preview label
        grid.Add(
            wx.StaticText(panel, label="Archive:"),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        self._archive_tpl = wx.TextCtrl(
            panel,
            value=self._options.archive_name_template,
            style=wx.TE_PROCESS_ENTER,
        )
        self._archive_tpl.Bind(wx.EVT_TEXT, self._on_archive_template_changed)
        grid.Add(self._archive_tpl, flag=wx.EXPAND)

        # Preview row — blank label + expanded-name label
        grid.Add(wx.StaticText(panel, label=""), flag=wx.ALIGN_CENTER_VERTICAL)
        self._archive_preview = wx.StaticText(
            panel, label=self._archive_name, style=wx.ST_ELLIPSIZE_END
        )
        preview_font = self._archive_preview.GetFont()
        preview_font.SetStyle(wx.FONTSTYLE_ITALIC)
        self._archive_preview.SetFont(preview_font)
        grid.Add(self._archive_preview, flag=wx.EXPAND)

        # Fabricator dropdown + Config button
        grid.Add(
            wx.StaticText(panel, label="Fabricator:"),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        fab_row = wx.BoxSizer(wx.HORIZONTAL)
        self._fab_ids, labels = self._load_fabricator_choices()
        self._fab_choice = wx.Choice(panel, choices=labels)
        self._fab_choice.SetSelection(self._fab_index_for(self._options.fabricator))
        fab_row.Add(self._fab_choice, proportion=1, flag=wx.EXPAND)
        config_btn = wx.Button(panel, label="Config\u2026", size=(60, -1))
        config_btn.Disable()  # placeholder — full viewer in a future release
        fab_row.Add(config_btn, flag=wx.LEFT, border=4)
        grid.Add(fab_row, flag=wx.EXPAND)

        # Inventory file picker
        grid.Add(
            wx.StaticText(panel, label="Inventory:"),
            flag=wx.ALIGN_CENTER_VERTICAL,
        )
        inv_row = wx.BoxSizer(wx.HORIZONTAL)
        self._inv_text = wx.TextCtrl(
            panel,
            value=self._options.inventory_path,
            style=wx.TE_PROCESS_ENTER,
        )
        browse_btn = wx.Button(panel, label="Browse\u2026", size=(70, -1))
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse_inventory)
        inv_row.Add(self._inv_text, proportion=1, flag=wx.EXPAND)
        inv_row.Add(browse_btn, flag=wx.LEFT, border=4)
        grid.Add(inv_row, flag=wx.EXPAND)

        sizer.Add(grid, flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(wx.StaticLine(panel), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=8)

        # -- Checkboxes --------------------------------------------------
        check_sizer = wx.BoxSizer(wx.VERTICAL)

        def _cb(label: str, checked: bool = True) -> wx.CheckBox:
            cb = wx.CheckBox(panel, label=label)
            cb.SetValue(checked)
            return cb

        self._cb_smd_only = _cb("SMD only (placement)", False)
        self._cb_exclude_dnp = _cb("Exclude DNP components")
        self._cb_fill_zones = _cb("Fill all zones before Gerbers")
        self._cb_backup = _cb("Create backup archive")
        self._cb_open_folder = _cb("Open production folder when done")

        # Grayed placeholder — pending issue #249
        cb_corrections = _cb("Apply placement corrections  (pending #249)", False)
        cb_corrections.Disable()

        self._cb_debug = _cb("Keep intermediate files (debug)", False)

        for cb in (
            self._cb_smd_only,
            self._cb_exclude_dnp,
            self._cb_fill_zones,
            self._cb_backup,
            self._cb_open_folder,
            cb_corrections,
            self._cb_debug,
        ):
            check_sizer.Add(cb, flag=wx.LEFT | wx.BOTTOM, border=4)

        sizer.Add(check_sizer, flag=wx.ALL, border=10)
        sizer.Add(wx.StaticLine(panel), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=8)

        # -- Buttons ------------------------------------------------------
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._generate_btn = wx.Button(panel, label="Generate")
        self._generate_btn.SetDefault()
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        # wx.Dialog.Show() (modeless) does not auto-handle wx.ID_CANCEL — bind explicitly.
        cancel_btn.Bind(wx.EVT_BUTTON, lambda _e: self._refresh_and_destroy())
        self._generate_btn.Bind(wx.EVT_BUTTON, self._on_generate)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._generate_btn, flag=wx.RIGHT, border=8)
        btn_row.Add(cancel_btn)
        sizer.Add(btn_row, flag=wx.ALL | wx.EXPAND, border=10)

        panel.SetSizer(sizer)
        return panel

    # ------------------------------------------------------------------
    # Progress panel
    # ------------------------------------------------------------------

    def _build_progress_panel(self) -> wx.Panel:
        """Build and return the progress panel (shown during generation)."""
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="jBOM Fabrication \u2014 Generating\u2026")
        font = title.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        sizer.Add(title, flag=wx.ALL, border=10)
        sizer.Add(wx.StaticLine(panel), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=8)

        gauge_grid = wx.FlexGridSizer(rows=len(_STEPS), cols=3, vgap=6, hgap=8)
        gauge_grid.AddGrowableCol(1, 1)

        for step in _STEPS:
            label = wx.StaticText(panel, label=_STEP_LABELS[step])
            gauge = wx.Gauge(panel, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
            status = wx.StaticText(panel, label="")
            self._gauges[step] = gauge
            self._status_texts[step] = status
            gauge_grid.Add(label, flag=wx.ALIGN_CENTER_VERTICAL)
            gauge_grid.Add(gauge, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
            gauge_grid.Add(status, flag=wx.ALIGN_CENTER_VERTICAL | wx.LEFT, border=4)

        sizer.Add(gauge_grid, flag=wx.ALL | wx.EXPAND, border=10)
        sizer.Add(wx.StaticLine(panel), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=8)

        # Diagnostics area (shown on error)
        self._diag_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE,
        )
        self._diag_text.SetMinSize((-1, 60))
        self._diag_text.Hide()
        sizer.Add(self._diag_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)

        self._progress_cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        self._progress_cancel_btn.Bind(wx.EVT_BUTTON, self._on_progress_cancel)
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self._progress_cancel_btn)
        sizer.Add(btn_row, flag=wx.ALL | wx.EXPAND, border=10)

        panel.SetSizer(sizer)
        return panel

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_fabricator_choices(self) -> tuple[list[str], list[str]]:
        """Return (ids, display_labels) for the fabricator dropdown."""
        try:
            from jbom.config.fabricators import get_fabricators_with_names

            pairs = get_fabricators_with_names()
        except Exception as _exc:  # pragma: no cover
            # Surface the error in the archive label so it is visible in KiCad.
            self._archive_name = f"(config error: {_exc})"
            pairs = [("generic", "Generic")]
        ids = [fid for fid, _ in pairs]
        labels = [name for _, name in pairs]
        return ids, labels

    def _fab_index_for(self, fid: str) -> int:
        """Return the dropdown index for *fid*, defaulting to 0."""
        try:
            return self._fab_ids.index(fid)
        except ValueError:
            return 0

    def _selected_fabricator_id(self) -> str:
        """Return the currently selected fabricator ID."""
        idx = self._fab_choice.GetSelection()
        if 0 <= idx < len(self._fab_ids):
            return self._fab_ids[idx]
        return "generic"

    # ------------------------------------------------------------------
    # Event handlers — input panel
    # ------------------------------------------------------------------

    def _on_archive_template_changed(self, _evt: wx.CommandEvent) -> None:
        """Re-expand the template and update the preview + archive_name.

        Called on every keystroke in the Archive text field.  Updates
        ``self._archive_name`` so that Generate uses the new expansion.
        Uses the same two-step expansion as plugin.py._expand_archive_template:
        1. pcbnew.ExpandTextVars for project-level variables
        2. jBOM TextVariableExpander for standard title block variables
        """
        if self._archive_preview is None:
            return
        new_template = self._archive_tpl.GetValue()
        try:
            import re

            import pcbnew  # noqa: PLC0415 — safe inside KiCad

            board = pcbnew.GetBoard()

            # Step 1: pcbnew.ExpandTextVars handles custom project vars.
            try:
                project = board.GetProject()
                expanded = pcbnew.ExpandTextVars(new_template, project)
            except Exception:
                expanded = new_template

            # Step 2: jBOM expander handles standard title block vars
            # (${TITLE}, ${REVISION}, ${DATE}, ${COMPANY}, ${CURRENT_DATE}).
            try:
                from jbom.common.types import TitleBlockMetadata
                from jbom.services.text_variable_expander import expand_text_variables

                tb = board.GetTitleBlock()
                meta = TitleBlockMetadata(
                    title=(tb.GetTitle() or "").strip(),
                    revision=(tb.GetRevision() or "").strip(),
                    date=(tb.GetDate() or "").strip(),
                    company=(tb.GetCompany() or "").strip(),
                )
                expanded = expand_text_variables(expanded, meta)
            except Exception:
                pass

            cleaned = re.sub(r"[^\w.-]", "_", expanded).strip("_")
            self._archive_name = cleaned or new_template
        except Exception:
            self._archive_name = new_template
        self._archive_preview.SetLabel(self._archive_name)

    def _on_browse_inventory(self, _evt: wx.CommandEvent) -> None:
        """Open a file dialog to select the inventory file."""
        dlg = wx.FileDialog(
            self,
            message="Select inventory file",
            wildcard="Inventory files (*.csv;*.xlsx;*.numbers)|*.csv;*.xlsx;*.numbers|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self._inv_text.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_generate(self, _evt: wx.CommandEvent) -> None:
        """Validate, save options, fill zones if requested, then start the thread."""
        # Capture all UI values on the main thread before the worker starts.
        fab_id = self._selected_fabricator_id()
        inventory_path = self._inv_text.GetValue().strip()
        smd_only = self._cb_smd_only.GetValue()
        open_folder = self._cb_open_folder.GetValue()
        debug_mode = self._cb_debug.GetValue()
        archive_stem = self._archive_name
        pcb_path = self._pcb_path

        # Persist selections
        from jbom.plugin.options import PluginOptions, save_options

        archive_template = self._archive_tpl.GetValue().strip()
        updated = PluginOptions(
            fabricator=fab_id,
            inventory_path=inventory_path,
            archive_name_template=archive_template,
        )
        if pcb_path:
            try:
                save_options(updated, Path(pcb_path))
            except OSError:
                pass  # Non-fatal; proceed with generation

        # Optional zone fill (in-memory, updates live KiCad view)
        if self._cb_fill_zones.GetValue():
            self._fill_zones()

        # Swap to progress panel
        self._cancel_requested.clear()
        self._input_panel.Hide()
        self._progress_panel.Show()
        self.GetSizer().Layout()
        self.GetSizer().Fit(self)
        self.Centre()

        def _step(step: str, status: str) -> None:
            wx.CallAfter(self._on_step, step, status)

        def _worker() -> None:
            """Background thread: BOM → POS → Gerbers → Backup (A2 orchestration)."""
            try:
                import pcbnew  # noqa: PLC0415

                board = pcbnew.GetBoard()

                project_dir = Path(pcb_path).parent if pcb_path else Path(".")
                production_dir = project_dir / "production"
                production_dir.mkdir(parents=True, exist_ok=True)

                diagnostics: list[str] = []
                artifact_paths: list[Path] = []

                def cancelled() -> bool:
                    return self._cancel_requested.is_set()

                # ----------------------------------------------------------
                # Step 1: BOM
                # ----------------------------------------------------------
                _step("bom", "start")
                if not cancelled():
                    try:
                        from jbom.application.bom_workflow import (
                            BOMRequest,
                            BOMWorkflow,
                        )
                        from jbom.services.bom_writer import BOMWriter

                        bom_request = BOMRequest(
                            input_path=pcb_path or ".",
                            fabricator=fab_id,
                            inventory_files=(
                                (inventory_path,) if inventory_path else ()
                            ),
                        )
                        bom_result = BOMWorkflow().run(bom_request)
                        diagnostics.extend(bom_result.diagnostics)
                        if bom_result.generation is not None:
                            bom_path = production_dir / "jbom.csv"
                            BOMWriter.write(bom_result.generation, bom_path, force=True)
                            artifact_paths.append(bom_path)
                    except Exception as exc:
                        diagnostics.append(f"BOM generation failed: {exc}")
                _step("bom", "done")

                # ----------------------------------------------------------
                # Step 2: POS
                # ----------------------------------------------------------
                _step("pos", "start")
                if not cancelled():
                    try:
                        from jbom.application.pos_workflow import (
                            POSRequest,
                            POSWorkflow,
                        )
                        from jbom.services.pos_writer import POSWriter

                        pos_request = POSRequest(
                            input_path=pcb_path or ".",
                            fabricator=fab_id,
                            smd_only=smd_only,
                        )
                        pos_result = POSWorkflow().run(pos_request)
                        diagnostics.extend(pos_result.diagnostics)
                        if pos_result.generation is not None:
                            pos_path = production_dir / "cpl.csv"
                            POSWriter.write(pos_result.generation, pos_path, force=True)
                            artifact_paths.append(pos_path)
                    except Exception as exc:
                        diagnostics.append(f"POS generation failed: {exc}")
                _step("pos", "done")

                # ----------------------------------------------------------
                # Step 3: Gerbers (pcbnew PLOT_CONTROLLER — no kicad-cli)
                # ----------------------------------------------------------
                _step("gerbers", "start")
                if not cancelled():
                    try:
                        from jbom.plugin.gerber_generator import (
                            PcbnewGerberGenerator,
                        )
                        from jbom.services.gerber_packager import GerberPackager

                        with tempfile.TemporaryDirectory() as tmp:
                            temp_gerber_dir = Path(tmp) / "gerbers"
                            temp_gerber_dir.mkdir()
                            gerber_result = PcbnewGerberGenerator(board).generate(
                                temp_gerber_dir,
                                fabricator=fab_id,
                                debug=debug_mode,
                            )
                            diagnostics.extend(gerber_result.diagnostics)
                            if not gerber_result.skipped:
                                gerber_zip = production_dir / f"{archive_stem}.zip"
                                GerberPackager().package(
                                    gerber_result.artifacts,
                                    gerber_zip,
                                    debug=debug_mode,
                                )
                                artifact_paths.append(gerber_zip)
                    except Exception as exc:
                        diagnostics.append(f"Gerber generation failed: {exc}")
                _step("gerbers", "done")

                # ----------------------------------------------------------
                # Step 4: Backup (all three artifacts in one archive)
                # ----------------------------------------------------------
                _step("backup", "start")
                if not cancelled() and artifact_paths:
                    try:
                        from jbom.services.backup_service import BackupService

                        backup_dir = production_dir / "backups"
                        BackupService().backup(
                            artifact_paths,
                            backup_dir,
                            archive_stem,
                        )
                    except Exception as exc:
                        diagnostics.append(f"Backup creation failed: {exc}")
                _step("backup", "done")

                # Build a lightweight result carrier for _on_complete.
                result = types.SimpleNamespace(
                    production_dir=(production_dir if artifact_paths else None),
                    diagnostics=tuple(diagnostics),
                )
                wx.CallAfter(self._on_complete, result, open_folder, debug_mode)

            except Exception as exc:
                wx.CallAfter(self._on_error, str(exc))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _fill_zones(self) -> None:
        """Fill board zones using the pcbnew API (in-memory only).

        Note: pcbnew.Refresh() is intentionally omitted here.  Calling it
        marks the board as modified in KiCad's undo history, which would
        prompt the user to save even if they only invoked the plugin and
        cancelled.  The zone fill is reflected in the exported Gerbers;
        the live editor view updates automatically when the board reloads.
        """
        try:
            import pcbnew  # noqa: PLC0415

            board = pcbnew.GetBoard()
            if board:
                filler = pcbnew.ZONE_FILLER(board)
                filler.Fill(board.Zones())
                # Do NOT call pcbnew.Refresh() — it sets the board's
                # modified flag and causes an unsaved-changes prompt.
        except Exception:  # pragma: no cover
            pass  # Non-fatal; proceed with generation

    # ------------------------------------------------------------------
    # Event handlers — progress panel
    # ------------------------------------------------------------------

    def _on_progress_cancel(self, _evt: wx.CommandEvent) -> None:
        """Signal the background thread to stop after the current step."""
        self._cancel_requested.set()
        self._progress_cancel_btn.Disable()

    def _on_step(self, step: str, status: str) -> None:
        """Update the gauge for *step*; called via ``wx.CallAfter`` from thread."""
        if step not in self._gauges:
            return
        gauge = self._gauges[step]
        text = self._status_texts[step]
        if status == "start":
            gauge.SetValue(50)
            text.SetLabel("\u2026")
        elif status == "done":
            gauge.SetValue(100)
            text.SetLabel("\u2713")
        self._progress_panel.Layout()

    def _on_complete(
        self,
        result: object,
        open_folder: bool,
        debug_mode: bool,
    ) -> None:
        """Handle workflow completion; called via ``wx.CallAfter``."""
        # Fill any remaining gauges to 100
        for gauge in self._gauges.values():
            if gauge.GetValue() < 100:
                gauge.SetValue(100)

        diagnostics = getattr(result, "diagnostics", ())
        production_dir = getattr(result, "production_dir", None)

        # Distinguish errors (no artifacts produced — production_dir is None)
        # from info-level diagnostics.  Stay open when there was an actual
        # failure or when the user requested debug mode.
        has_error = production_dir is None
        stay_open = debug_mode or has_error

        if stay_open:
            # Show diagnostics and switch Cancel → Close.
            if diagnostics:
                self._diag_text.SetValue("\n".join(str(d) for d in diagnostics))
                self._diag_text.Show()
                self.GetSizer().Layout()
                self.GetSizer().Fit(self)
            # Rebind the button so it closes + optionally opens the folder
            # (open_folder applies in debug mode too — user wants to inspect).
            self._progress_cancel_btn.SetLabel("Close")
            self._progress_cancel_btn.Unbind(wx.EVT_BUTTON)

            def _close_and_open(_e: wx.CommandEvent) -> None:
                if open_folder and production_dir is not None:
                    self._open_folder(Path(production_dir))
                self._refresh_and_destroy()

            self._progress_cancel_btn.Bind(wx.EVT_BUTTON, _close_and_open)
            self._progress_cancel_btn.Enable()
        else:
            # Auto-close + open folder
            if open_folder and production_dir is not None:
                self._open_folder(Path(production_dir))
            self._refresh_and_destroy()

    def _on_error(self, message: str) -> None:
        """Handle unexpected thread exception; called via ``wx.CallAfter``."""
        self._diag_text.SetValue(f"Error: {message}")
        self._diag_text.Show()
        self._progress_cancel_btn.SetLabel("Close")
        self._progress_cancel_btn.Unbind(wx.EVT_BUTTON)
        self._progress_cancel_btn.Bind(
            wx.EVT_BUTTON, lambda _e: self._refresh_and_destroy()
        )
        self._progress_cancel_btn.Enable()
        self.GetSizer().Layout()
        self.GetSizer().Fit(self)

    def _on_close(self, evt: wx.CloseEvent) -> None:
        """Handle dialog close (X button) — signal cancel and destroy.

        Overrides wx.Dialog's default EVT_CLOSE behaviour (which hides rather
        than destroys) so that Destroy() is called unconditionally.  This
        triggers KiCad's toolbar button re-enable via the wxDialog destructor.
        """
        self._cancel_requested.set()
        self._refresh_and_destroy()

    def _refresh_and_destroy(self) -> None:
        """Call ``pcbnew.Refresh()`` then ``Destroy()`` at every final teardown.

        ``pcbnew.Refresh()`` posts an update event to KiCad's main wx event
        loop.  KiCad's toolbar ``UpdateUI`` handler re-evaluates button state
        as part of that cycle — without it, the ActionPlugin toolbar button
        may not be re-enabled after the dialog closes.

        Mirrors Fabrication-Toolkit's ``updateDisplay`` which always calls
        ``pcbnew.Refresh()`` before ``self.Destroy()``.
        """
        try:
            import pcbnew  # noqa: PLC0415

            pcbnew.Refresh()
        except Exception:  # pragma: no cover
            pass  # Non-fatal: Destroy() still runs
        self.Destroy()

    @staticmethod
    def _open_folder(path: Path) -> None:
        """Open *path* in the platform file manager."""
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])  # noqa: S603,S607
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", str(path)])  # noqa: S603,S607
            else:
                subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607
        except Exception:  # pragma: no cover
            pass  # Non-fatal
