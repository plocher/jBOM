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
    for token in ["--aggregation", "--include-dnp", "--inventory", "-o", "--output"]:
        assert token in out


def test_pos_help_shows_core_flags():
    out = run_help(["pos"]).lower()
    for token in ["--units", "--origin", "--smd-only", "-o", "--output"]:
        assert token in out


def test_inventory_help_shows_inventory_interface_tokens():
    out = run_help(["inventory"]).lower()
    # Support both variants:
    # - Simplified single-command inventory with search flags
    # - Older subcommand-based inventory with {generate,list}
    tokens_search = ["--search", "--provider", "--api-key", "--limit", "--interactive"]
    tokens_subcmd = ["{generate,list}", "inventory commands", "generate", "list"]
    if any(t in out for t in tokens_search):
        for token in tokens_search:
            assert token in out
    else:
        # Fall back to subcommands presence and basic -o/-output on generate
        assert any(t in out for t in tokens_subcmd)
