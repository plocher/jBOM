"""Integration tests for multi-project batch inventory.

Verifies the acceptance criteria from issue #144:
  - jbom inventory proj1 proj2 proj3 -o combined.csv produces merged COMPONENT
    rows deduplicated on ComponentID
  - All existing single-project behaviour unchanged

Uses mocked SchematicReader and ProjectFileResolver so no real KiCad files
are required.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

from jbom.cli.main import main
from jbom.common.types import Component


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_component(
    reference: str,
    value: str,
    footprint: str = "R_0603_1608Metric",
    lib_id: str = "Device:R",
    uuid: str | None = None,
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        uuid=uuid or f"uuid-{reference}",
        properties={},
        in_bom=True,
        exclude_from_sim=False,
        dnp=False,
    )


def _make_resolved_input(schematic_path: Path, project_name: str):
    """Build a minimal mock ResolvedInput for a schematic path."""
    mock = MagicMock()
    mock.is_schematic = True
    mock.resolved_path = schematic_path
    mock.project_context = MagicMock()
    mock.project_context.project_base_name = project_name
    mock.project_context.project_directory = schematic_path.parent
    mock.get_hierarchical_files.return_value = [schematic_path]
    return mock


# ---------------------------------------------------------------------------
# Acceptance test: multi-project inventory deduplication
# ---------------------------------------------------------------------------


class TestMultiProjectInventoryAcceptance:
    """Acceptance criteria: jbom inventory p1 p2 -o combined.csv"""

    def test_merged_output_deduplicated_on_component_id(self, tmp_path):
        """
        Given two projects each containing a 10K/0603 resistor and project B
        also having a unique 100nF capacitor, the combined inventory should
        contain exactly one resistor row and one capacitor row.
        """
        sch_a = tmp_path / "projA" / "projA.kicad_sch"
        sch_b = tmp_path / "projB" / "projB.kicad_sch"
        sch_a.parent.mkdir(parents=True)
        sch_b.parent.mkdir(parents=True)
        sch_a.write_text("")
        sch_b.write_text("")

        output_csv = tmp_path / "combined.csv"

        # projA: 10K resistor
        comps_a = [_make_component("R1", "10K")]
        # projB: same 10K resistor + a unique 100nF capacitor
        comps_b = [
            _make_component("R1", "10K"),
            _make_component(
                "C1", "100nF", footprint="C_0603_1608Metric", lib_id="Device:C"
            ),
        ]

        resolved_a = _make_resolved_input(sch_a, "projA")
        resolved_b = _make_resolved_input(sch_b, "projB")

        with (
            patch("jbom.cli.inventory.ProjectFileResolver") as mock_resolver_cls,
            patch("jbom.cli.inventory.SchematicReader") as mock_reader_cls,
        ):
            mock_resolver = MagicMock()
            mock_resolver.resolve_input.side_effect = [resolved_a, resolved_b]
            mock_resolver_cls.return_value = mock_resolver

            mock_reader = MagicMock()
            mock_reader.load_components.side_effect = [comps_a, comps_b]
            mock_reader_cls.return_value = mock_reader

            result = main(
                [
                    "inventory",
                    str(sch_a.parent),
                    str(sch_b.parent),
                    "-o",
                    str(output_csv),
                    "--force",
                ]
            )

        assert result == 0, "Command should succeed"
        assert output_csv.exists(), "Output file should be created"

        rows = list(csv.DictReader(output_csv.open()))

        # Resistor should appear exactly once (deduplicated)
        resistor_rows = [r for r in rows if "RES" in r.get("ComponentID", "")]
        cap_rows = [r for r in rows if "CAP" in r.get("ComponentID", "")]

        assert (
            len(resistor_rows) == 1
        ), f"Resistor should appear exactly once, got {len(resistor_rows)}: {resistor_rows}"
        assert (
            len(cap_rows) == 1
        ), f"Capacitor should appear exactly once, got {len(cap_rows)}"

    def test_three_projects_combined(self, tmp_path):
        """Three projects with overlapping and unique parts are correctly merged."""
        projects = []
        schematics = []
        for name in ["A", "B", "C"]:
            sch = tmp_path / name / f"{name}.kicad_sch"
            sch.parent.mkdir()
            sch.write_text("")
            projects.append(name)
            schematics.append(sch)

        output_csv = tmp_path / "combined.csv"

        # A: 10K, 100nF (2 unique)
        # B: 10K (dup), 4k7 (new)
        # C: 100nF (dup), 10uF (new)
        comps = [
            [
                _make_component("R1", "10K"),
                _make_component("C1", "100nF", lib_id="Device:C", footprint="C_0603"),
            ],
            [_make_component("R1", "10K"), _make_component("R2", "4k7")],
            [
                _make_component("C1", "100nF", lib_id="Device:C", footprint="C_0603"),
                _make_component("C2", "10uF", lib_id="Device:C", footprint="C_0805"),
            ],
        ]

        resolved = [_make_resolved_input(s, p) for s, p in zip(schematics, projects)]

        with (
            patch("jbom.cli.inventory.ProjectFileResolver") as mock_resolver_cls,
            patch("jbom.cli.inventory.SchematicReader") as mock_reader_cls,
        ):
            mock_resolver = MagicMock()
            mock_resolver.resolve_input.side_effect = resolved
            mock_resolver_cls.return_value = mock_resolver

            mock_reader = MagicMock()
            mock_reader.load_components.side_effect = comps
            mock_reader_cls.return_value = mock_reader

            result = main(
                [
                    "inventory",
                    str(schematics[0].parent),
                    str(schematics[1].parent),
                    str(schematics[2].parent),
                    "-o",
                    str(output_csv),
                    "--force",
                ]
            )

        assert result == 0
        rows = list(csv.DictReader(output_csv.open()))
        # 4 unique parts total: 10K, 100nF, 4k7, 10uF
        assert len(rows) == 4, (
            f"Expected 4 unique component rows, got {len(rows)}: "
            f"{[r.get('ComponentID', r.get('Value', '?')) for r in rows]}"
        )


# ---------------------------------------------------------------------------
# Backward compatibility: single-project behaviour unchanged
# ---------------------------------------------------------------------------


class TestSingleProjectBackwardCompat:
    """Single-project invocations must behave exactly as before."""

    def test_single_project_still_works(self, tmp_path):
        sch = tmp_path / "myproj" / "myproj.kicad_sch"
        sch.parent.mkdir()
        sch.write_text("")
        output_csv = tmp_path / "out.csv"

        comps = [
            _make_component("R1", "10K"),
            _make_component("C1", "100nF", lib_id="Device:C"),
        ]
        resolved = _make_resolved_input(sch, "myproj")

        with (
            patch("jbom.cli.inventory.ProjectFileResolver") as mock_resolver_cls,
            patch("jbom.cli.inventory.SchematicReader") as mock_reader_cls,
        ):
            mock_resolver = MagicMock()
            mock_resolver.resolve_input.return_value = resolved
            mock_resolver_cls.return_value = mock_resolver

            mock_reader = MagicMock()
            mock_reader.load_components.return_value = comps
            mock_reader_cls.return_value = mock_reader

            result = main(
                [
                    "inventory",
                    str(sch.parent),
                    "-o",
                    str(output_csv),
                    "--force",
                ]
            )

        assert result == 0
        assert output_csv.exists()
        rows = list(csv.DictReader(output_csv.open()))
        assert len(rows) == 2  # R1 and C1 as separate component types

    def test_no_args_defaults_to_current_dir(self):
        """jbom inventory with no args should attempt current directory (single-project path)."""
        # We just verify routing — _handle_generate_inventory will naturally fail
        # in a test environment with no kicad project in CWD, but the KEY assertion
        # is that _handle_batch_inventory is NOT called.
        with patch("jbom.cli.inventory._handle_batch_inventory") as mock_batch:
            with patch("jbom.cli.inventory._handle_generate_inventory") as mock_single:
                mock_single.return_value = 0
                main(["inventory"])
        mock_single.assert_called_once_with(".", mock_single.call_args[0][1])
        mock_batch.assert_not_called()


# ---------------------------------------------------------------------------
# --stop-on-error flag
# ---------------------------------------------------------------------------


class TestStopOnError:
    def test_stop_on_error_returns_failure_when_project_fails(self, tmp_path):
        """With --stop-on-error, a failing first project causes non-zero exit."""
        output_csv = tmp_path / "out.csv"

        with patch("jbom.cli.inventory.ProjectFileResolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver.resolve_input.side_effect = Exception("Cannot find schematic")
            mock_resolver_cls.return_value = mock_resolver

            result = main(
                [
                    "inventory",
                    "bad_project_1",
                    "bad_project_2",
                    "--stop-on-error",
                    "-o",
                    str(output_csv),
                ]
            )

        assert result == 1

    def test_continue_on_error_default_succeeds_with_partial_results(self, tmp_path):
        """Without --stop-on-error, good projects still produce output despite bad ones."""
        sch_good = tmp_path / "good" / "good.kicad_sch"
        sch_good.parent.mkdir()
        sch_good.write_text("")
        output_csv = tmp_path / "out.csv"

        comps_good = [_make_component("R1", "10K")]
        resolved_good = _make_resolved_input(sch_good, "good")

        resolve_calls = [Exception("bad project"), resolved_good]

        with (
            patch("jbom.cli.inventory.ProjectFileResolver") as mock_resolver_cls,
            patch("jbom.cli.inventory.SchematicReader") as mock_reader_cls,
        ):
            mock_resolver = MagicMock()
            mock_resolver.resolve_input.side_effect = resolve_calls
            mock_resolver_cls.return_value = mock_resolver

            mock_reader = MagicMock()
            mock_reader.load_components.return_value = comps_good
            mock_reader_cls.return_value = mock_reader

            result = main(
                [
                    "inventory",
                    "bad_project",
                    str(sch_good.parent),
                    "-o",
                    str(output_csv),
                    "--force",
                ]
            )

        assert result == 0, "Should succeed when at least one project produces output"
        assert output_csv.exists()
