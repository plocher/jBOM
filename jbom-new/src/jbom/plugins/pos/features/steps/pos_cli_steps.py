"""Steps for POS CLI default behavior tests."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from behave import given, when, then


@given("I am in an empty project directory")
def step_in_empty_dir(context):
    # Create or clear a dedicated empty directory under the test temp dir
    base = getattr(context, "test_temp_dir", Path.cwd())
    context.project_dir = base / "empty_project"
    context.project_dir.mkdir(parents=True, exist_ok=True)
    for p in list(context.project_dir.iterdir()):
        if p.is_file():
            p.unlink()


@given("a KiCad project file exists in the project directory")
def step_create_project_file(context):
    # Create a .kicad_pro project file matching the project name
    proj = context.project_dir / f"{context.project_name}.kicad_pro"
    proj.write_text("(kicad_sch (version 20221018))\n")


@when('I run "{cmd}" in the project directory')
def step_run_cli(context, cmd):
    # Run the command capturing stdout/stderr without changing global cwd
    # Compute jbom-new/src by walking parents until a 'src/jbom' exists
    here = Path(__file__).resolve()
    py_path = None
    for p in here.parents:
        candidate = p / "src" / "jbom"
        if candidate.exists() and candidate.is_dir():
            py_path = str(p / "src")
            break
    env = dict(os.environ)
    if py_path:
        env["PYTHONPATH"] = py_path
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(context.project_dir),
        capture_output=True,
        text=True,
        env=env,
    )
    context.cli_returncode = proc.returncode
    context.cli_stdout = proc.stdout
    context.cli_stderr = proc.stderr


@then("the command exits with code {code:d}")
def step_assert_exit_code(context, code):
    assert getattr(context, "cli_returncode", None) == code, (
        f"Expected exit code {code}, got {getattr(context, 'cli_returncode', None)}\n"
        f"stderr: {getattr(context, 'cli_stderr', '')}"
    )


@then('stderr contains "{text}"')
def step_stderr_contains(context, text):
    assert text in getattr(context, "cli_stderr", ""), context.cli_stderr


@then('a file named "{name}" exists in the project directory')
def step_file_exists(context, name):
    path = context.project_dir / name
    assert path.exists() and path.is_file(), f"Expected file not found: {path}"
