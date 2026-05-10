"""Zone fill utility for the KiCad plugin.

Extracted from :mod:`jbom.plugin.dialog` for testability.  This module does
**not** import ``wx`` — ``pcbnew`` is lazy-imported inside
:func:`fill_zones_if_needed` so the module is safe to import in CLI/test
environments.

Only called from within KiCad's embedded Python interpreter at runtime.
"""

from __future__ import annotations

__all__ = ["fill_zones_if_needed"]


def fill_zones_if_needed(pcb_path: str) -> bool:
    """Fill board zones only if actually needed; auto-save when fill runs.

    Checks whether all zones are already filled and not stale before calling
    ``ZONE_FILLER.Fill()``.  If zones are already current the fill is skipped
    entirely — the board state is untouched and no dirty flag is set.

    If zones genuinely need filling, ``Fill()`` is called and the board file
    is saved to disk immediately so that the source file, generated Gerbers,
    and backup archive are all produced from the same consistent state.

    KiCad owns the dirty flag entirely; this function never reads or writes
    ``board.IsModified()``.

    Args:
        pcb_path: Filesystem path of the active PCB file, or empty string.
            When non-empty, ``pcbnew.SaveBoard()`` is called after fill so
            the disk file matches the in-memory filled state.

    Returns:
        ``True`` if ``ZONE_FILLER.Fill()`` was called (zones were stale).
        ``False`` if fill was skipped (zones already current) or if the board
        could not be obtained.
    """
    try:
        import pcbnew  # noqa: PLC0415 — only executed inside KiCad

        board = pcbnew.GetBoard()
        if not board:
            return False

        zones = list(board.Zones())

        # Skip fill if all zones are already filled and not stale.
        # GetNeedRefill() was added in KiCad 7; guard for older builds.
        already_current = not zones or all(
            z.IsFilled() and (not hasattr(z, "GetNeedRefill") or not z.GetNeedRefill())
            for z in zones
        )
        if already_current:
            return False  # No-op: board state untouched

        # Zones need filling — fill then immediately save.
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())

        # Auto-save: keep source file in sync with filled state used for
        # Gerbers and backup.  Try pcbnew.SaveBoard() first (standard
        # KiCad 7+ API), fall back to board.Save() for older builds.
        if pcb_path:
            try:
                pcbnew.SaveBoard(pcb_path, board)
            except Exception:  # pragma: no cover
                try:
                    board.Save(pcb_path)
                except Exception:  # pragma: no cover
                    pass  # Non-fatal: Gerbers still use filled in-memory board

        return True

    except Exception:  # pragma: no cover
        return False  # Non-fatal; caller proceeds with generation
