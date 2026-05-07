"""KiCad runtime environment detection and project write-guard utilities.

Provides two related capabilities:

1. ``is_running_inside_kicad()`` — detects whether jBOM is executing inside
   KiCad's embedded Python context (ActionPlugin mode).  When True, the plugin
   has direct in-memory access to board/schematic state; filesystem lock files
   and ``kicad-cli`` subprocess fallbacks are irrelevant.

2. ``check_write_permitted()`` — guards schematic write operations against
   KiCad lock files.  Silently bypasses in plugin mode.  Raises
   ``PermissionError`` on conflict in normal CLI mode; emits a warning instead
   when ``dry_run=True``.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jbom.services.project_context import ProjectContext

__all__ = ["is_running_inside_kicad", "check_write_permitted"]


def is_running_inside_kicad() -> bool:
    """Return ``True`` if jBOM is executing within KiCad's embedded Python context.

    Detection is based on whether the ``pcbnew`` C-extension module is
    importable.  Outside KiCad this import always fails; inside it succeeds
    because KiCad pre-loads the module into the interpreter.

    When this function returns ``True``:

    - Lock-file guards are not meaningful — KiCad holds the lock by design and
      the plugin has direct in-memory access to the latest project state.
    - ``kicad-cli`` subprocess fallbacks are unnecessary — native Python APIs
      are available.

    Returns:
        ``True`` if running inside KiCad, ``False`` otherwise.
    """
    try:
        import pcbnew  # noqa: F401

        return True
    except ImportError:
        return False


def check_write_permitted(
    project_context: "ProjectContext",
    *,
    dry_run: bool = False,
) -> None:
    """Guard schematic write operations against KiCad lock files.

    Call this once per write-capable command (e.g. ``jbom annotate``) *after*
    project resolution but *before* any filesystem writes.

    Behaviour matrix::

        Mode         | Locked? | dry_run | Outcome
        -------------|---------|---------|-----------------------------
        plugin       |  any    |  any    | no-op (in-memory access)
        CLI          |  no     |  any    | no-op
        CLI          |  yes    |  False  | raises PermissionError
        CLI          |  yes    |  True   | prints WARNING, continues

    Args:
        project_context: The resolved :class:`~jbom.services.project_context.ProjectContext`
            to inspect.
        dry_run: When ``True`` a warning is emitted instead of raising.

    Raises:
        PermissionError: If the project is locked and ``dry_run`` is ``False``.
    """
    # Plugin mode: KiCad holds the lock intentionally; bypass entirely.
    if is_running_inside_kicad():
        return

    if not project_context.is_locked:
        return

    lock_name = project_context.lock_file.name
    msg = (
        f"KiCad lock file detected ({lock_name}). "
        "The project appears to be open in KiCad. "
        "Unsaved KiCad edits will not be visible to jBOM, and jBOM writes "
        "may be overwritten when KiCad saves. "
        "Close KiCad before running this command, or use --dry-run to "
        "preview changes without writing."
    )

    if dry_run:
        print(f"WARNING: {msg}", file=sys.stderr)
    else:
        raise PermissionError(msg)
