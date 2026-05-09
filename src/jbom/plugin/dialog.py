"""jBOM Fabrication stub dialog (Session A POC).

This module is imported only inside KiCad's embedded Python interpreter, so
top-level ``import wx`` is safe here — KiCad bundles wxPython.

Session A acceptance criteria
------------------------------
- Dialog appears when the toolbar button is clicked.
- Displays the current jBOM version.
- Displays the PCB file path received from ``pcbnew.GetBoard()``.
- Has a *Cancel* button that dismisses the dialog cleanly.
- Does not crash on macOS with KiCad's bundled Python.

Session B will replace this stub with the full storyboard dialog defined in
``docs/dev/development_notes/active/plugin_ux_storyboard.md``, including
the fabricator dropdown, inventory picker, checkboxes, and per-step progress
view.
"""

from __future__ import annotations

import wx

try:
    from jbom import __version__ as _jbom_version
except ImportError:  # pragma: no cover — defensive; should always be importable
    _jbom_version = "unknown"


class JBOMStubDialog(wx.Dialog):
    """Minimal stub dialog that validates plugin load and user interaction.

    Args:
        parent: Parent window (the KiCad main frame, or ``None``).
        pcb_path: Filesystem path of the active PCB file, or empty string.
    """

    def __init__(self, parent: wx.Window | None, *, pcb_path: str = "") -> None:
        super().__init__(
            parent,
            title="jBOM Fabrication",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        root = wx.BoxSizer(wx.VERTICAL)

        # ------------------------------------------------------------------
        # Version banner
        # ------------------------------------------------------------------
        banner = wx.StaticText(self, label=f"jBOM  v{_jbom_version}")
        font = banner.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        banner.SetFont(font)
        root.Add(banner, flag=wx.ALL, border=12)

        # ------------------------------------------------------------------
        # PCB path (informational)
        # ------------------------------------------------------------------
        pcb_text = pcb_path if pcb_path else "(no board loaded)"
        pcb_label = wx.StaticText(self, label=f"PCB: {pcb_text}")
        root.Add(pcb_label, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        root.Add(
            wx.StaticLine(self),
            flag=wx.EXPAND | wx.LEFT | wx.RIGHT,
            border=8,
        )

        # ------------------------------------------------------------------
        # Placeholder notice
        # ------------------------------------------------------------------
        notice = wx.StaticText(
            self,
            label=(
                "Full fabrication dialog — fabricator selection,\n"
                "inventory picker, zone fill, and Gerber generation —\n"
                "will be available in the next release (Session B)."
            ),
        )
        root.Add(notice, flag=wx.ALL, border=12)

        # ------------------------------------------------------------------
        # Button row
        # ------------------------------------------------------------------
        btn_sizer = wx.StdDialogButtonSizer()
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetDefault()
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, flag=wx.ALIGN_RIGHT | wx.ALL, border=8)

        self.SetSizer(root)
        root.Fit(self)
        self.Centre()
