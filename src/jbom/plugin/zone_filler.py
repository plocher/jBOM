"""Zone fill utility for the KiCad plugin.

Extracted from :mod:`jbom.plugin.dialog` for testability.  This module does
**not** import ``wx`` — ``pcbnew`` is lazy-imported inside
:func:`fill_zones_if_needed` so the module is safe to import in CLI/test
environments.

Only called from within KiCad's embedded Python interpreter at runtime.
"""

from __future__ import annotations

__all__ = ["fill_zones_if_needed"]


_TRACE_LOG = "/tmp/jbom_trace.log"


def _trace(label: str, board: object | None = None) -> None:  # pragma: no cover
    """Diagnostic trace — REMOVE before production."""
    modified = ""
    if board is not None:
        try:
            modified = f"  IsModified={board.IsModified()}"
        except Exception as exc:
            modified = f"  IsModified=ERR({exc})"
    msg = f"[jBOM-TRACE] {label}{modified}"
    print(msg, flush=True)
    try:
        with open(_TRACE_LOG, "a") as _f:
            _f.write(msg + "\n")
    except Exception:
        pass


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
            _trace("fill_zones_if_needed: no board")
            return False

        _trace("fill_zones_if_needed: entry", board)
        zones = list(board.Zones())
        _trace(f"fill_zones_if_needed: {len(zones)} zone(s) found", board)

        # Check each zone for stale/unfilled status
        for i, z in enumerate(zones):
            try:
                is_f = z.IsFilled()
                need_r = z.GetNeedRefill() if hasattr(z, "GetNeedRefill") else "N/A"
                _trace(f"  zone[{i}]: IsFilled={is_f}  GetNeedRefill={need_r}", board)
            except Exception as exc:
                _trace(f"  zone[{i}]: ERR({exc})", board)

        # Skip fill if all zones are already filled and not stale.
        # GetNeedRefill() was added in KiCad 7; guard for older builds.
        already_current = not zones or all(
            z.IsFilled() and (not hasattr(z, "GetNeedRefill") or not z.GetNeedRefill())
            for z in zones
        )
        if already_current:
            _trace("fill_zones_if_needed: all zones current — skipping Fill()", board)
            return False  # No-op: board state untouched

        # Zones need filling — fill then immediately save.
        _trace("fill_zones_if_needed: calling ZONE_FILLER.Fill()", board)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        _trace("fill_zones_if_needed: after ZONE_FILLER.Fill()", board)

        # Auto-save: keep source file in sync with filled state used for
        # Gerbers and backup.  Try pcbnew.SaveBoard() first (standard
        # KiCad 7+ API), fall back to board.Save() for older builds.
        if pcb_path:
            try:
                _trace(f"fill_zones_if_needed: calling SaveBoard('{pcb_path}')", board)
                pcbnew.SaveBoard(pcb_path, board)
                _trace("fill_zones_if_needed: after SaveBoard()", board)
            except Exception as exc:  # pragma: no cover
                _trace(
                    f"fill_zones_if_needed: SaveBoard failed ({exc}), trying board.Save()",
                    board,
                )
                try:
                    board.Save(pcb_path)
                    _trace("fill_zones_if_needed: after board.Save()", board)
                except Exception as exc2:  # pragma: no cover
                    _trace(
                        f"fill_zones_if_needed: board.Save() also failed ({exc2})",
                        board,
                    )
        else:
            _trace("fill_zones_if_needed: no pcb_path — skipping save", board)

        return True

    except Exception as exc:  # pragma: no cover
        _trace(f"fill_zones_if_needed: EXCEPTION {exc}")
        return False  # Non-fatal; caller proceeds with generation
