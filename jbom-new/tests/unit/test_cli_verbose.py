import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


def run_cmd(args, cwd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    cmd = [sys.executable, "-m", "jbom.cli.main"] + args
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)
    return res.returncode, res.stdout + res.stderr


def test_bom_verbose_emits_diagnostics_or_artifacts(tmp_path):
    # Create a minimal schematic via the project-centric steps equivalent
    sch = tmp_path / "project.kicad_sch"
    sch.write_text("(kicad_sch (version 20211123))\n", encoding="utf-8")
    pro = tmp_path / "project.kicad_pro"
    pro.write_text("(kicad_project (version 1))\n", encoding="utf-8")

    code, out = run_cmd(["bom", "-v"], cwd=tmp_path)
    assert code == 0
    # Robust assertion: either diagnostics or the artifact header is present
    assert (
        ("found schematic" in out)
        or ("Loading components from" in out)
        or ("References,Value,Footprint,Quantity" in out)
    )
