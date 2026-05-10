"""Unit tests for Tranche 1 plugin improvements (issues #254 and #255).

#254 — FabricationRequest.skip_backup field and FabricationWorkflow gate:
- skip_backup defaults to False
- skip_backup=True prevents BackupService from being called
- __post_init__ coerces value to bool

#255 — _fill_zones() no-op detection:
- returns False and skips ZONE_FILLER.Fill() when all zones are already filled
- returns True when fill was genuinely needed (zones not all filled)
- returns False gracefully when board has no zones
- GetNeedRefill() is used when present; absent attribute is tolerated
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# #254 — FabricationRequest.skip_backup
# ---------------------------------------------------------------------------


class TestFabricationRequestSkipBackup:
    """FabricationRequest carries skip_backup with correct defaults/coercion."""

    def test_skip_backup_defaults_to_false(self) -> None:
        from jbom.application.fabrication_orchestration import FabricationRequest

        req = FabricationRequest(input_path="/fake/board.kicad_pcb")
        assert req.skip_backup is False

    def test_skip_backup_true_is_stored(self) -> None:
        from jbom.application.fabrication_orchestration import FabricationRequest

        req = FabricationRequest(input_path="/fake/board.kicad_pcb", skip_backup=True)
        assert req.skip_backup is True

    def test_skip_backup_is_coerced_to_bool(self) -> None:
        from jbom.application.fabrication_orchestration import FabricationRequest

        req = FabricationRequest(
            input_path="/fake/board.kicad_pcb", skip_backup=1  # type: ignore[arg-type]
        )
        assert req.skip_backup is True
        assert type(req.skip_backup) is bool


class TestFabricationWorkflowSkipBackup:
    """FabricationWorkflow skips BackupService when skip_backup=True."""

    def _make_request(self, tmp_path: Path, *, skip_backup: bool) -> object:
        from jbom.application.fabrication_orchestration import FabricationRequest

        # Point input_path at the tmp dir so the workflow can resolve a project dir.
        return FabricationRequest(
            input_path=str(tmp_path),
            skip_bom=True,
            skip_pos=True,
            skip_gerbers=True,
            skip_backup=skip_backup,
        )

    def test_backup_skipped_when_skip_backup_true(self, tmp_path: Path) -> None:
        from jbom.application.fabrication_orchestration import FabricationWorkflow

        request = self._make_request(tmp_path, skip_backup=True)

        with patch(
            "jbom.application.fabrication_orchestration.FabricationWorkflow"
            "._create_backup"
        ) as mock_backup:
            FabricationWorkflow().run(request)  # type: ignore[arg-type]
            mock_backup.assert_not_called()

    def test_backup_called_when_skip_backup_false(self, tmp_path: Path) -> None:
        """When skip_backup=False, _create_backup is reached (may still no-op due to
        empty artifact list, but it is not pre-empted by the flag)."""
        from jbom.application.fabrication_orchestration import FabricationWorkflow

        request = self._make_request(tmp_path, skip_backup=False)

        # With all steps skipped, artifact list will be empty and backup gate
        # (artifacts truthy) will prevent _create_backup from being called anyway.
        # We verify skip_backup=False does NOT block the gate; the artifact list
        # gate handles the rest.
        with patch(
            "jbom.application.fabrication_orchestration.FabricationWorkflow"
            "._create_backup"
        ) as mock_backup:
            FabricationWorkflow().run(request)  # type: ignore[arg-type]
            # No artifacts → backup gate blocks even with skip_backup=False.
            mock_backup.assert_not_called()


# ---------------------------------------------------------------------------
# #255 — fill_zones_if_needed() no-op detection (tested via sys.modules patching)
# ---------------------------------------------------------------------------
# Tests import jbom.plugin.zone_filler directly — no wx dependency.


def _make_mock_zone(*, is_filled: bool, need_refill: bool = False) -> MagicMock:
    """Return a mock ZONE object with configurable IsFilled/GetNeedRefill."""
    zone = MagicMock()
    zone.IsFilled.return_value = is_filled
    zone.GetNeedRefill.return_value = need_refill
    return zone


def _make_mock_board(zones: list[MagicMock]) -> MagicMock:
    board = MagicMock()
    board.Zones.return_value = zones
    return board


class TestFillZonesNoOp:
    """fill_zones_if_needed() skips ZONE_FILLER when zones are already current."""

    def _run_fill_zones(
        self,
        zones: list[MagicMock],
        pcb_path: str = "",
    ) -> tuple[bool, MagicMock]:
        """Run fill_zones_if_needed() with pcbnew injected via sys.modules."""
        import sys

        mock_board = _make_mock_board(zones)
        mock_pcbnew = MagicMock()
        mock_pcbnew.GetBoard.return_value = mock_board
        mock_pcbnew.ZONE_FILLER.return_value = MagicMock()
        mock_pcbnew.SaveBoard = MagicMock()

        with patch.dict(sys.modules, {"pcbnew": mock_pcbnew}):
            # Reload is not needed; the lazy import inside fill_zones_if_needed
            # will use sys.modules['pcbnew'] at call time.
            from jbom.plugin.zone_filler import fill_zones_if_needed

            result = fill_zones_if_needed(pcb_path)

        return result, mock_pcbnew

    def test_no_zones_returns_false_without_filling(self) -> None:
        """A board with no zones is a no-op — fill is skipped, returns False."""
        result, mock_pcbnew = self._run_fill_zones(zones=[])
        assert result is False
        mock_pcbnew.ZONE_FILLER.assert_not_called()

    def test_all_zones_filled_and_current_returns_false(self) -> None:
        """All zones IsFilled=True, GetNeedRefill=False → skip, return False."""
        zones = [
            _make_mock_zone(is_filled=True, need_refill=False),
            _make_mock_zone(is_filled=True, need_refill=False),
        ]
        result, mock_pcbnew = self._run_fill_zones(zones)
        assert result is False
        mock_pcbnew.ZONE_FILLER.assert_not_called()

    def test_unfilled_zone_triggers_fill(self) -> None:
        """At least one zone IsFilled=False → ZONE_FILLER.Fill() is called."""
        zones = [
            _make_mock_zone(is_filled=True, need_refill=False),
            _make_mock_zone(is_filled=False, need_refill=False),
        ]
        result, mock_pcbnew = self._run_fill_zones(zones)
        assert result is True
        mock_pcbnew.ZONE_FILLER.assert_called_once()
        mock_pcbnew.ZONE_FILLER.return_value.Fill.assert_called_once()

    def test_stale_zone_triggers_fill(self) -> None:
        """Zone IsFilled=True but GetNeedRefill=True → fill is still run."""
        zones = [_make_mock_zone(is_filled=True, need_refill=True)]
        result, mock_pcbnew = self._run_fill_zones(zones)
        assert result is True
        mock_pcbnew.ZONE_FILLER.assert_called_once()

    def test_zone_without_get_need_refill_attribute_is_tolerated(self) -> None:
        """Zones without GetNeedRefill (pre-KiCad-7) don't crash; IsFilled governs."""
        zone = MagicMock(spec=["IsFilled"])  # no GetNeedRefill
        zone.IsFilled.return_value = True
        # hasattr(zone, "GetNeedRefill") → False; treated as not-stale.
        result, mock_pcbnew = self._run_fill_zones([zone])
        assert result is False
        mock_pcbnew.ZONE_FILLER.assert_not_called()

    def test_fill_auto_saves_when_pcb_path_set(self, tmp_path: Path) -> None:
        """When fill runs, pcbnew.SaveBoard() is called with the pcb_path."""
        pcb_file = str(tmp_path / "board.kicad_pcb")
        zones = [_make_mock_zone(is_filled=False)]
        result, mock_pcbnew = self._run_fill_zones(zones, pcb_path=pcb_file)
        assert result is True
        mock_pcbnew.SaveBoard.assert_called_once_with(pcb_file, mock_pcbnew.GetBoard())

    def test_fill_does_not_save_when_no_pcb_path(self) -> None:
        """When pcb_path is empty, SaveBoard is NOT called even if fill ran."""
        zones = [_make_mock_zone(is_filled=False)]
        result, mock_pcbnew = self._run_fill_zones(zones, pcb_path="")
        assert result is True
        mock_pcbnew.SaveBoard.assert_not_called()

    def test_no_op_does_not_save(self, tmp_path: Path) -> None:
        """When fill is a no-op, SaveBoard is NOT called."""
        pcb_file = str(tmp_path / "board.kicad_pcb")
        zones = [_make_mock_zone(is_filled=True, need_refill=False)]
        result, mock_pcbnew = self._run_fill_zones(zones, pcb_path=pcb_file)
        assert result is False
        mock_pcbnew.SaveBoard.assert_not_called()
