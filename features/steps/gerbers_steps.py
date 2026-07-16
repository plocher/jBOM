"""Step definitions for features/gerbers/ BDD scenarios.

Covers:
- mock kicad-cli PATH injection
- jbom gerbers output assertions (file count, layer names, extensions, content)
- jbom fab production/ directory structure assertions
- zip archive content assertions (gerber zip + backup zip)
"""

from __future__ import annotations
from fnmatch import fnmatch

import os
import shutil
import stat
import zipfile
from pathlib import Path

from behave import given, then
from common_diagnostic_utils import assert_with_diagnostics


# ---------------------------------------------------------------------------
# Given: mock kicad-cli injection
# ---------------------------------------------------------------------------


@given("mock kicad-cli is available")
def step_mock_kicad_cli_available(context) -> None:
    """Install the mock kicad-cli fixture and prepend its directory to PATH.

    Copies ``features/fixtures/mock_kicad_cli/kicad-cli`` into the scenario
    sandbox, makes it executable, then records a PATH override in
    ``context.mock_env`` so that ``step_run_command`` passes it to every
    subsequent subprocess.  The mock is found before any real kicad-cli on the
    host system.

    The mock generates structurally valid Gerber X2 stub files whose layer list
    is driven by the ``--layers`` argument jBOM constructs from the fabricator
    config — not hardcoded here.
    """
    fixture_src = (
        Path(context.repo_root)
        / "features"
        / "fixtures"
        / "mock_kicad_cli"
        / "kicad-cli"
    )
    assert fixture_src.exists(), f"mock kicad-cli fixture not found: {fixture_src}"

    mock_bin = Path(context.sandbox_root) / "mock_bin"
    mock_bin.mkdir(exist_ok=True)

    dst = mock_bin / "kicad-cli"
    shutil.copy2(fixture_src, dst)
    # Ensure executable bit is set (copytree may not preserve it on all OSes)
    dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # Prepend mock_bin to PATH so GerberExporter._find_kicad_cli() finds it first.
    # env.update() in step_run_command applies this to every subsequent subprocess.
    existing_path = os.environ.get("PATH", "")
    context.mock_env = {"PATH": f"{mock_bin}:{existing_path}"}


# ---------------------------------------------------------------------------
# Then: file existence helpers (sandbox-root-relative)
# ---------------------------------------------------------------------------


@then('"{rel_path}" should exist in the sandbox')
def step_rel_path_exists(context, rel_path: str) -> None:
    """Assert a path relative to the sandbox root exists (file or directory)."""
    target = Path(context.sandbox_root) / rel_path
    assert_with_diagnostics(
        target.exists(),
        f"Expected path does not exist: {rel_path}",
        context,
        expected=f"exists: {rel_path}",
        actual=f"not found: {target}",
    )


@then('"{rel_path}" should not exist in the sandbox')
def step_rel_path_not_exists(context, rel_path: str) -> None:
    """Assert a path relative to the sandbox root does NOT exist."""
    target = Path(context.sandbox_root) / rel_path
    assert_with_diagnostics(
        not target.exists(),
        f"Path should not exist but does: {rel_path}",
        context,
        expected=f"absent: {rel_path}",
        actual=f"found: {target}",
    )


# ---------------------------------------------------------------------------
# Then: gerber output directory assertions
# ---------------------------------------------------------------------------


@then("the gerbers output directory should contain {count:d} gerber files")
def step_gerbers_dir_file_count(context, count: int) -> None:
    """Assert the gerbers/ subdirectory contains exactly *count* Gerber files.

    Counts only files — not drill maps (.gbr map files are counted separately).
    """
    gerbers_dir = Path(context.sandbox_root) / "gerbers"
    assert_with_diagnostics(
        gerbers_dir.is_dir(),
        "gerbers/ output directory does not exist",
        context,
        expected="gerbers/ directory exists",
        actual=f"not found: {gerbers_dir}",
    )
    # Count all files (Gerber + drill); the count the scenario specifies
    # should match the total produced by the mock for the chosen fabricator.
    files = [f for f in gerbers_dir.iterdir() if f.is_file()]
    assert_with_diagnostics(
        len(files) == count,
        f"Expected {count} file(s) in gerbers/, found {len(files)}",
        context,
        expected=f"{count} files",
        actual=f"{len(files)} files: {[f.name for f in sorted(files)]}",
    )


@then('a gerber file for layer "{layer}" should exist')
def step_gerber_file_for_layer_exists(context, layer: str) -> None:
    """Assert that a Gerber file whose name contains the layer name exists.

    Layer names use KiCad dot notation (e.g. ``F.Cu``); the file will have
    underscores (``project-F_Cu.gtl``).  The check matches on the safe name
    (dots replaced with underscores) anywhere in the output directory.
    """
    gerbers_dir = Path(context.sandbox_root) / "gerbers"
    safe = layer.replace(".", "_")
    matches = list(gerbers_dir.glob(f"*-{safe}.*")) if gerbers_dir.is_dir() else []
    assert_with_diagnostics(
        len(matches) > 0,
        f"No gerber file found for layer '{layer}' (looking for *-{safe}.*)",
        context,
        expected=f"file matching *-{safe}.*",
        actual=(
            f"files present: {[f.name for f in sorted(gerbers_dir.iterdir())]}"
            if gerbers_dir.is_dir()
            else "directory absent"
        ),
    )


@then('the gerber file for layer "{layer}" should use extension ".{ext}"')
def step_gerber_extension(context, layer: str, ext: str) -> None:
    """Assert the Gerber file for *layer* carries the expected Protel extension."""
    gerbers_dir = Path(context.sandbox_root) / "gerbers"
    safe = layer.replace(".", "_")
    matches = list(gerbers_dir.glob(f"*-{safe}.*")) if gerbers_dir.is_dir() else []
    assert_with_diagnostics(
        len(matches) > 0,
        f"No gerber file found for layer '{layer}'",
        context,
        expected=f"*-{safe}.{ext}",
        actual="no file found",
    )
    actual_ext = matches[0].suffix.lstrip(".")
    assert_with_diagnostics(
        actual_ext == ext,
        f"Layer '{layer}' file has wrong extension: expected .{ext}, got .{actual_ext}",
        context,
        expected=f".{ext}",
        actual=f".{actual_ext} ({matches[0].name})",
    )


@then('the gerber file for layer "{layer}" should contain "{text}"')
def step_gerber_content(context, layer: str, text: str) -> None:
    """Assert the Gerber stub for *layer* contains *text* (e.g. a TF attribute)."""
    gerbers_dir = Path(context.sandbox_root) / "gerbers"
    safe = layer.replace(".", "_")
    matches = list(gerbers_dir.glob(f"*-{safe}.*")) if gerbers_dir.is_dir() else []
    assert len(matches) > 0, f"No gerber file found for layer '{layer}'"
    content = matches[0].read_text(encoding="utf-8")
    assert_with_diagnostics(
        text in content,
        f"Text '{text}' not found in gerber file for layer '{layer}'",
        context,
        expected=text,
        actual=content[:400],
    )


@then("a drill file should exist in the gerbers output directory")
def step_drill_file_exists(context) -> None:
    """Assert at least one .drl drill file exists in gerbers/."""
    gerbers_dir = Path(context.sandbox_root) / "gerbers"
    drills = list(gerbers_dir.glob("*.drl")) if gerbers_dir.is_dir() else []
    assert_with_diagnostics(
        len(drills) > 0,
        "No .drl file found in gerbers/ directory",
        context,
        expected="at least one .drl file",
        actual=f"files: {[f.name for f in sorted(gerbers_dir.iterdir())] if gerbers_dir.is_dir() else 'directory absent'}",
    )


# ---------------------------------------------------------------------------
# Then: production/ directory structure (jbom fab)
# ---------------------------------------------------------------------------


@then("the production directory should exist")
def step_production_dir_exists(context) -> None:
    prod = Path(context.sandbox_root) / "production"
    assert_with_diagnostics(
        prod.is_dir(),
        "production/ directory not found",
        context,
        expected="production/ exists",
        actual=f"contents of sandbox: {[p.name for p in sorted(Path(context.sandbox_root).iterdir())]}",
    )


@then('the production artifact "{filename}" should exist')
def step_production_artifact_exists(context, filename: str) -> None:
    """Assert a named file exists directly inside production/."""
    target = Path(context.sandbox_root) / "production" / filename
    assert_with_diagnostics(
        target.exists(),
        f"Production artifact '{filename}' not found",
        context,
        expected=f"production/{filename}",
        actual=_list_production(context),
    )


@then('no file matching "{glob_pattern}" should exist in production/')
def step_no_production_match(context, glob_pattern: str) -> None:
    """Assert no file matching *glob_pattern* exists in production/."""
    prod = Path(context.sandbox_root) / "production"
    matches = list(prod.glob(glob_pattern)) if prod.is_dir() else []
    assert_with_diagnostics(
        len(matches) == 0,
        f"Unexpected file(s) matching '{glob_pattern}' found in production/",
        context,
        expected="no matches",
        actual=f"found: {[m.name for m in matches]}",
    )


@then('a gerber zip matching "{glob_pattern}" should exist in production/')
def step_gerber_zip_exists(context, glob_pattern: str) -> None:
    """Assert a zip file matching *glob_pattern* exists in production/."""
    prod = Path(context.sandbox_root) / "production"
    matches = list(prod.glob(glob_pattern)) if prod.is_dir() else []
    assert_with_diagnostics(
        len(matches) > 0,
        f"No file matching '{glob_pattern}' found in production/",
        context,
        expected=f"at least one match for '{glob_pattern}'",
        actual=_list_production(context),
    )


@then('a backup zip should exist under "production/backups/"')
def step_backup_zip_exists(context) -> None:
    """Assert at least one .zip exists in production/backups/."""
    backups = Path(context.sandbox_root) / "production" / "backups"
    zips = list(backups.glob("*.zip")) if backups.is_dir() else []
    assert_with_diagnostics(
        len(zips) > 0,
        "No backup zip found in production/backups/",
        context,
        expected="at least one .zip in production/backups/",
        actual=_list_production(context),
    )


# ---------------------------------------------------------------------------
# Then: zip content assertions
# ---------------------------------------------------------------------------


@then("the gerber zip should contain {count:d} files")
def step_gerber_zip_entry_count(context, count: int) -> None:
    """Assert the gerber zip in production/ has exactly *count* entries."""
    zips = list((Path(context.sandbox_root) / "production").glob("*.zip"))
    # Exclude backup zips (they live under backups/)
    zips = [z for z in zips if z.parent.name == "production"]
    assert (
        len(zips) == 1
    ), f"Expected exactly one gerber zip, found: {[z.name for z in zips]}"
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    assert_with_diagnostics(
        len(names) == count,
        f"Gerber zip should contain {count} file(s), found {len(names)}",
        context,
        expected=f"{count} entries",
        actual=f"{len(names)} entries: {sorted(names)}",
    )


@then('the gerber zip should contain a file for layer "{layer}"')
def step_gerber_zip_has_layer(context, layer: str) -> None:
    """Assert the gerber zip contains a file whose name includes the layer."""
    zips = [
        z
        for z in (Path(context.sandbox_root) / "production").glob("*.zip")
        if z.parent.name == "production"
    ]
    assert len(zips) >= 1, "No gerber zip found in production/"
    safe = layer.replace(".", "_")
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    matches = [n for n in names if f"-{safe}." in n or f"_{safe}." in n]
    assert_with_diagnostics(
        len(matches) > 0,
        f"Gerber zip contains no file for layer '{layer}'",
        context,
        expected=f"entry containing '{safe}'",
        actual=f"zip entries: {sorted(names)}",
    )


@then("the backup zip should contain {count:d} files")
def step_backup_zip_entry_count(context, count: int) -> None:
    """Assert the backup zip has exactly *count* entries."""
    backups = Path(context.sandbox_root) / "production" / "backups"
    zips = list(backups.glob("*.zip")) if backups.is_dir() else []
    assert len(zips) >= 1, "No backup zip found in production/backups/"
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    assert_with_diagnostics(
        len(names) == count,
        f"Backup zip should contain {count} file(s), found {len(names)}",
        context,
        expected=f"{count} entries",
        actual=f"{len(names)} entries: {sorted(names)}",
    )


@then('the backup zip should contain an entry matching "{glob_pattern}"')
def step_backup_zip_contains_matching_entry(context, glob_pattern: str) -> None:
    """Assert the backup zip contains at least one matching entry name."""
    backups = Path(context.sandbox_root) / "production" / "backups"
    zips = list(backups.glob("*.zip")) if backups.is_dir() else []
    assert len(zips) >= 1, "No backup zip found in production/backups/"
    with zipfile.ZipFile(zips[0]) as zf:
        names = zf.namelist()
    matches = [n for n in names if fnmatch(n, glob_pattern)]
    assert_with_diagnostics(
        len(matches) > 0,
        f"Backup zip contains no entry matching '{glob_pattern}'",
        context,
        expected=f"entry matching '{glob_pattern}'",
        actual=f"entries: {sorted(names)}",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_production(context) -> str:
    """Return a diagnostic string listing production/ contents (recursive)."""
    prod = Path(context.sandbox_root) / "production"
    if not prod.is_dir():
        return "production/ directory absent"
    lines = []
    for p in sorted(prod.rglob("*")):
        lines.append(str(p.relative_to(context.sandbox_root)))
    return (
        "production/ contents:\n  " + "\n  ".join(lines)
        if lines
        else "production/ is empty"
    )
