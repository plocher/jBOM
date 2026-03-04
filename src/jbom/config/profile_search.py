"""Profile search path resolution for jBOM configuration files.

Provides a shared mechanism for locating *.fab.yaml, *.supplier.yaml,
*.defaults.yaml (and future profile types) across a prioritized search path.

Search order (highest priority first):
  1. <cwd>/.jbom/
  2. <repo_root>/.jbom/  (walk up from cwd looking for .git)
  3. Directories in JBOM_PROFILE_PATH env var (colon-separated on Unix)
  4. ~/.jbom/
  5. Platform system directory
  6. Built-in package directory (passed explicitly by each loader)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def find_profile(
    name: str,
    suffix: str,
    *,
    cwd: Path | None = None,
    builtin_dir: Path | None = None,
) -> Path | None:
    """Find the first matching profile file across the search path.

    Searches user-configurable locations in priority order, then falls back
    to the built-in package directory if provided.

    Args:
        name: Profile name (e.g. 'generic', 'jlc', 'aerospace').
        suffix: Profile type suffix without dots (e.g. 'fab', 'supplier', 'defaults').
        cwd: Working directory for project-local search. Defaults to Path.cwd().
        builtin_dir: Package-internal directory to check last. Each loader
            passes its own type-specific built-in directory here.

    Returns:
        Path to the first matching file found, or None if not found anywhere.
    """
    filename = f"{name}.{suffix}.yaml"
    dirs = list(profile_search_dirs(cwd=cwd))
    if builtin_dir is not None:
        dirs.append(builtin_dir)
    for directory in dirs:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def profile_search_dirs(*, cwd: Path | None = None) -> list[Path]:
    """Return the ordered list of user-configurable directories searched for profiles.

    Does NOT include the built-in package directory; callers append that via
    the builtin_dir parameter of find_profile().

    Args:
        cwd: Working directory override. Defaults to Path.cwd().

    Returns:
        Ordered list of directories (may include non-existent paths).
    """
    search_cwd = (cwd or Path.cwd()).resolve()
    dirs: list[Path] = []

    # 1. .jbom/ in cwd
    dirs.append(search_cwd / ".jbom")

    # 2. .jbom/ at repo root (if different from cwd)
    repo_root = _find_repo_root(search_cwd)
    if repo_root is not None and repo_root != search_cwd:
        dirs.append(repo_root / ".jbom")

    # 3. JBOM_PROFILE_PATH env var (colon-separated on Unix, semicolon on Windows)
    env_path = os.environ.get("JBOM_PROFILE_PATH", "")
    if env_path:
        sep = ";" if sys.platform == "win32" else ":"
        for entry in env_path.split(sep):
            entry = entry.strip()
            if entry:
                dirs.append(Path(entry))

    # 4. ~/.jbom/
    dirs.append(Path.home() / ".jbom")

    # 5. Platform system directory
    dirs.extend(_platform_system_dirs())

    return dirs


def _find_repo_root(start: Path) -> Path | None:
    """Walk up the directory tree looking for a .git directory or file."""
    current = start
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _platform_system_dirs() -> list[Path]:
    """Return platform-specific system-level config directories."""
    if sys.platform == "darwin":
        return [Path.home() / "Library" / "Application Support" / "jBOM"]
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        return [Path(appdata) / "jBOM"] if appdata else []
    # Linux / other Unix: XDG_DATA_HOME → ~/.local/share → /usr/local/share
    xdg = os.environ.get("XDG_DATA_HOME", "")
    dirs: list[Path] = []
    dirs.append(
        Path(xdg) / "jbom" if xdg else Path.home() / ".local" / "share" / "jbom"
    )
    dirs.append(Path("/usr/local/share/jbom"))
    return dirs


__all__ = ["find_profile", "profile_search_dirs"]
