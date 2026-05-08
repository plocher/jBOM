"""Gerber/drill/netlist export service for fabrication artifact generation.

Tiered dispatch:
1. ``kicad-cli pcb export`` subprocess — located via PATH, then platform-specific
   well-known installation directories (macOS app bundle, Windows Program Files,
   common Linux paths).
2. ``pcbnew`` Python API (plugin mode) — stub only; raises a diagnostic because
   the implementation is deferred to the plugin adapter issue (#227).
3. Graceful degradation — when neither path is available the service returns a
   ``GerberResult`` with ``skipped=True`` and an actionable diagnostic.  BOM
   and POS generation are unaffected.

Usage::

    from jbom.services.gerber_service import GerberExporter, GerberRequest

    result = GerberExporter().generate(
        GerberRequest(
            pcb_file=Path("myproject.kicad_pcb"),
            output_directory=Path("fab/gerbers"),
        )
    )
    if result.skipped:
        print(result.skip_reason)
    else:
        for path in result.artifacts:
            print(path)
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from jbom.common.kicad_runtime import is_running_inside_kicad

__all__ = [
    "GerberExporter",
    "GerberRequest",
    "GerberResult",
    "gerber_request_from_config",
]


def _find_kicad_cli() -> str | None:
    """Return the path to the kicad-cli executable, or ``None`` if not found.

    Search order:
    1. ``PATH`` — covers Linux system installs and any user-configured PATH.
    2. Platform-specific well-known installation directories:
       - **macOS**: ``/Applications/KiCad/KiCad.app/Contents/MacOS/``
       - **Windows**: ``%PROGRAMFILES%\\KiCad\\<version>\\bin\\`` (versions 7–9)
       - **Linux**: ``/usr/bin/``, ``/usr/local/bin/``, ``/snap/bin/``
    """
    # Try both spellings; KiCad uses a hyphen but some older builds used underscore.
    for name in ("kicad-cli", "kicad_cli"):
        found = shutil.which(name)
        if found:
            return found

    system = platform.system()
    candidates: list[Path] = []

    if system == "Darwin":
        bundle = Path("/Applications/KiCad/KiCad.app/Contents/MacOS")
        candidates = [bundle / "kicad-cli", bundle / "kicad_cli"]

    elif system == "Windows":
        prog = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        for version in ("9.0", "8.0", "7.0"):
            candidates.append(prog / "KiCad" / version / "bin" / "kicad-cli.exe")

    else:  # Linux / BSD / other
        candidates = [
            Path("/usr/bin/kicad-cli"),
            Path("/usr/local/bin/kicad-cli"),
            Path("/snap/bin/kicad-cli"),
        ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    return None


def _kicad_cli_not_found_message() -> str:
    """Return a platform-appropriate diagnostic when kicad-cli cannot be located."""
    system = platform.system()
    if system == "Darwin":
        install_hint = (
            "On macOS, install KiCad from https://www.kicad.org/download/ — "
            "jBOM checks /Applications/KiCad/KiCad.app/Contents/MacOS/ automatically."
        )
    elif system == "Windows":
        install_hint = (
            r"On Windows, install KiCad from https://www.kicad.org/download/ — "
            r"jBOM checks C:\Program Files\KiCad\<version>\bin\ automatically."
        )
    else:
        install_hint = (
            "On Linux, install KiCad via your package manager (e.g. "
            "`sudo apt install kicad` or `sudo dnf install kicad`). "
            "kicad-cli is usually placed on PATH automatically."
        )
    return (
        f"kicad-cli not found. {install_hint} " "BOM and POS generation are unaffected."
    )


def _normalize_text(value: str, *, field_name: str) -> str:
    """Validate and normalise a required non-empty text field."""
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


@dataclass(frozen=True)
class GerberRequest:
    """Adapter-neutral request for Gerber/drill/netlist generation.

    Attributes:
        pcb_file: Path to the ``.kicad_pcb`` source file.
        output_directory: Directory where fabrication artifacts are written.
            Created automatically if it does not exist.
        fabricator: Fabricator profile identifier (e.g. ``"jlc"``).  Reserved
            for diagnostics and future plot-option customisation.
        include_drill: When ``True`` (default) run ``kicad-cli pcb export drill``.
        include_netlist: When ``True`` also run ``kicad-cli pcb export ipc356``
            to produce an IPC-D-356 netlist.  Defaults to ``False``.
        layers: Explicit allowlist of KiCad layer names to export (e.g.
            ``("F.Cu", "B.Cu", "Edge.Cuts")``).  ``None`` exports all layers
            (kicad-cli default — equivalent to no ``--layers`` flag).
        protel_extensions: When ``True`` (default) kicad-cli uses Protel-style
            extensions (``.gtl``, ``.gbl``, etc.).  ``False`` passes
            ``--no-protel-ext`` and all files get the generic ``.gbr`` extension.
        drill_split_plated_holes: When ``True`` produce separate ``*-PTH.drl``
            and ``*-NPTH.drl`` files via ``--excellon-separate-th``.  ``False``
            (default) produces a single merged ``*.drl``.
        drill_map_format: When non-``None``, generate a drill-map file via
            ``--generate-map --map-format <value>``.  Accepted values match
            kicad-cli: ``"gerber"``, ``"pdf"``, ``"svg"``, ``"ps"``, ``"dxf"``.
            ``None`` (default) generates no map.
    """

    pcb_file: Path
    output_directory: Path
    fabricator: str = "generic"
    include_drill: bool = True
    include_netlist: bool = False
    layers: tuple[str, ...] | None = None
    protel_extensions: bool = True
    drill_split_plated_holes: bool = False
    drill_map_format: str | None = None

    def __post_init__(self) -> None:
        # Validate raw input *before* Path coercion: Path("") → Path(".") in Python,
        # so checking str() of the already-coerced value would silently accept "".
        if not str(self.pcb_file or "").strip():
            raise ValueError("pcb_file must be non-empty")
        if not str(self.output_directory or "").strip():
            raise ValueError("output_directory must be non-empty")
        object.__setattr__(self, "pcb_file", Path(self.pcb_file))
        object.__setattr__(self, "output_directory", Path(self.output_directory))
        object.__setattr__(
            self,
            "fabricator",
            _normalize_text(self.fabricator or "generic", field_name="fabricator"),
        )
        object.__setattr__(self, "include_drill", bool(self.include_drill))
        object.__setattr__(self, "include_netlist", bool(self.include_netlist))
        if self.layers is not None:
            object.__setattr__(
                self,
                "layers",
                tuple(
                    str(layer).strip() for layer in self.layers if str(layer).strip()
                ),
            )
        object.__setattr__(self, "protel_extensions", bool(self.protel_extensions))
        object.__setattr__(
            self, "drill_split_plated_holes", bool(self.drill_split_plated_holes)
        )
        object.__setattr__(
            self,
            "drill_map_format",
            str(self.drill_map_format).strip().lower()
            if self.drill_map_format
            else None,
        )


@dataclass(frozen=True)
class GerberResult:
    """Result from a Gerber/drill/netlist generation attempt.

    Attributes:
        artifacts: Paths of all files written to ``output_directory``.
            Empty when ``skipped`` is ``True``.
        diagnostics: Human-readable messages emitted during generation.
            Always present; may be empty on clean success.
        skipped: ``True`` when generation could not proceed (e.g. missing
            ``kicad-cli``, missing PCB file, or plugin-mode stub).
        skip_reason: Short machine-readable token explaining why generation
            was skipped (e.g. ``"kicad_cli_not_found"``).  Empty string when
            ``skipped`` is ``False``.
    """

    artifacts: tuple[Path, ...]
    diagnostics: tuple[str, ...]
    skipped: bool = False
    skip_reason: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "skipped", bool(self.skipped))
        object.__setattr__(self, "skip_reason", str(self.skip_reason or ""))


class GerberExporter:
    """Generate Gerber, drill, and netlist fabrication artifacts from a KiCad PCB.

    Dispatch priority:
    1. When **not** running inside KiCad: ``kicad-cli`` subprocess.
    2. When running inside KiCad (plugin mode): ``pcbnew`` API stub —
       returns a diagnostic because the implementation is deferred to #227.
    """

    def generate(self, request: GerberRequest) -> GerberResult:
        """Generate fabrication artifacts for the given PCB file.

        Args:
            request: Options for Gerber/drill/netlist generation.

        Returns:
            :class:`GerberResult` with artifact paths and diagnostics.
            ``skipped`` is ``True`` when generation was not possible.
        """
        if is_running_inside_kicad():
            return self._generate_via_pcbnew(request)
        return self._generate_via_kicad_cli(request)

    # ------------------------------------------------------------------
    # Private dispatch implementations
    # ------------------------------------------------------------------

    def _generate_via_pcbnew(self, request: GerberRequest) -> GerberResult:
        """Plugin-mode stub — pcbnew API generation is not yet implemented."""
        return GerberResult(
            artifacts=(),
            diagnostics=(
                "Gerber generation via the pcbnew Python API is not yet implemented "
                "(tracked in issue #227). "
                "To generate Gerbers, run `jbom gerbers` from the command line "
                "where kicad-cli is available.",
            ),
            skipped=True,
            skip_reason="pcbnew_api_not_implemented",
        )

    def _generate_via_kicad_cli(self, request: GerberRequest) -> GerberResult:
        """Generate Gerbers by invoking kicad-cli as a subprocess."""
        kicad_cli = _find_kicad_cli()
        if kicad_cli is None:
            return GerberResult(
                artifacts=(),
                diagnostics=(_kicad_cli_not_found_message(),),
                skipped=True,
                skip_reason="kicad_cli_not_found",
            )

        if not request.pcb_file.exists():
            return GerberResult(
                artifacts=(),
                diagnostics=(
                    f"PCB file not found: {request.pcb_file}. "
                    "Gerber generation skipped.",
                ),
                skipped=True,
                skip_reason="pcb_file_not_found",
            )

        request.output_directory.mkdir(parents=True, exist_ok=True)

        diagnostics: list[str] = []
        artifacts: list[Path] = []

        # --- Gerbers ---
        before = set(request.output_directory.iterdir())
        gerber_args = [
            "pcb",
            "export",
            "gerbers",
            "--output",
            str(request.output_directory),
        ]
        if request.layers:
            gerber_args.extend(["--layers", ",".join(request.layers)])
        if not request.protel_extensions:
            gerber_args.append("--no-protel-ext")
        gerber_args.append(str(request.pcb_file))
        err = self._run_kicad_cli(kicad_cli, args=gerber_args, step="gerbers")
        if err:
            diagnostics.append(err)
            return GerberResult(
                artifacts=(),
                diagnostics=tuple(diagnostics),
                skipped=True,
                skip_reason="gerber_export_failed",
            )
        after = set(request.output_directory.iterdir())
        artifacts.extend(sorted(after - before))

        # --- Drill files ---
        if request.include_drill:
            before = set(request.output_directory.iterdir())
            drill_args = [
                "pcb",
                "export",
                "drill",
                "--output",
                str(request.output_directory),
            ]
            if request.drill_split_plated_holes:
                drill_args.append("--excellon-separate-th")
            if request.drill_map_format:
                drill_args.extend(
                    ["--generate-map", "--map-format", request.drill_map_format]
                )
            drill_args.append(str(request.pcb_file))
            err = self._run_kicad_cli(kicad_cli, args=drill_args, step="drill")
            if err:
                diagnostics.append(err)
            else:
                after = set(request.output_directory.iterdir())
                artifacts.extend(sorted(after - before))

        # --- IPC-D-356 netlist ---
        if request.include_netlist:
            netlist_file = request.output_directory / f"{request.pcb_file.stem}.ipc"
            before = set(request.output_directory.iterdir())
            err = self._run_kicad_cli(
                kicad_cli,
                args=[
                    "pcb",
                    "export",
                    "ipc356",
                    "--output",
                    str(netlist_file),
                    str(request.pcb_file),
                ],
                step="netlist",
            )
            if err:
                diagnostics.append(err)
            else:
                after = set(request.output_directory.iterdir())
                artifacts.extend(sorted(after - before))

        return GerberResult(
            artifacts=tuple(artifacts),
            diagnostics=tuple(diagnostics),
            skipped=False,
        )

    def _run_kicad_cli(
        self,
        kicad_cli: str,
        *,
        args: list[str],
        step: str,
    ) -> str | None:
        """Run a kicad-cli command.

        Returns:
            An error message string on failure, or ``None`` on success.
        """
        try:
            result = subprocess.run(
                [kicad_cli, *args],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "(no output)").strip()
                return (
                    f"kicad-cli {step} failed " f"(exit {result.returncode}): {detail}"
                )
            return None
        except subprocess.TimeoutExpired:
            return f"kicad-cli {step} timed out after 120 seconds"
        except OSError as exc:
            return f"kicad-cli {step} invocation failed: {exc}"


def gerber_request_from_config(
    pcb_file: Path,
    output_directory: Path,
    fabricator_id: str = "generic",
    gerbers_cfg: dict | None = None,
) -> GerberRequest:
    """Build a :class:`GerberRequest` from a fabricator ``gerbers`` config dict.

    Pass the ``FabricatorConfig.gerbers`` mapping (or ``None`` to use defaults).
    When ``gerbers_cfg`` is ``None`` the request uses kicad-cli defaults: all
    layers, Protel extensions enabled, merged drill file, no drill maps.

    Args:
        pcb_file: Path to the ``.kicad_pcb`` source file.
        output_directory: Directory where Gerber artifacts will be written.
        fabricator_id: Fabricator identifier for diagnostics.
        gerbers_cfg: The ``gerbers`` sub-dict from a fabricator YAML, or ``None``.

    Returns:
        A fully populated :class:`GerberRequest`.
    """
    cfg = gerbers_cfg or {}

    # --- layers ---
    layers_raw = cfg.get("layers")
    layers: tuple[str, ...] | None = None
    if layers_raw and isinstance(layers_raw, list):
        layers = tuple(str(layer).strip() for layer in layers_raw if str(layer).strip())

    # --- naming ---
    naming = cfg.get("naming") or {}
    protel_extensions = bool(naming.get("protel_extensions", True))

    # --- drill ---
    drill = cfg.get("drill") or {}
    split = bool(drill.get("split_plated_holes", False))
    map_fmt_raw = drill.get("map_format")
    map_fmt: str | None = str(map_fmt_raw).strip().lower() if map_fmt_raw else None

    return GerberRequest(
        pcb_file=pcb_file,
        output_directory=output_directory,
        fabricator=fabricator_id,
        layers=layers,
        protel_extensions=protel_extensions,
        drill_split_plated_holes=split,
        drill_map_format=map_fmt,
    )
