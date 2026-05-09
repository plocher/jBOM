"""PcbnewGerberGenerator — in-process Gerber generation for the KiCad plugin.

Uses ``pcbnew.PLOT_CONTROLLER`` and ``EXCELLON_WRITER`` to generate Gerber and
drill files directly from the live board object, avoiding the ``kicad-cli``
subprocess that hangs when called from inside a KiCad plugin (two KiCad
instances contend on macOS and Windows).

This module is only *called* from within KiCad's embedded Python interpreter.
``pcbnew`` is lazy-imported inside :meth:`PcbnewGerberGenerator.generate` so
that the module itself remains importable in CLI/test environments.

Ported from Fabrication-Toolkit's ``plugins/process.py``
(``ProcessManager.generate_gerber`` / ``generate_drills``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jbom.services.gerber_service import GerberResult

__all__ = ["PcbnewGerberGenerator"]

# Standard fabrication layers used when the fabricator config has no explicit
# ``gerbers.layers`` stanza.
_DEFAULT_LAYERS: list[str] = [
    "F.Cu",
    "B.Cu",
    "F.Mask",
    "B.Mask",
    "F.Paste",
    "B.Paste",
    "F.Silkscreen",
    "B.Silkscreen",
    "Edge.Cuts",
]


class PcbnewGerberGenerator:
    """Generate Gerber and drill files using ``pcbnew.PLOT_CONTROLLER``.

    Unlike :class:`~jbom.services.gerber_service.GerberExporter` (which
    spawns a ``kicad-cli`` subprocess), this class operates on the live board
    object already loaded in KiCad's memory — no subprocess is spawned and no
    PCB file needs to be re-read from disk.

    Args:
        board: The live ``pcbnew.BOARD`` object obtained from
            ``pcbnew.GetBoard()``.
    """

    def __init__(self, board: Any) -> None:
        """Store the live board reference.

        Args:
            board: ``pcbnew.BOARD`` object from ``pcbnew.GetBoard()``.
        """
        self._board = board

    def generate(
        self,
        output_dir: Path,
        *,
        fabricator: str = "generic",
        debug: bool = False,
    ) -> GerberResult:
        """Generate Gerber and drill files to *output_dir*.

        Layer selection is driven by the fabricator config's ``gerbers.layers``
        stanza.  Each layer name is resolved via ``board.GetLayerID(name)``
        and skipped with a diagnostic when it is absent from the board
        (``UNDEFINED_LAYER``) or disabled.

        Args:
            output_dir: Directory where Gerber and drill files are written.
                Created automatically if absent.
            fabricator: Fabricator profile identifier (e.g. ``"jlc"``) used to
                select the layer list and naming policy from the fabricator
                config YAML.
            debug: Informational flag; passed through to the caller.  Does not
                alter the output of this method (cleanup is the caller's
                responsibility).

        Returns:
            :class:`~jbom.services.gerber_service.GerberResult` with all
            written artifact paths and any accumulated diagnostics.
            ``skipped=True`` when generation could not proceed.
        """
        import pcbnew  # noqa: PLC0415 — only executed inside KiCad

        diagnostics: list[str] = []
        artifacts_before_drill: list[Path] = []

        output_dir = Path(output_dir)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return GerberResult(
                artifacts=(),
                diagnostics=(f"Could not create Gerber output directory: {exc}",),
                skipped=True,
                skip_reason="output_dir_error",
            )

        # Resolve layer list, protel-extension flag, and drill config from the
        # fabricator profile.  Falls back to _DEFAULT_LAYERS on any error.
        layers, protel_extensions, drill_cfg = self._load_gerber_policy(
            fabricator, diagnostics
        )

        # pcbnew.UNDEFINED_LAYER is -1 in all supported KiCad versions; fall
        # back to -1 if the constant is absent (future-proofing).
        undefined_layer: int = getattr(pcbnew, "UNDEFINED_LAYER", -1)

        # ----------------------------------------------------------------
        # Gerber files — PLOT_CONTROLLER path (ported from FT process.py)
        # ----------------------------------------------------------------
        try:
            plot_controller = pcbnew.PLOT_CONTROLLER(self._board)
            plot_opts = plot_controller.GetPlotOptions()

            plot_opts.SetOutputDirectory(str(output_dir))
            plot_opts.SetPlotFrameRef(False)
            plot_opts.SetAutoScale(False)
            plot_opts.SetScale(1)
            plot_opts.SetMirror(False)
            plot_opts.SetUseGerberAttributes(True)
            plot_opts.SetUseGerberProtelExtensions(protel_extensions)
            plot_opts.SetUseAuxOrigin(True)
            plot_opts.SetSubtractMaskFromSilk(True)
            plot_opts.SetUseGerberX2format(False)
            plot_opts.SetDrillMarksType(0)  # NO_DRILL_SHAPE

            # SetExcludeEdgeLayer added in KiCad 7; guard for older builds.
            if hasattr(plot_opts, "SetExcludeEdgeLayer"):
                plot_opts.SetExcludeEdgeLayer(True)

            # SetSketchPadLineWidth may be absent on some builds.
            if hasattr(plot_opts, "SetSketchPadLineWidth"):
                plot_opts.SetSketchPadLineWidth(pcbnew.FromMM(0.1))

            for layer_name in layers:
                layer_id: int = self._board.GetLayerID(layer_name)

                if layer_id == undefined_layer:
                    diagnostics.append(
                        f"Gerber: layer {layer_name!r} not present on this board — skipped."
                    )
                    continue

                if not self._board.IsLayerEnabled(layer_id):
                    continue

                # Use the KiCad layer name (dots → underscores) as the file
                # suffix; pcbnew appends the correct Protel extension.
                suffix = layer_name.replace(".", "_").replace(" ", "_")
                plot_controller.SetLayer(layer_id)
                plot_controller.OpenPlotfile(
                    suffix, pcbnew.PLOT_FORMAT_GERBER, layer_name
                )
                plot_controller.PlotLayer()

            plot_controller.ClosePlot()

        except Exception as exc:
            diagnostics.append(f"Gerber plotting failed: {exc}")
            return GerberResult(
                artifacts=(),
                diagnostics=tuple(diagnostics),
                skipped=True,
                skip_reason="plot_error",
            )

        # Snapshot file list before adding drill files so we can diff later.
        artifacts_before_drill = sorted(p for p in output_dir.iterdir() if p.is_file())

        # ----------------------------------------------------------------
        # Drill files — EXCELLON_WRITER (ported from FT process.py)
        # ----------------------------------------------------------------
        try:
            generate_map = bool(drill_cfg.get("map_format"))

            drill_writer = pcbnew.EXCELLON_WRITER(self._board)
            drill_writer.SetOptions(
                False,  # aMirror
                False,  # aMinimalHeader
                self._board.GetDesignSettings().GetAuxOrigin(),
                False,  # aExcellonFormat
            )
            drill_writer.SetFormat(True)  # metric units
            if generate_map:
                drill_writer.SetMapFileFormat(pcbnew.PLOT_FORMAT_GERBER)
            drill_writer.CreateDrillandMapFilesSet(
                str(output_dir),
                True,  # aGenDrill
                generate_map,  # aGenMap
            )

        except Exception as exc:
            diagnostics.append(
                f"Drill file generation failed (Gerbers were written): {exc}"
            )
            # Gerbers succeeded — return them even if drills failed.
            if artifacts_before_drill:
                return GerberResult(
                    artifacts=tuple(artifacts_before_drill),
                    diagnostics=tuple(diagnostics),
                    skipped=False,
                )
            return GerberResult(
                artifacts=(),
                diagnostics=tuple(diagnostics),
                skipped=True,
                skip_reason="drill_error",
            )

        # Collect all written files (gerbers + drill).
        all_artifacts = sorted(p for p in output_dir.iterdir() if p.is_file())

        if not all_artifacts:
            return GerberResult(
                artifacts=(),
                diagnostics=tuple(diagnostics),
                skipped=True,
                skip_reason="no_artifacts",
            )

        return GerberResult(
            artifacts=tuple(all_artifacts),
            diagnostics=tuple(diagnostics),
            skipped=False,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_gerber_policy(
        self,
        fabricator: str,
        diagnostics: list[str],
    ) -> tuple[list[str], bool, dict[str, Any]]:
        """Return ``(layers, protel_extensions, drill_config)`` from fabricator config.

        Falls back to :data:`_DEFAULT_LAYERS` / protel=True / empty drill config
        when the fabricator config has no ``gerbers:`` stanza or cannot be loaded.

        Args:
            fabricator: Fabricator profile ID (e.g. ``"jlc"``).
            diagnostics: Mutable list to append diagnostic messages to.

        Returns:
            Triple ``(layers, protel_extensions, drill_cfg)`` where:

            * ``layers`` — ordered list of KiCad layer names to plot.
            * ``protel_extensions`` — whether to use Protel-style file extensions.
            * ``drill_cfg`` — mapping with optional ``split_plated_holes`` and
              ``map_format`` keys from the fabricator YAML.
        """
        try:
            from jbom.config.fabricators import load_fabricator  # noqa: PLC0415

            config = load_fabricator(fabricator)
            gerbers: dict[str, Any] = dict(config.gerbers or {})
            layers = list(gerbers.get("layers") or _DEFAULT_LAYERS)
            naming: dict[str, Any] = dict(gerbers.get("naming") or {})
            protel = bool(naming.get("protel_extensions", True))
            drill_cfg: dict[str, Any] = dict(gerbers.get("drill") or {})
            return layers, protel, drill_cfg
        except Exception as exc:
            diagnostics.append(
                f"Could not load Gerber policy for fabricator {fabricator!r} ({exc}); "
                "using default layer set."
            )
            return list(_DEFAULT_LAYERS), True, {}
