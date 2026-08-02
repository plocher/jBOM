"""Contract tests: jBOM JLC CPL vs Fabrication-Toolkit positions.

Requires local project files under Dropbox/KiCad/projects. Skipped when absent.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from jbom.application.pos_workflow import POSRequest, POSWorkflow

_CPNODE_PCB = Path(
    "/Users/jplocher/Dropbox/KiCad/projects/MRCS/cpNode-IOX/cpNode-IOX.kicad_pcb"
)
_CPNODE_FT = Path(
    "/Users/jplocher/Dropbox/KiCad/projects/MRCS/cpNode-IOX/production/"
    "cpNode-IOX_3.0A-FT_positions.csv"
)

# Known residual: barrel-jack pad geometry differs slightly from pcbnew
# GetBoundingBox centre used by FT (~0.6 mm X). Tracked with the parity suite.
_KNOWN_XY_RESIDUALS = {"J6"}


@pytest.mark.contract
class TestCpNodeIoxFTParity:
    """Full X/Y/Rotation parity for the board that opened issue #383."""

    @pytest.fixture(autouse=True)
    def skip_if_absent(self) -> None:
        if not _CPNODE_PCB.is_file() or not _CPNODE_FT.is_file():
            pytest.skip("cpNode-IOX PCB or FT golden positions.csv not found")

    def test_jlc_path_matches_ft_positions(self) -> None:
        ft: dict[str, tuple[float, float, float]] = {}
        with open(_CPNODE_FT, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                ft[row["Designator"]] = (
                    float(row["Mid X"]),
                    float(row["Mid Y"]),
                    float(row["Rotation"]),
                )

        result = POSWorkflow().run(
            POSRequest(
                input_path=str(_CPNODE_PCB),
                fabricator="jlc",
                smd_only=False,
            )
        )
        assert result.generation is not None
        rows = {r["reference"]: r for r in result.generation.pos_data}

        mismatches: list[str] = []
        for ref, (fx, fy, fr) in sorted(ft.items()):
            row = rows.get(ref)
            if row is None:
                mismatches.append(f"{ref}: missing from jBOM CPL")
                continue
            jx = float(row["x_mm"])
            jy = float(row["y_mm"])
            jr = float(row["rotation"])
            rot_ok = abs(((jr - fr + 180.0) % 360.0) - 180.0) < 0.1
            xy_ok = abs(jx - fx) < 0.05 and abs(jy - fy) < 0.05
            if ref in _KNOWN_XY_RESIDUALS:
                if not rot_ok:
                    mismatches.append(
                        f"{ref}: rotation jbom={jr:.3f} FT={fr:.3f} "
                        f"(known XY residual allowed)"
                    )
                continue
            if not (xy_ok and rot_ok):
                mismatches.append(
                    f"{ref}: jbom=({jx:.4f},{jy:.4f},{jr:.1f}) "
                    f"FT=({fx:.4f},{fy:.4f},{fr:.1f}) [{row.get('footprint')}]"
                )

        assert (
            not mismatches
        ), f"{len(mismatches)} CPL mismatch(es) vs FT golden:\n" + "\n".join(
            f"  {m}" for m in mismatches
        )
