"""Structured diagnostics for the jBOM KiCad plugin.

This module is **wx-free** so it can be imported and exercised from tests
without KiCad/wxPython.  It provides three layered diagnostic capabilities,
each designed to address one part of "what was the plugin doing?":

1. **Environment snapshot** — captured once per Python session (the KiCad
   process lifetime).  Describes plugin mode (PCM vs dev-loop), Python
   version, vendored ``pydantic_core`` tag, source path, and the sys.path
   entries the bootstrap inserted.  Cheap to render repeatedly; recomputed
   only on explicit ``invalidate_environment()`` (test hook).

2. **Profile snapshot** — captured per dialog invocation but cached by a
   fingerprint of discovered ``*.jbom.yaml`` files (path + mtime + size).
   When the user edits a profile, the fingerprint changes and the snapshot
   is rebuilt; otherwise the cached snapshot is reused so repeated dialog
   opens don't pay full discovery cost.

3. **Lifecycle log** — append-only, structured per-run.  Each Run() opens
   a new ``LifecycleRun`` collection that captures dialog open, user
   interactions, worker-thread step transitions, completion, and close.
   Runs are retained for the KiCad session (capped at
   ``_MAX_RETAINED_RUNS``) so the developer can compare consecutive runs.

A plain-text report renderer (:func:`render_text_report`) emits the union of
all three layers so the dialog's "Save log\u2026" button can write a file the
user can attach to a bug report.
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

_MAX_RETAINED_RUNS = 20
_MAX_EVENTS_PER_RUN = 200


# ---------------------------------------------------------------------------
# Environment snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """Static plugin runtime info captured once per Python session."""

    mode: str  # "pcm" | "dev-loop" | "unknown"
    python_version: str
    platform: str
    machine: str
    vendor_tag: str | None
    source_path: str
    source_mtime: str  # ISO 8601 local time, or "unknown"
    project_dir: str  # ``JBOM_PROJECT_DIR`` env, or ""
    profile_path_env: str  # ``JBOM_PROFILE_PATH`` env, or ""
    inserted_sys_path: tuple[str, ...]


_environment_cache: EnvironmentSnapshot | None = None


def capture_environment(*, force: bool = False) -> EnvironmentSnapshot:
    """Return the cached environment snapshot, computing it on first call.

    Args:
        force: When ``True``, recompute even if a cached snapshot exists.
            Useful for tests that mutate ``os.environ``.

    Returns:
        The cached :class:`EnvironmentSnapshot`.
    """
    global _environment_cache
    if _environment_cache is not None and not force:
        return _environment_cache

    bootstrap_info: dict[str, object] = {}
    raw = os.environ.get("JBOM_PLUGIN_BOOTSTRAP_INFO", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                bootstrap_info = parsed
        except (TypeError, ValueError):
            bootstrap_info = {}

    source_path_str = str(bootstrap_info.get("this_dir") or "")
    if not source_path_str:
        # Fall back to this file's location's parent (dev-loop tests).
        source_path_str = str(Path(__file__).resolve().parent)
    try:
        mtime = datetime.datetime.fromtimestamp(
            Path(source_path_str).stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        mtime = "unknown"

    inserted = bootstrap_info.get("inserted") or []
    inserted_tuple: tuple[str, ...] = tuple(
        str(p) for p in inserted if isinstance(p, (str, os.PathLike))
    )

    snapshot = EnvironmentSnapshot(
        mode=str(bootstrap_info.get("mode") or "unknown"),
        python_version=(
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
        platform=sys.platform,
        machine=platform.machine(),
        vendor_tag=(str(bootstrap_info["tag"]) if bootstrap_info.get("tag") else None),
        source_path=source_path_str,
        source_mtime=mtime,
        project_dir=os.environ.get("JBOM_PROJECT_DIR", "").strip(),
        profile_path_env=os.environ.get("JBOM_PROFILE_PATH", "").strip(),
        inserted_sys_path=inserted_tuple,
    )
    _environment_cache = snapshot
    return snapshot


def invalidate_environment() -> None:
    """Clear the cached environment snapshot (test hook)."""
    global _environment_cache
    _environment_cache = None


# ---------------------------------------------------------------------------
# Profile snapshot
# ---------------------------------------------------------------------------


# Role labels used to elide long paths in the diagnostics panel.
# Order here is the precedence used by ``_classify_dir``: the first match wins.
_ROLE_PROJECT = "Project"
_ROLE_HOME = "Home"
_ROLE_SYSTEM = "System"
_ROLE_ENV = "Env"
_ROLE_FACTORY = "Factory"
_ROLE_OTHER = "Other"


@dataclass(frozen=True)
class SearchDirInfo:
    """One entry in the profile search path.

    ``role`` is the short label used in the diagnostics panel (Project / Home /
    System / Env / Factory / Other).  ``is_builtin`` is kept as a back-compat
    convenience equivalent to ``role == 'Factory'``.
    """

    path: str
    exists: bool
    is_builtin: bool
    role: str = _ROLE_OTHER


@dataclass(frozen=True)
class ProfileSnapshot:
    """Per-invocation view of the unified profile subsystem.

    ``chain_entries`` is the full effective lineage from highest-priority to
    base.  The first entries come from the named profile and its ``extends:``
    chain; the trailing entries enumerate every ``common.jbom.yaml`` that the
    unified loader merges in as the implicit base layer, ordered from
    highest-priority (project) to lowest (factory).
    """

    fingerprint: str
    search_dirs: tuple[SearchDirInfo, ...]
    discovered_profiles: tuple[str, ...]
    stanza_ids: tuple[tuple[str, tuple[str, ...]], ...]  # (stanza, ids) pairs
    selected_fabricator: str
    selected_chain: tuple[str, ...]  # back-compat: profile names only
    selected_file: str  # "" when not resolved
    # ``chain_entries`` is the canonical lineage shown in the dialog: every
    # entry is a (role, short_name) pair where ``short_name`` is the profile
    # name (e.g. ``jlc``) without the ``.jbom.yaml`` suffix.
    chain_entries: tuple[tuple[str, str], ...] = ()


_profile_cache: ProfileSnapshot | None = None


def _fingerprint_profile_files(search_dirs: Iterable[Path]) -> str:
    """Hash a stable summary of every ``*.jbom.yaml`` file across search dirs.

    Includes path + size + mtime so any edit (including touch) invalidates
    the cache.  Hashes use ``hash()`` on a sorted tuple of tuples \u2014 we don't
    need cryptographic strength here, just a cheap inequality detector.
    """
    entries: list[tuple[str, int, int]] = []
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.jbom.yaml")):
            try:
                stat = path.stat()
            except OSError:
                continue
            entries.append((str(path), stat.st_size, int(stat.st_mtime_ns)))
    entries.sort()
    return f"{abs(hash(tuple(entries))):016x}"


def capture_profile_snapshot(
    selected_fabricator: str = "",
    *,
    cwd: Path | None = None,
) -> ProfileSnapshot:
    """Build (or reuse) a structured view of the unified profile subsystem.

    The snapshot is cached by a fingerprint derived from every discoverable
    ``*.jbom.yaml`` file's path + size + mtime.  When the user edits a
    profile (or adds one), the fingerprint changes and the snapshot is
    rebuilt; otherwise the cached snapshot is reused so repeated dialog
    invocations stay cheap.

    Args:
        selected_fabricator: The currently selected fabricator id, used to
            compute the resolved ``extends`` chain.
        cwd: Optional override for project-local search (defaults to
            ``Path.cwd()``).
    """
    global _profile_cache

    # Lazy import: avoid pulling pydantic/yaml into wx-free unit tests
    # that only exercise lifecycle bookkeeping.
    from jbom.config import profile_search as _ps
    from jbom.config import unified as _unified

    builtin_dir = Path(_unified._BUILTIN_DIR).resolve()
    user_dirs = list(_ps.profile_search_dirs(cwd=cwd))
    all_dirs: list[Path] = []
    seen: set[str] = set()
    for d in [*user_dirs, builtin_dir]:
        key = str(d)
        if key in seen:
            continue
        seen.add(key)
        all_dirs.append(d)

    fingerprint = _fingerprint_profile_files(all_dirs)
    if (
        _profile_cache is not None
        and _profile_cache.fingerprint == fingerprint
        and _profile_cache.selected_fabricator == selected_fabricator
    ):
        return _profile_cache

    role_lookup = _build_role_lookup(cwd=cwd, builtin_dir=builtin_dir)
    search_dirs = tuple(
        SearchDirInfo(
            path=str(d),
            exists=d.is_dir(),
            is_builtin=(d == builtin_dir),
            role=_classify_dir(d, role_lookup),
        )
        for d in all_dirs
    )

    discovered = tuple(_unified._discover_named_profile_names(all_dirs))

    stanza_ids: list[tuple[str, tuple[str, ...]]] = []
    for stanza in ("fab", "supplier", "defaults", "presets"):
        try:
            ids = _unified.list_unified_stanza_ids(
                stanza, cwd=cwd, builtin_dir=builtin_dir
            )
        except Exception:
            ids = []
        stanza_ids.append((stanza, tuple(ids)))

    chain, selected_file, extends_files = _resolve_chain(selected_fabricator, all_dirs)

    chain_entries = _build_chain_entries(chain, extends_files, all_dirs, role_lookup)

    snapshot = ProfileSnapshot(
        fingerprint=fingerprint,
        search_dirs=search_dirs,
        discovered_profiles=discovered,
        stanza_ids=tuple(stanza_ids),
        selected_fabricator=selected_fabricator,
        selected_chain=chain,
        selected_file=selected_file,
        chain_entries=chain_entries,
    )
    _profile_cache = snapshot
    return snapshot


def _build_chain_entries(
    chain: tuple[str, ...],
    extends_files: tuple[str, ...],
    search_dirs: list[Path],
    role_lookup: tuple[tuple[Path, str], ...],
) -> tuple[tuple[str, str], ...]:
    """Build the unified chain shown to the user.

    The chain enumerates the named profile + its ``extends:`` ancestors in
    most-specific-first order, then appends every ``common.jbom.yaml`` that
    the loader implicitly merges in as the base layer, in priority order.
    """
    entries: list[tuple[str, str]] = []
    for name, file_path in zip(chain, extends_files):
        role = _role_for_file(file_path, role_lookup)
        entries.append((role, name))
    for directory in search_dirs:
        candidate = directory / "common.jbom.yaml"
        if candidate.is_file():
            role = _role_for_file(str(candidate), role_lookup)
            entries.append((role, "common"))
    return tuple(entries)


def _role_for_file(file_path: str, role_lookup: tuple[tuple[Path, str], ...]) -> str:
    """Return the role of *file_path* (its containing directory)."""
    if not file_path:
        return _ROLE_OTHER
    try:
        parent = Path(file_path).parent
    except (ValueError, OSError):
        return _ROLE_OTHER
    return _classify_dir(parent, role_lookup)


def _build_role_lookup(
    *, cwd: Path | None, builtin_dir: Path
) -> tuple[tuple[Path, str], ...]:
    """Return ``(anchor_dir, role)`` pairs used to classify search-path entries.

    Order matters: ``_classify_dir`` returns the role of the first anchor
    that is a prefix of the input path.  Anchors are listed most-specific
    first so the project ``.jbom`` (which is typically inside the user's
    home directory) is not classified as Home.
    """
    from jbom.config import profile_search as _ps

    anchors: list[tuple[Path, str]] = []
    try:
        project_cwd = _ps._resolve_search_cwd(cwd)
        anchors.append((project_cwd / ".jbom", _ROLE_PROJECT))
        repo_root = _ps._find_repo_root(project_cwd)
        if repo_root is not None and repo_root != project_cwd:
            anchors.append((repo_root / ".jbom", _ROLE_PROJECT))
    except Exception:
        pass

    env_path = os.environ.get("JBOM_PROFILE_PATH", "")
    if env_path:
        sep = ";" if sys.platform == "win32" else ":"
        for entry in env_path.split(sep):
            entry = entry.strip()
            if entry:
                try:
                    anchors.append((Path(entry).resolve(), _ROLE_ENV))
                except OSError:
                    pass

    try:
        anchors.append((Path.home() / ".jbom", _ROLE_HOME))
    except OSError:
        pass

    try:
        for system_dir in _ps._platform_system_dirs():
            anchors.append((system_dir, _ROLE_SYSTEM))
    except Exception:
        pass

    anchors.append((builtin_dir, _ROLE_FACTORY))
    return tuple(anchors)


def _classify_dir(path: Path, anchors: tuple[tuple[Path, str], ...]) -> str:
    """Return the role for *path* ("Project", "Home", "Factory", …)."""
    for anchor, role in anchors:
        try:
            if path == anchor or _is_relative_to(path, anchor):
                return role
        except Exception:
            continue
    return _ROLE_OTHER


def _is_relative_to(path: Path, anchor: Path) -> bool:
    """``Path.is_relative_to`` polyfill for Python 3.9 compatibility."""
    try:
        path.relative_to(anchor)
        return True
    except (ValueError, OSError):
        return False


def _elide_path(path_str: str, anchors: tuple[tuple[Path, str], ...]) -> str:
    """Replace the longest matching anchor prefix with its role label.

    e.g. ``/.../jBOM/src/jbom/config/profiles/jlc.jbom.yaml`` becomes
    ``Factory / jlc.jbom.yaml``.
    """
    if not path_str:
        return ""
    try:
        target = Path(path_str)
    except (ValueError, OSError):
        return path_str
    for anchor, role in anchors:
        try:
            if _is_relative_to(target, anchor):
                rel = target.relative_to(anchor)
                return f"{role} / {rel}" if str(rel) != "." else role
        except Exception:
            continue
    return path_str


def invalidate_profile_snapshot() -> None:
    """Clear the cached profile snapshot (test hook)."""
    global _profile_cache
    _profile_cache = None


def _resolve_chain(
    selected_fabricator: str, search_dirs: list[Path]
) -> tuple[tuple[str, ...], str, tuple[str, ...]]:
    """Walk the ``extends:`` chain for *selected_fabricator*.

    Returns ``(chain_names, first_file, all_files)`` where ``chain_names`` is
    the tuple of profile names (``child``, ``parent``, ``grandparent``, ...),
    ``first_file`` is the file path of the named profile (the leftmost
    entry), and ``all_files`` is the parallel tuple of file paths for every
    entry in ``chain_names``.  Stops on cycles or missing parents.
    """
    if not selected_fabricator:
        return (), "", ()

    from jbom.config import unified as _unified

    name = selected_fabricator.strip().lower()
    visited: list[str] = []
    files: list[str] = []
    file_for_first = ""
    while name and name not in visited:
        path = _unified._find_named_profile_path(name, search_dirs)
        if path is None:
            break
        visited.append(name)
        files.append(str(path))
        if not file_for_first:
            file_for_first = str(path)
        try:
            data = _unified._load_yaml_mapping(path, context=f"profile {name!r}")
        except Exception:
            break
        parent = data.get("extends")
        if not isinstance(parent, str):
            break
        name = parent.strip().lower()
    return tuple(visited), file_for_first, tuple(files)


# ---------------------------------------------------------------------------
# Lifecycle log (per-run collections retained for the KiCad session)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleEvent:
    """One row in a lifecycle run."""

    timestamp: str  # "HH:MM:SS"
    stage: str
    detail: str = ""


@dataclass
class LifecycleRun:
    """One dialog invocation's chronological events."""

    started_at: str  # "HH:MM:SS"
    pcb_path: str = ""
    events: list[LifecycleEvent] = field(default_factory=list)
    ended_at: str | None = None


_runs: list[LifecycleRun] = []
_active_run: LifecycleRun | None = None


def begin_run(*, pcb_path: str = "") -> LifecycleRun:
    """Start a new lifecycle run.  Ends any prior un-finished run first."""
    global _active_run
    if _active_run is not None and _active_run.ended_at is None:
        end_run()
    run = LifecycleRun(started_at=_now(), pcb_path=pcb_path)
    _runs.append(run)
    if len(_runs) > _MAX_RETAINED_RUNS:
        del _runs[: len(_runs) - _MAX_RETAINED_RUNS]
    _active_run = run
    return run


def record_event(stage: str, detail: str = "") -> None:
    """Append an event to the active run (no-op if no run is active)."""
    if _active_run is None:
        return
    if len(_active_run.events) >= _MAX_EVENTS_PER_RUN:
        return
    _active_run.events.append(
        LifecycleEvent(timestamp=_now(), stage=stage, detail=detail)
    )


def end_run() -> None:
    """Mark the active run finished."""
    global _active_run
    if _active_run is None:
        return
    _active_run.ended_at = _now()
    _active_run = None


def get_runs() -> tuple[LifecycleRun, ...]:
    """Return all retained runs (oldest first)."""
    return tuple(_runs)


def clear_runs() -> None:
    """Clear all retained runs (test hook).  Also ends any active run."""
    global _active_run
    _runs.clear()
    _active_run = None


def _now() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------


def render_environment(env: EnvironmentSnapshot) -> str:
    """Render the Environment section as plain text."""
    lines = [
        f"Mode:    {env.mode}",
        f"Python:  {env.python_version}  ({env.platform}/{env.machine})",
        f"Vendor:  {env.vendor_tag or '(none)'}",
        f"Source:  {env.source_path}  ({env.source_mtime})",
        f"Project: {env.project_dir or '(unset)'}",
        f"JBOM_PROFILE_PATH: {env.profile_path_env or '(unset)'}",
    ]
    if env.inserted_sys_path:
        lines.append("Inserted sys.path entries:")
        for entry in env.inserted_sys_path:
            lines.append(f"  - {entry}")
    return "\n".join(lines)


def render_profiles(snapshot: ProfileSnapshot) -> str:
    """Render the Profile subsystem section as plain text."""
    lines = ["Search dirs:"]
    role_width = max(
        (len(info.role) for info in snapshot.search_dirs),
        default=len(_ROLE_FACTORY),
    )
    for info in snapshot.search_dirs:
        mark = "\u2713" if info.exists else "\u2717"
        missing = "  (missing)" if not info.exists else ""
        lines.append(f"  {mark} {info.role.ljust(role_width)}  {info.path}{missing}")
    lines.append("Discovered: " + (", ".join(snapshot.discovered_profiles) or "(none)"))
    lines.append("Stanzas:")
    width = max((len(name) for name, _ in snapshot.stanza_ids), default=0)
    for name, ids in snapshot.stanza_ids:
        formatted = ", ".join(ids) if ids else "(none)"
        lines.append(f"  {name.ljust(width)}: {formatted}")
    if snapshot.selected_fabricator:
        if snapshot.chain_entries:
            chain = " \u2192 ".join(
                f"{role}:{name}" for role, name in snapshot.chain_entries
            )
        else:
            chain = "(unresolved)"
        lines.append(f"Selected: {snapshot.selected_fabricator}")
        lines.append(f"  chain: {chain}")
    lines.append(f"Fingerprint: {snapshot.fingerprint}")
    return "\n".join(lines)


def render_lifecycle(runs: Iterable[LifecycleRun]) -> str:
    """Render every lifecycle run as plain text, oldest first."""
    blocks: list[str] = []
    runs_list = list(runs)
    if not runs_list:
        return "(no runs recorded)"
    for index, run in enumerate(runs_list, start=1):
        header = f"--- Run {index} \u2014 started {run.started_at}"
        if run.ended_at:
            header += f"  ended {run.ended_at}"
        if run.pcb_path:
            header += f"\n     pcb={run.pcb_path}"
        block_lines = [header]
        if not run.events:
            block_lines.append("  (no events)")
        else:
            stage_width = max(len(e.stage) for e in run.events)
            for event in run.events:
                detail = f"  {event.detail}" if event.detail else ""
                block_lines.append(
                    f"  [{event.timestamp}] {event.stage.ljust(stage_width)}{detail}"
                )
        blocks.append("\n".join(block_lines))
    return "\n".join(blocks)


def render_text_report(
    env: EnvironmentSnapshot,
    profiles: ProfileSnapshot | None,
    runs: Iterable[LifecycleRun],
) -> str:
    """Render the full plain-text diagnostic report for "Save log\u2026"."""
    sections = [
        "=== Environment ===",
        render_environment(env),
        "",
        "=== Profile subsystem ===",
        render_profiles(profiles) if profiles is not None else "(not yet captured)",
        "",
        "=== Lifecycle ===",
        render_lifecycle(runs),
    ]
    return "\n".join(sections) + "\n"


__all__ = [
    "EnvironmentSnapshot",
    "LifecycleEvent",
    "LifecycleRun",
    "ProfileSnapshot",
    "SearchDirInfo",
    "begin_run",
    "capture_environment",
    "capture_profile_snapshot",
    "clear_runs",
    "end_run",
    "get_runs",
    "invalidate_environment",
    "invalidate_profile_snapshot",
    "record_event",
    "render_environment",
    "render_lifecycle",
    "render_profiles",
    "render_text_report",
]
