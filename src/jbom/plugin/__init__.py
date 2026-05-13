"""jBOM KiCad ActionPlugin adapter.

This is the PCM-installable plugin entry point for the jBOM fabrication
workflow.  Importing this module in a CLI or test environment is safe and
inert — no ``pcbnew`` import is attempted and no ActionPlugin is registered.

Guard pattern
-------------
Mirrors Fabrication Toolkit's ``plugins/__init__.py``:

.. code-block:: python

    _is_standalone = "pcbnew" not in sys.modules or __name__ == "__main__"
    if not _is_standalone:
        from .plugin import JBOMFabricationPlugin
        _plugin_instance = JBOMFabricationPlugin()
        _plugin_instance.register()

``sys.path`` bootstrapping
--------------------------
This module makes ``import jbom`` and the vendored third-party runtime
dependencies importable in both deployment modes:

* **PCM install** — ``jbom/`` and the pure-Python vendored packages
  (``pydantic``, ``yaml``, …) live alongside this file in ``<this_dir>``.
  The compiled ``pydantic_core`` extension lives under
  ``<this_dir>/_vendor/pydantic_core/<py_tag>-<plat_tag>/pydantic_core/``;
  :func:`_vendor_pydantic_core_path` picks the directory matching the
  running KiCad interpreter (CPython 3.9 on KiCad 9, CPython 3.12 on KiCad
  10) and prepends it to ``sys.path``.

* **Dev loop (symlink)** — this directory is ``src/jbom/plugin/`` symlinked
  into KiCad's scripting plugins folder as ``com_spcoast_jbom``.  We add
  ``src/`` (two levels up from ``plugin/``) so the editable ``jbom`` package
  is importable.  Third-party runtime deps are *not* auto-discovered from
  homebrew / user-site / venv paths anymore: export
  ``JBOM_PLUGIN_PYTHON_DEPS_DIR`` (colon-separated on Unix, semicolon on
  Windows) to point at site-packages dirs holding ``pydantic`` etc. when you
  need them.

Dev-loop setup (macOS, KiCad 9)::

    ln -s "$PWD/src/jbom/plugin" \\
      ~/Library/Application\\ Support/kicad/9.0/scripting/plugins/com_spcoast_jbom

Important: use ``com_spcoast_jbom`` (not ``jbom``) as the symlink target name
to avoid a naming conflict with the importable ``jbom`` package when KiCad
adds the scripting plugins directory to ``sys.path``.

Diagnostics
-----------
Set ``JBOM_PLUGIN_DEBUG=1`` before launching KiCad to capture the bootstrap
mode, selected vendor tag, and inserted ``sys.path`` entries in the
environment variable ``JBOM_PLUGIN_BOOTSTRAP_INFO`` (JSON).  The plugin
dialog surfaces this via the load-stamp tooltip in debug mode.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path discovery
# ---------------------------------------------------------------------------

# ``os.path.realpath`` (not abspath) is required here: in dev-loop mode this
# file is reached via a symlink and we want the *real* source location so
# ``src/`` and ``_vendor/`` are both resolved consistently.
_this_dir = Path(os.path.realpath(__file__)).parent
# Two levels up from ``src/jbom/plugin/`` lands at ``src/`` in the dev tree.
# In PCM mode (``${KICADX_3RD_PARTY}/plugins/com_spcoast_jbom/``) this
# resolves to ``${KICADX_3RD_PARTY}/plugins/``, which is already in sys.path
# by the time KiCad loads us — adding it again later is harmless.
_src_dir = _this_dir.parent.parent


def _is_dev_loop_checkout(this_dir: Path, src_dir: Path) -> bool:
    """Return True when the plugin is running from the source-tree dev loop."""
    return src_dir.name == "src" and (src_dir.parent / "pyproject.toml").is_file()


# ---------------------------------------------------------------------------
# Vendored-binary selection (PCM mode)
# ---------------------------------------------------------------------------


def _vendor_folder_tag() -> str | None:
    """Compute the ``_vendor/pydantic_core/<tag>/`` folder for this interpreter.

    Returns ``None`` for unsupported (python_version, os, arch) combinations.
    """
    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        if machine in {"arm64", "aarch64"}:
            return f"{py_tag}-macosx_arm64"
        if machine in {"x86_64", "amd64"}:
            return f"{py_tag}-macosx_x86_64"
        return None
    if sys.platform.startswith("linux"):
        if machine in {"x86_64", "amd64"}:
            return f"{py_tag}-manylinux_x86_64"
        if machine in {"aarch64", "arm64"}:
            return f"{py_tag}-manylinux_aarch64"
        return None
    if sys.platform == "win32":
        if machine in {"amd64", "x86_64"}:
            return f"{py_tag}-win_amd64"
        return None
    return None


def _vendor_pydantic_core_path(this_dir: Path) -> Path | None:
    """Return the directory holding the matching ``pydantic_core`` package.

    Returns ``None`` when no compatible vendored copy is present.  Falls back
    to a ``local_*`` directory produced by ``--skip-binary-fetch`` builds when
    no exact tag match is found.
    """
    tag = _vendor_folder_tag()
    if tag is not None:
        candidate = this_dir / "_vendor" / "pydantic_core" / tag
        if (candidate / "pydantic_core").is_dir():
            return candidate
    local_dir = this_dir / "_vendor" / "pydantic_core"
    if local_dir.is_dir():
        for sub in sorted(local_dir.iterdir()):
            if sub.is_dir() and (sub / "pydantic_core").is_dir():
                return sub
    return None


# ---------------------------------------------------------------------------
# sys.path bootstrapping
# ---------------------------------------------------------------------------


def _dev_loop_extra_dependency_paths() -> list[Path]:
    """Return developer-provided dependency dirs honoured in dev-loop mode.

    Only ``JBOM_PLUGIN_PYTHON_DEPS_DIR`` (colon/semicolon-separated list) is
    consulted; we no longer probe homebrew or user-site directories.  This
    keeps the dev loop predictable and free of accidental imports from the
    host OS Python install.
    """
    raw = os.environ.get("JBOM_PLUGIN_PYTHON_DEPS_DIR", "").strip()
    if not raw:
        return []
    sep = ";" if sys.platform == "win32" else ":"
    candidates: list[Path] = []
    for entry in raw.split(sep):
        entry = entry.strip()
        if not entry:
            continue
        path = Path(entry).expanduser()
        if path.is_dir():
            candidates.append(path)
    return candidates


def _bootstrap_sys_path() -> dict[str, object]:
    """Insert the right vendored-deps directories onto ``sys.path``.

    Returns a small diagnostic dict describing the mode, selected tag, and
    inserted paths so callers can stash it (e.g. via env var) without us
    leaking dev-loop assumptions into production sessions.
    """
    inserted: list[str] = []

    def _prepend(path: Path) -> None:
        path_str = str(path)
        if path_str in sys.path:
            return
        sys.path.insert(0, path_str)
        inserted.append(path_str)

    dev_loop = _is_dev_loop_checkout(_this_dir, _src_dir)
    info: dict[str, object] = {
        "this_dir": str(_this_dir),
        "src_dir": str(_src_dir),
        "mode": "dev-loop" if dev_loop else "pcm",
        "tag": None,
        "inserted": inserted,
    }

    # In PCM mode, the compiled pydantic_core lives under _vendor/. Prepend
    # the matching directory (if any) before the plugin dir itself so the
    # import resolves to the bundled package.
    pydantic_core_dir = _vendor_pydantic_core_path(_this_dir)
    if pydantic_core_dir is not None:
        info["tag"] = pydantic_core_dir.name
        _prepend(pydantic_core_dir)

    # Plugin dir itself is always on the path so the pure-Python vendored
    # packages (pydantic, yaml, …) and the vendored ``jbom`` package are
    # importable.
    _prepend(_this_dir)

    # Dev-loop only: editable ``src/`` and optional user-supplied deps dir.
    if dev_loop:
        _prepend(_src_dir)
        for extra in _dev_loop_extra_dependency_paths():
            _prepend(extra)

    return info


_bootstrap_info = _bootstrap_sys_path()

# Only publish the bootstrap detail through the environment when explicitly
# asked.  The dialog reads ``JBOM_PLUGIN_BOOTSTRAP_INFO`` to render the debug
# tooltip; production users see nothing.
if os.environ.get("JBOM_PLUGIN_DEBUG", "").strip() == "1":
    try:
        os.environ["JBOM_PLUGIN_BOOTSTRAP_INFO"] = json.dumps(_bootstrap_info)
    except (TypeError, ValueError):
        pass

# ---------------------------------------------------------------------------
# ActionPlugin registration — KiCad context only
# ---------------------------------------------------------------------------

# ``pcbnew`` is pre-loaded by KiCad's embedded Python before any plugin
# ``__init__.py`` runs.  In CLI/test environments it is never present.
_is_standalone = "pcbnew" not in sys.modules or __name__ == "__main__"

if not _is_standalone:  # pragma: no cover — only executes inside KiCad
    try:
        from .plugin import JBOMFabricationPlugin

        # Store the instance at module level — mirrors FT's pattern of
        # ``plugin = Plugin(); plugin.register()``.  Without this, the
        # temporary JBOMFabricationPlugin() may be GC'd immediately after
        # register() returns; KiCad's ActionPlugin registry holds only a
        # C++ pointer, so a collected Python wrapper causes silent
        # suppression of subsequent ``Run()`` calls — the toolbar button
        # appears to work once and then becomes inert.  Retaining a
        # module-level reference prevents GC for the KiCad session.
        _plugin_instance = JBOMFabricationPlugin()
        _plugin_instance.register()
    except Exception:
        import traceback

        traceback.print_exc()
