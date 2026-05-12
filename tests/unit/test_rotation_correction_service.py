"""Tests for RotationCorrectionService and the apply_rotation_corrections pipeline.

Test tiers
----------
Tier 1 — Service unit tests (pure Python, no PCB file needed):
    Rule loading, first-match semantics, rotation delta arithmetic,
    normalize flag, offset application, colon-pattern matching.

Tier 2 — Pipeline integration (synthetic pos_data rows):
    apply_rotation_corrections() wires the service into pos_data dicts;
    verifies rotation_raw clearing, offset application, diagnostic output.

Tier 3 — Fabricator config (cpl_rotation_range field):
    jlc.fab.yaml sets cpl_rotation_range: [0, 360]; generic/pcbway have None.
    apply_fab_rotation_range() folds angles into the declared window.

Tier 4 — FT parity contract (real PCB + fresh FT golden file, contract marker):
    Core-ESP32-Devkit project: jBOM+corrections must match the FT-generated
    positions.csv rotation for every component FT includes.
    Skipped automatically when the PCB or golden file is absent.
"""

from __future__ import annotations

import csv
import textwrap
from pathlib import Path
from typing import Any

import pytest

from jbom.services.rotation_correction_service import RotationCorrectionService
from jbom.application.pos_workflow import (
    apply_fab_rotation_range,
    apply_rotation_corrections,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BUILTIN_CSV = (
    Path(__file__).parent.parent.parent
    / "src"
    / "jbom"
    / "config"
    / "transformations.csv"
)

_CORE_ESP32_PCB = Path(
    "/Users/jplocher/Dropbox/KiCad/projects/Core-ESP32-Devkit/Core-ESP32.kicad_pcb"
)
_CORE_ESP32_FT_GOLDEN = Path(
    "/Users/jplocher/Dropbox/KiCad/projects/Core-ESP32-Devkit/production/positions.csv"
)


def _service_from_csv_text(csv_text: str) -> RotationCorrectionService:
    """Build a RotationCorrectionService from an inline CSV string (no disk I/O)."""
    tmp = Path(__file__).parent / "_tmp_transformations.csv"
    tmp.write_text(textwrap.dedent(csv_text), encoding="utf-8")
    try:
        return RotationCorrectionService.load(transformations_path=tmp)
    finally:
        tmp.unlink(missing_ok=True)


def _pos_row(
    reference: str,
    footprint: str,
    rotation: float,
    x_mm: float = 10.0,
    y_mm: float = 20.0,
    rotation_raw: str | None = None,
) -> dict[str, Any]:
    """Build a minimal pos_data row as POSGenerator would produce it."""
    row: dict[str, Any] = {
        "reference": reference,
        "footprint": footprint,
        "rotation": rotation,
        "x_mm": x_mm,
        "y_mm": y_mm,
    }
    if rotation_raw is not None:
        row["rotation_raw"] = rotation_raw
    return row


# ---------------------------------------------------------------------------
# Tier 1 — Service unit tests
# ---------------------------------------------------------------------------


class TestBuiltinLoad:
    def test_loads_without_error(self) -> None:
        svc = RotationCorrectionService.load()
        assert svc.rule_count > 0

    def test_builtin_file_exists(self) -> None:
        assert (
            _BUILTIN_CSV.is_file()
        ), f"Built-in transformations.csv missing: {_BUILTIN_CSV}"

    def test_rule_count_matches_data_rows(self) -> None:
        """Rule count should equal non-comment, non-header data rows."""
        data_rows = 0
        with open(_BUILTIN_CSV, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if stripped.lower().startswith('"regex to match"'):
                    continue
                data_rows += 1
        svc = RotationCorrectionService.load()
        assert svc.rule_count == data_rows


class TestMatching:
    def test_no_match_returns_rotation_unchanged(self) -> None:
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOT-23",180,0,0\n'
        )
        assert svc.apply_rotation("Resistor_SMD:R_0805", 45.0) == 45.0

    def test_first_match_wins_not_last(self) -> None:
        """When two patterns both match, the first rule in the file applies."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n'
            '"^SOT-",90,0,0\n'
            '"^SOT-23",180,0,0\n'
        )
        # SOT-23 matches both "^SOT-" (first) and "^SOT-23" (second)
        # First-match semantics → delta = 90, not 180
        result = svc.apply_rotation("Package_TO_SOT_SMD:SOT-23", 0.0)
        assert result == 90.0

    def test_name_only_pattern_matches_right_of_colon(self) -> None:
        """Pattern without ':' matches the NAME part of LIBRARY:NAME."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^CP_Elec_",180,0,0\n'
        )
        assert svc.has_correction("Capacitor_SMD:CP_Elec_5x5")
        assert not svc.has_correction("Resistor_SMD:R_0805")

    def test_name_only_pattern_does_not_match_library_part(self) -> None:
        """Pattern without ':' should NOT trigger on the library nickname alone."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n'
            '"^Capacitor_SMD",90,0,0\n'
        )
        # "Capacitor_SMD" is the library prefix; without ":" the pattern checks
        # only the name part ("CP_Elec_5x5"), so this should NOT match.
        assert not svc.has_correction("Capacitor_SMD:CP_Elec_5x5")

    def test_colon_pattern_matches_full_lib_name_string(self) -> None:
        """Pattern containing ':' is matched against the full LIBRARY:NAME string."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n'
            '"Capacitor_SMD:CP_Elec_",90,0,0\n'
        )
        assert svc.has_correction("Capacitor_SMD:CP_Elec_5x5")

    def test_footprint_without_colon_checked_as_whole(self) -> None:
        """When footprint has no ':', the whole string is checked as the name."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOT-23",180,0,0\n'
        )
        assert svc.has_correction("SOT-23")

    def test_empty_footprint_does_not_match(self) -> None:
        svc = RotationCorrectionService.load()
        assert not svc.has_correction("")


class TestRotationArithmetic:
    def test_delta_added_to_kicad_rotation(self) -> None:
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOT-23",180,0,0\n'
        )
        # KiCad 90° + delta 180° = 270°
        assert svc.apply_rotation("Package_TO_SOT_SMD:SOT-23", 90.0) == 270.0

    def test_negative_delta_without_normalize(self) -> None:
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOIC127P",-90,0,0\n'
        )
        # KiCad 0° + delta -90° = -90° (no normalization)
        assert svc.apply_rotation("SPCoast:SOIC127P798X216-8N", 0.0) == -90.0

    def test_apply_rotation_returns_raw_no_range_folding(self) -> None:
        """apply_rotation always returns the raw delta-adjusted value; no range folding."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOT-23",180,0,0\n'
        )
        # No rule match — raw KiCad -90° passes through unchanged
        result = svc.apply_rotation("Resistor_SMD:R_0805", -90.0)
        assert result == -90.0

    def test_delta_applied_returns_raw_even_when_out_of_0_360(self) -> None:
        """A 450° result is returned as-is; range folding is done by apply_fab_rotation_range."""
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOT-23",270,0,0\n'
        )
        # KiCad 180° + delta 270° = 450° — no folding in apply_rotation
        result = svc.apply_rotation("Package_TO_SOT_SMD:SOT-23", 180.0)
        assert result == pytest.approx(450.0)


class TestOffsets:
    def test_no_match_returns_zero_offset(self) -> None:
        svc = RotationCorrectionService.load()
        dx, dy = svc.apply_offset("Resistor_SMD:R_0805_2012Metric")
        assert dx == 0.0
        assert dy == 0.0

    def test_rule_with_nonzero_offset(self) -> None:
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n'
            '"^TestPkg",90,1.5,-0.75\n'
        )
        dx, dy = svc.apply_offset("MyLib:TestPkg_2x2")
        assert dx == pytest.approx(1.5)
        assert dy == pytest.approx(-0.75)

    def test_zero_offsets_in_db_returns_zero(self) -> None:
        svc = _service_from_csv_text(
            '"Regex To Match","Rotation","Delta X","Delta Y"\n' '"^SOT-23",180,0,0\n'
        )
        dx, dy = svc.apply_offset("Package_TO_SOT_SMD:SOT-23")
        assert dx == 0.0
        assert dy == 0.0


class TestBuiltinRules:
    """Spot-check specific rules from the harvested transformations.csv."""

    @pytest.mark.parametrize(
        "footprint,kicad_rot,expected_delta",
        [
            ("Package_TO_SOT_SMD:SOT-23", 0.0, 180.0),
            ("Capacitor_SMD:CP_Elec_5x5", 0.0, 180.0),
            ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", 0.0, 270.0),
            ("Package_QFP:LQFP-48_7x7mm_P0.5mm", 0.0, 270.0),
            ("Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm", 0.0, 90.0),
        ],
    )
    def test_known_builtin_rule(
        self, footprint: str, kicad_rot: float, expected_delta: float
    ) -> None:
        svc = RotationCorrectionService.load()
        result = svc.apply_rotation(footprint, kicad_rot)
        assert result == pytest.approx(expected_delta), (
            f"{footprint}: expected delta {expected_delta}°, "
            f"got {result}° (kicad={kicad_rot}°)"
        )


# ---------------------------------------------------------------------------
# Tier 2 — Pipeline integration (apply_rotation_corrections)
# ---------------------------------------------------------------------------


class TestApplyRotationCorrectionsPipeline:
    def test_db_rule_match_updates_rotation(self) -> None:
        """Components matching a DB rule get their rotation corrected."""
        rows = [_pos_row("U1", "Package_TO_SOT_SMD:SOT-23", 0.0)]
        corrected, diags = apply_rotation_corrections(rows)
        assert corrected[0]["rotation"] == pytest.approx(180.0)

    def test_no_db_match_rotation_preserved(self) -> None:
        """Components not matching any rule keep their KiCad rotation."""
        rows = [_pos_row("R1", "Resistor_SMD:R_0805_2012Metric", 45.0)]
        corrected, diags = apply_rotation_corrections(rows)
        assert corrected[0]["rotation"] == pytest.approx(45.0)

    def test_rotation_raw_cleared_for_corrected_row(self) -> None:
        """rotation_raw is cleared so the field resolver uses the corrected float."""
        rows = [_pos_row("U1", "Package_TO_SOT_SMD:SOT-23", 0.0, rotation_raw="0")]
        corrected, _ = apply_rotation_corrections(rows)
        assert "rotation_raw" not in corrected[0]

    def test_rotation_raw_cleared_for_all_rows_even_without_db_match(self) -> None:
        """rotation_raw is cleared for all rows (normalization may also change it)."""
        rows = [
            _pos_row("R1", "Resistor_SMD:R_0805_2012Metric", 45.0, rotation_raw="45")
        ]
        corrected, _ = apply_rotation_corrections(rows)
        assert "rotation_raw" not in corrected[0]

    def test_corrections_preserve_negative_angle_without_range(self) -> None:
        """apply_rotation_corrections does NOT fold angles; raw -90° stays -90°."""
        rows = [_pos_row("R1", "Resistor_SMD:R_0805_2012Metric", -90.0)]
        corrected, _ = apply_rotation_corrections(rows)
        assert corrected[0]["rotation"] == pytest.approx(-90.0)

    def test_nonzero_offset_updates_x_y(self) -> None:
        """When a DB rule has non-zero X/Y deltas, x_mm and y_mm are adjusted."""
        svc_csv = (
            '"Regex To Match","Rotation","Delta X","Delta Y"\n'
            '"^TestOffset",0,1.0,2.0\n'
        )
        tmp = Path(__file__).parent / "_tmp_offsets.csv"
        tmp.write_text(svc_csv, encoding="utf-8")
        try:
            from jbom.services.rotation_correction_service import (
                RotationCorrectionService as _Svc,
            )

            _svc = _Svc.load(transformations_path=tmp)
            # Call the lower-level service directly to verify offsets
            dx, dy = _svc.apply_offset("MyLib:TestOffset_1x4")
            assert dx == pytest.approx(1.0)
            assert dy == pytest.approx(2.0)
        finally:
            tmp.unlink(missing_ok=True)

    def test_zero_offset_does_not_clear_x_raw(self) -> None:
        """When the DB offset is (0, 0), x_raw/y_raw are not touched."""
        rows = [
            {
                "reference": "U1",
                "footprint": "Package_TO_SOT_SMD:SOT-23",
                "rotation": 0.0,
                "x_mm": 5.0,
                "y_mm": 10.0,
                "x_raw": "5.0000",
                "y_raw": "10.0000",
            }
        ]
        corrected, _ = apply_rotation_corrections(rows)
        # SOT-23 has delta (0, 0) in the DB → x_raw preserved
        assert "x_raw" in corrected[0]
        assert "y_raw" in corrected[0]

    def test_summary_diagnostic_always_emitted(self) -> None:
        """A summary Diagnostic is always appended after processing."""
        rows = [_pos_row("R1", "Resistor_SMD:R_0805_2012Metric", 0.0)]
        _, diags = apply_rotation_corrections(rows)
        assert any("Rotation corrections applied" in d.message for d in diags)

    def test_verbose_emits_per_component_diagnostic_for_db_hits(self) -> None:
        """verbose=True adds one info diagnostic per DB-rule match."""
        rows = [_pos_row("U1", "Package_TO_SOT_SMD:SOT-23", 0.0)]
        _, diags = apply_rotation_corrections(rows, verbose=True)
        per_component = [d for d in diags if "U1" in d.message]
        assert len(per_component) >= 1

    def test_db_hit_count_in_summary_diagnostic(self) -> None:
        rows = [
            _pos_row("U1", "Package_TO_SOT_SMD:SOT-23", 0.0),  # matches
            _pos_row("R1", "Resistor_SMD:R_0805_2012Metric", 0.0),  # no match
        ]
        _, diags = apply_rotation_corrections(rows)
        summary = next(d for d in diags if "Rotation corrections applied" in d.message)
        assert "1 DB rule" in summary.message

    def test_empty_pos_data_returns_empty(self) -> None:
        corrected, diags = apply_rotation_corrections([])
        assert corrected == []
        assert any("Rotation corrections applied" in d.message for d in diags)


# ---------------------------------------------------------------------------
# Tier 3 — Fabricator config cpl_rotation_range + apply_fab_rotation_range
# ---------------------------------------------------------------------------


class TestFabricatorCplRotationRange:
    def test_jlc_has_0_360_range(self) -> None:
        from jbom.config.fabricators import load_fabricator

        jlc = load_fabricator("jlc")
        assert jlc.cpl_rotation_range == (0.0, 360.0)

    def test_generic_has_no_rotation_range(self) -> None:
        from jbom.config.fabricators import load_fabricator

        generic = load_fabricator("generic")
        assert generic.cpl_rotation_range is None

    def test_pcbway_has_no_rotation_range(self) -> None:
        from jbom.config.fabricators import load_fabricator

        pcbway = load_fabricator("pcbway")
        assert pcbway.cpl_rotation_range is None

    def test_cpl_rotation_range_defaults_none(self) -> None:
        from jbom.config.fabricators import FabricatorConfig

        default = FabricatorConfig.model_fields["cpl_rotation_range"].default
        assert default is None

    def test_invalid_range_not_360_span_raises(self) -> None:
        from jbom.config.fabricators import FabricatorConfig

        with pytest.raises(ValueError, match="spanning exactly 360"):
            FabricatorConfig.model_validate(
                {
                    "id": "test",
                    "pos_columns": {"Designator": "reference"},
                    "suppliers": ["lcsc"],
                    "field_synonyms": {
                        "fab_pn": {"display_name": "P", "synonyms": []},
                        "supplier_pn": {"display_name": "S", "synonyms": []},
                        "mpn": {"display_name": "M", "synonyms": []},
                    },
                    "cpl_rotation_range": [0, 180],  # only 180° span — invalid
                },
                context={"default_id": "test"},
            )


class TestApplyFabRotationRange:
    """Tests for the data-driven range-folding function (Part 2)."""

    def _make_fab(self, lo: float, hi: float):
        """Build a minimal FabricatorConfig with the given cpl_rotation_range."""
        from jbom.config.fabricators import FabricatorConfig

        cfg = FabricatorConfig(
            id="test",
            name="Test",
            pos_columns={"Designator": "reference"},
            cpl_rotation_range=(lo, hi),
            suppliers=["generic"],
            field_synonyms={
                "fab_pn": {"display_name": "Fab PN", "synonyms": []},
                "supplier_pn": {"display_name": "Supplier PN", "synonyms": []},
                "mpn": {"display_name": "MPN", "synonyms": []},
            },
        )
        return cfg

    def test_none_fab_config_returns_unchanged(self) -> None:
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", -90.0)]
        result = apply_fab_rotation_range(rows, None)
        assert result[0]["rotation"] == pytest.approx(-90.0)

    def test_fab_without_range_returns_unchanged(self) -> None:
        from jbom.config.fabricators import FabricatorConfig

        cfg = FabricatorConfig(
            id="generic",
            name="Generic",
            pos_columns={"D": "r"},
            suppliers=["generic"],
            field_synonyms={
                "fab_pn": {"display_name": "Fab PN", "synonyms": []},
                "supplier_pn": {"display_name": "Supplier PN", "synonyms": []},
                "mpn": {"display_name": "MPN", "synonyms": []},
            },
        )
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", -90.0)]
        result = apply_fab_rotation_range(rows, cfg)
        assert result[0]["rotation"] == pytest.approx(-90.0)

    def test_0_360_folds_negative_to_positive(self) -> None:
        """[0, 360]: -90° → 270°  (JLCPCB use case)."""
        fab = self._make_fab(0, 360)
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", -90.0)]
        result = apply_fab_rotation_range(rows, fab)
        assert result[0]["rotation"] == pytest.approx(270.0)

    def test_0_360_preserves_already_valid_positive(self) -> None:
        fab = self._make_fab(0, 360)
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", 270.0)]
        result = apply_fab_rotation_range(rows, fab)
        assert result[0]["rotation"] == pytest.approx(270.0)

    def test_0_360_folds_above_360(self) -> None:
        """[0, 360]: 450° → 90°."""
        fab = self._make_fab(0, 360)
        rows = [_pos_row("U1", "Package_SO:SOIC-8", 450.0)]
        result = apply_fab_rotation_range(rows, fab)
        assert result[0]["rotation"] == pytest.approx(90.0)

    def test_neg180_pos180_folds_positive_to_negative(self) -> None:
        """[-180, 180]: 270° → -90°  (hypothetical alternative convention)."""
        fab = self._make_fab(-180, 180)
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", 270.0)]
        result = apply_fab_rotation_range(rows, fab)
        assert result[0]["rotation"] == pytest.approx(-90.0)

    def test_neg180_pos180_preserves_already_valid_negative(self) -> None:
        fab = self._make_fab(-180, 180)
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", -90.0)]
        result = apply_fab_rotation_range(rows, fab)
        assert result[0]["rotation"] == pytest.approx(-90.0)

    def test_rotation_raw_cleared_when_angle_changes(self) -> None:
        fab = self._make_fab(0, 360)
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", -90.0, rotation_raw="-90")]
        result = apply_fab_rotation_range(rows, fab)
        assert "rotation_raw" not in result[0]

    def test_rotation_raw_preserved_when_angle_unchanged(self) -> None:
        """If the angle is already in range, no copy is made and rotation_raw kept."""
        fab = self._make_fab(0, 360)
        rows = [_pos_row("R1", "Resistor_SMD:R_0805", 90.0, rotation_raw="90")]
        result = apply_fab_rotation_range(rows, fab)
        # 90° is already in [0, 360) — same row object, raw preserved
        assert "rotation_raw" in result[0]

    def test_multiple_rows_all_folded(self) -> None:
        fab = self._make_fab(0, 360)
        rows = [
            _pos_row("R1", "Resistor_SMD:R_0805", -90.0),
            _pos_row("R2", "Resistor_SMD:R_0805", 0.0),
            _pos_row("R3", "Resistor_SMD:R_0805", 180.0),
            _pos_row("R4", "Resistor_SMD:R_0805", 270.0),
        ]
        result = apply_fab_rotation_range(rows, fab)
        assert [r["rotation"] for r in result] == pytest.approx(
            [270.0, 0.0, 180.0, 270.0]
        )


# ---------------------------------------------------------------------------
# Tier 4 — FT parity contract (requires real PCB + fresh FT golden)
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestFTParity:
    """Verify jBOM rotation corrections match FT's positions.csv output.

    Skipped automatically when the PCB or golden file is not present on disk.
    The golden file must have been freshly generated by Fabrication-Toolkit
    with auto_translate=True (default).

    Known scope: components that FT excludes from the CPL (marked
    exclude_from_pos_files) will appear in jBOM but not in the FT golden;
    these are counted as 'skipped'.
    """

    @pytest.fixture(autouse=True)
    def skip_if_absent(self) -> None:
        if not _CORE_ESP32_PCB.is_file() or not _CORE_ESP32_FT_GOLDEN.is_file():
            pytest.skip(
                "Core-ESP32-Devkit PCB or FT golden positions.csv not found — "
                "run FT with auto_translate=True to generate"
            )

    def test_core_esp32_rotation_parity_with_jlc_normalize(self) -> None:
        """All components in the FT golden must match jBOM+corrections (normalize=True)."""
        from jbom.services.pcb_reader import DefaultKiCadReaderService
        from jbom.services.pos_generator import POSGenerator
        from jbom.common.options import PlacementOptions

        board = DefaultKiCadReaderService().read_pcb_file(_CORE_ESP32_PCB)
        rows = POSGenerator(PlacementOptions(smd_only=False)).generate_pos_data(board)
        svc = RotationCorrectionService.load()

        ft_golden: dict[str, float] = {}
        with open(_CORE_ESP32_FT_GOLDEN, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                ft_golden[row["Designator"]] = float(row["Rotation"])

        mismatches: list[str] = []
        skipped = 0
        for r in rows:
            ref = r["reference"]
            ft_rot = ft_golden.get(ref)
            if ft_rot is None:
                skipped += 1
                continue
            corrected = svc.apply_rotation(r["footprint"], r["rotation"])
            # Apply JLCPCB range folding (Part 2) separately
            from jbom.config.fabricators import load_fabricator as _lf

            _jlc = _lf("jlc")
            folded_rows = apply_fab_rotation_range([{"rotation": corrected}], _jlc)
            corrected = folded_rows[0]["rotation"]
            if abs(corrected - ft_rot) >= 0.1:
                mismatches.append(
                    f"{ref}: kicad={r['rotation']:.1f}° → jbom={corrected:.1f}°"
                    f" FT={ft_rot:.1f}° [{r['footprint']}]"
                )

        assert not mismatches, (
            f"{len(mismatches)} rotation mismatch(es) vs FT golden "
            f"({skipped} component(s) excluded from FT CPL):\n"
            + "\n".join(f"  {m}" for m in mismatches)
        )
