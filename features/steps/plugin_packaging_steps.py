"""BDD steps for PCM plugin package icon/layout validation."""

from __future__ import annotations

import os
import struct
import subprocess
import zipfile
from pathlib import Path

from behave import then, when

from common_diagnostic_utils import assert_with_diagnostics


def _get_archive_path(context) -> Path:
    """Return the archive path captured by the build step."""
    archive = getattr(context, "plugin_archive", None)
    assert archive is not None, "plugin archive path not set on context"
    return Path(archive)


def _png_dimensions(png_bytes: bytes) -> tuple[int, int]:
    """Return (width, height) parsed from PNG IHDR."""
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    if png_bytes[12:16] != b"IHDR":
        raise ValueError("PNG missing IHDR header")
    return struct.unpack(">II", png_bytes[16:24])


@when("I build the PCM archive with skip binary fetch")
def step_build_pcm_archive_with_skip_binary_fetch(context) -> None:
    """Build a local PCM archive in the scenario sandbox."""
    output_dir = Path(context.sandbox_root) / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "python",
        "scripts/build_pcm_package.py",
        "--output-dir",
        str(output_dir),
        "--skip-binary-fetch",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(context.src_root)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=context.repo_root,
        env=env,
    )

    context.last_command = " ".join(command)
    context.last_output = result.stdout + result.stderr
    context.last_exit_code = result.returncode

    assert_with_diagnostics(
        result.returncode == 0,
        "PCM archive build failed",
        context,
        expected=0,
        actual=result.returncode,
    )

    archives = sorted(output_dir.glob("jbom-pcm-*.zip"))
    assert_with_diagnostics(
        len(archives) == 1,
        "Expected exactly one PCM archive output",
        context,
        expected=1,
        actual=len(archives),
    )
    context.plugin_archive = archives[0]


@then("the archive should include the required plugin packaging files")
def step_archive_contains_required_plugin_packaging_files(context) -> None:
    """Assert required KiCad plugin package layout entries are present."""
    required_entries = {
        "metadata.json",
        "plugins/__init__.py",
        "plugins/plugin.py",
        "plugins/assets/icons/pcb-fabrication-tool-light-24.png",
        "plugins/assets/icons/pcb-fabrication-tool-dark-24.png",
        "resources/icon.png",
    }

    archive = _get_archive_path(context)
    with zipfile.ZipFile(archive, "r") as archive_file:
        names = set(archive_file.namelist())

    missing = sorted(required_entries - names)
    assert_with_diagnostics(
        not missing,
        "Required plugin packaging files are missing from archive",
        context,
        expected=sorted(required_entries),
        actual=sorted(names),
    )


@then('"{archive_path}" in the archive should be a {width:d}x{height:d} PNG')
def step_archive_png_dimensions(
    context, archive_path: str, width: int, height: int
) -> None:
    """Assert a PNG entry inside the archive has exact dimensions."""
    archive = _get_archive_path(context)
    with zipfile.ZipFile(archive, "r") as archive_file:
        png_bytes = archive_file.read(archive_path)
    actual_width, actual_height = _png_dimensions(png_bytes)

    assert_with_diagnostics(
        (actual_width, actual_height) == (width, height),
        f"PNG dimensions mismatch for {archive_path}",
        context,
        expected=f"{width}x{height}",
        actual=f"{actual_width}x{actual_height}",
    )


@then('"{archive_path}" in the archive should contain text "{expected_text}"')
def step_archive_file_contains_text(
    context, archive_path: str, expected_text: str
) -> None:
    """Assert a text file entry inside the archive contains expected text."""
    archive = _get_archive_path(context)
    with zipfile.ZipFile(archive, "r") as archive_file:
        content = archive_file.read(archive_path).decode("utf-8")

    assert_with_diagnostics(
        expected_text in content,
        f"Expected text not found in archive entry {archive_path}",
        context,
        expected=expected_text,
        actual=content,
    )
