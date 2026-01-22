import subprocess
import sys
from pathlib import Path

# Unit tests for CLI --help output. These are fast and stable, unlike Gherkin end-to-end.

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"


def run_help(args):
    env = dict(**os_environ_with_pythonpath())
    cmd = [sys.executable, "-m", "jbom.cli.main"] + args + ["--help"]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert res.returncode == 0, res.stderr or res.stdout
    return res.stdout + res.stderr


def os_environ_with_pythonpath():
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR)
    return env


def test_bom_help_includes_fabricator_choices():
    out = run_help(["bom"]).lower()
    # Stable tokens rather than brittle long strings
    assert "--fabricator" in out
    for fab in ["generic", "jlc", "pcbway", "seeed"]:
        assert fab in out


def test_bom_help_shows_key_options():
    out = run_help(["bom"]).lower()
    for token in ["--include-dnp", "--inventory", "-o", "--output"]:
        assert token in out


def test_pos_help_shows_core_flags():
    out = run_help(["pos"]).lower()
    for token in ["--units", "--origin", "--smd-only", "-o", "--output"]:
        assert token in out


def test_inventory_help_shows_inventory_interface_tokens():
    out = run_help(["inventory"]).lower()
    # Test current simplified interface with inventory matching flags
    tokens_current = ["--inventory", "--filter-matches", "-o", "--output"]
    for token in tokens_current:
        assert token in out
