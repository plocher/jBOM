"""Per-project jBOM plugin options persistence.

Reads and writes ``jbom-options.json`` to the project's ``.jbom/`` directory,
resolved from the git repository root.  Falls back to ``~/.jbom/`` when no
git root can be determined (e.g. the PCB file lives outside any repository).

Persisted fields
----------------
``fabricator``
    Fabricator profile identifier (e.g. ``"jlc"``, ``"pcbway"``).
    Defaults to ``"jlc"``.

``inventory_path``
    Absolute path to the inventory CSV/XLSX/Numbers file, or empty string
    (meaning "no inventory — generate BOM without enrichment").

Session-only settings — checkboxes (SMD only, Exclude DNP, Fill zones,
Create backup, Open production folder, Debug mode) — are **not** persisted.
They reset to their defaults each time the dialog opens.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

__all__ = [
    "PluginOptions",
    "load_options",
    "save_options",
]

_OPTIONS_FILENAME = "jbom-options.json"
_OPTIONS_DIR = ".jbom"


@dataclass
class PluginOptions:
    """Persisted per-project plugin preferences.

    Attributes:
        fabricator: Fabricator profile identifier (e.g. ``"jlc"``).
        inventory_path: Path to the inventory file, or empty string.
    """

    fabricator: str = "jlc"
    inventory_path: str = ""

    def to_dict(self) -> dict[str, str]:
        """Serialize options to a JSON-compatible mapping."""
        return asdict(self)  # type: ignore[return-value]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PluginOptions":
        """Deserialize options from a mapping; extra keys are silently ignored.

        Args:
            data: Mapping previously produced by :meth:`to_dict` (or parsed
                from JSON).

        Returns:
            :class:`PluginOptions` with recognized fields populated; unknown
            fields are discarded.
        """
        fabricator = str(data.get("fabricator", "jlc")).strip() or "jlc"
        inventory_path = str(data.get("inventory_path", ""))
        return cls(fabricator=fabricator, inventory_path=inventory_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_git_root(start_dir: Path) -> Path | None:
    """Return the git repository root containing *start_dir*, or ``None``.

    Args:
        start_dir: Directory from which to start the upward search.

    Returns:
        Absolute :class:`~pathlib.Path` of the repository root, or ``None``
        if *start_dir* is not inside a git repository or if ``git`` is not
        available.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
        pass
    return None


def _options_file(project_path: Path) -> Path:
    """Return the canonical path for ``jbom-options.json``.

    Resolution order:

    1. ``$git_root/.jbom/jbom-options.json`` — version-controllable, shared
       across the whole project checkout.
    2. ``~/.jbom/jbom-options.json`` — fallback when no git root is found.

    Args:
        project_path: KiCad project directory or PCB file path.

    Returns:
        Absolute path to the options file (may not yet exist).
    """
    start = project_path if project_path.is_dir() else project_path.parent
    git_root = _find_git_root(start)
    base = git_root if git_root is not None else Path.home()
    return base / _OPTIONS_DIR / _OPTIONS_FILENAME


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_options(project_path: Path) -> PluginOptions:
    """Load :class:`PluginOptions` from disk; return defaults on any failure.

    This function never raises — a malformed or absent options file simply
    returns :class:`PluginOptions` defaults.

    Args:
        project_path: KiCad project directory or PCB file path.

    Returns:
        Persisted :class:`PluginOptions`, or defaults when the file is absent,
        empty, or malformed.
    """
    path = _options_file(project_path)
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8")
            data: dict[str, object] = json.loads(raw)
            return PluginOptions.from_dict(data)
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    return PluginOptions()


def save_options(options: PluginOptions, project_path: Path) -> None:
    """Persist :class:`PluginOptions` to disk.

    Creates the parent ``.jbom/`` directory if it does not already exist.

    Args:
        options: Options instance to persist.
        project_path: KiCad project directory or PCB file path.

    Raises:
        OSError: If the file cannot be written (disk full, permissions, etc.).
    """
    path = _options_file(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(options.to_dict(), indent=2, ensure_ascii=False)
    path.write_text(payload, encoding="utf-8")
