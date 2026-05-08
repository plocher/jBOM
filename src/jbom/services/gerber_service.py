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
            for future plot-option customisation per fabricator; currently
            used only for diagnostics.
        include_drill: When ``True`` (default) also run ``kicad-cli pcb export
            drill`` to produce PTH/NPTH drill files.
        include_netlist: When ``True`` also run ``kicad-cli pcb export ipc356``
            to produce an IPC-D-356 netlist.  Defaults to ``False`` as most
            fabricators do not require it.
    """

    pcb_file: Path
    output_directory: Path
    fabricator: str = "generic"
    include_drill: bool = True
    include_netlist: bool = False

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
        err = self._run_kicad_cli(
            kicad_cli,
            args=[
                "pcb",
                "export",
                "gerbers",
                "--output",
                str(request.output_directory),
                str(request.pcb_file),
            ],
            step="gerbers",
        )
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
            err = self._run_kicad_cli(
                kicad_cli,
                args=[
                    "pcb",
                    "export",
                    "drill",
                    "--output",
                    str(request.output_directory),
                    str(request.pcb_file),
                ],
                step="drill",
            )
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
