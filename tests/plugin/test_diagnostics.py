"""Tests for ``jbom.plugin.diagnostics`` (wx-free)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from jbom.plugin import diagnostics as diag


@pytest.fixture(autouse=True)
def _reset_diagnostics_state() -> None:
    """Ensure each test sees a clean diagnostics module."""
    diag.clear_runs()
    diag.invalidate_environment()
    diag.invalidate_profile_snapshot()
    yield
    diag.clear_runs()
    diag.invalidate_environment()
    diag.invalidate_profile_snapshot()


# ---------------------------------------------------------------------------
# Environment snapshot
# ---------------------------------------------------------------------------


def test_environment_snapshot_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Repeated calls return the same instance until invalidated."""
    monkeypatch.delenv("JBOM_PLUGIN_BOOTSTRAP_INFO", raising=False)
    snap1 = diag.capture_environment()
    snap2 = diag.capture_environment()
    assert snap1 is snap2
    diag.invalidate_environment()
    snap3 = diag.capture_environment()
    assert snap3 is not snap1


def test_environment_reads_bootstrap_info_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When ``JBOM_PLUGIN_BOOTSTRAP_INFO`` is set, fields are populated from it."""
    info = {
        "mode": "pcm",
        "tag": "cp39-macosx_arm64",
        "this_dir": str(tmp_path),
        "src_dir": str(tmp_path.parent),
        "inserted": [str(tmp_path / "_vendor")],
    }
    monkeypatch.setenv("JBOM_PLUGIN_BOOTSTRAP_INFO", json.dumps(info))
    snap = diag.capture_environment(force=True)
    assert snap.mode == "pcm"
    assert snap.vendor_tag == "cp39-macosx_arm64"
    assert snap.source_path == str(tmp_path)
    assert snap.inserted_sys_path == (str(tmp_path / "_vendor"),)


def test_environment_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed bootstrap JSON does not raise; fields fall back to defaults."""
    monkeypatch.setenv("JBOM_PLUGIN_BOOTSTRAP_INFO", "not-json")
    snap = diag.capture_environment(force=True)
    assert snap.mode == "unknown"
    assert snap.vendor_tag is None


# ---------------------------------------------------------------------------
# Profile snapshot
# ---------------------------------------------------------------------------


def test_profile_snapshot_cached_by_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repeated calls without file changes return the cached snapshot."""
    monkeypatch.chdir(tmp_path)
    project_jbom = tmp_path / ".jbom"
    project_jbom.mkdir()
    (project_jbom / "jlc.jbom.yaml").write_text("fab:\n  name: JLC\n", encoding="utf-8")

    snap1 = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    snap2 = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    assert snap1 is snap2
    assert "jlc" in snap1.discovered_profiles
    # fab stanza should include jlc
    stanzas = dict(snap1.stanza_ids)
    assert "jlc" in stanzas["fab"]


def test_profile_snapshot_rebuilds_when_file_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editing a profile file invalidates the cached snapshot fingerprint."""
    monkeypatch.chdir(tmp_path)
    project_jbom = tmp_path / ".jbom"
    project_jbom.mkdir()
    target = project_jbom / "jlc.jbom.yaml"
    target.write_text("fab:\n  name: JLC\n", encoding="utf-8")

    snap1 = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    # Force a mtime change by writing different content with a bumped timestamp.
    target.write_text("fab:\n  name: JLC v2\n", encoding="utf-8")
    new_mtime = target.stat().st_mtime + 1.0
    os.utime(target, (new_mtime, new_mtime))
    snap2 = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    assert snap1.fingerprint != snap2.fingerprint


def test_profile_snapshot_renders_search_dirs_and_stanzas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rendered text exposes search dirs, stanzas, and the selected chain."""
    monkeypatch.chdir(tmp_path)
    project_jbom = tmp_path / ".jbom"
    project_jbom.mkdir()
    (project_jbom / "jlc.jbom.yaml").write_text(
        "extends: generic\nfab:\n  name: JLC\n", encoding="utf-8"
    )
    snap = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    text = diag.render_profiles(snap)
    assert "Search dirs:" in text
    assert "Stanzas:" in text
    assert "jlc" in text
    assert "Fingerprint:" in text


def test_profile_snapshot_classifies_project_and_factory_roles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project ``.jbom`` and the built-in profiles dir get role-tagged."""
    monkeypatch.chdir(tmp_path)
    project_jbom = tmp_path / ".jbom"
    project_jbom.mkdir()
    (project_jbom / "jlc.jbom.yaml").write_text("fab:\n  name: JLC\n", encoding="utf-8")
    snap = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    roles = {info.role for info in snap.search_dirs}
    assert "Project" in roles
    assert "Factory" in roles
    # The first chain entry is the named profile, role-tagged Project.
    assert snap.chain_entries[0] == ("Project", "jlc")


def test_profile_snapshot_chain_appends_common_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The chain enumerates extends ancestors then every ``common.jbom.yaml``."""
    monkeypatch.chdir(tmp_path)
    project_jbom = tmp_path / ".jbom"
    project_jbom.mkdir()
    (project_jbom / "common.jbom.yaml").write_text("defaults: {}\n", encoding="utf-8")
    (project_jbom / "jlc.jbom.yaml").write_text("fab:\n  name: JLC\n", encoding="utf-8")
    snap = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    # Named profile first, then the project's common.jbom.yaml.
    assert snap.chain_entries[0] == ("Project", "jlc")
    assert ("Project", "common") in snap.chain_entries
    text = diag.render_profiles(snap)
    assert "chain: Project:jlc \u2192 Project:common" in text


def test_profile_snapshot_chain_omits_unresolvable_extends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a profile extends a missing parent, the chain truncates cleanly."""
    monkeypatch.chdir(tmp_path)
    project_jbom = tmp_path / ".jbom"
    project_jbom.mkdir()
    (project_jbom / "jlc.jbom.yaml").write_text(
        "extends: nonexistent\nfab:\n  name: JLC\n", encoding="utf-8"
    )
    snap = diag.capture_profile_snapshot("jlc", cwd=tmp_path)
    names = [name for _role, name in snap.chain_entries if name != "common"]
    assert names == ["jlc"]


def test_lifecycle_records_events_in_active_run() -> None:
    """Events are appended to the active run; no run = no recording."""
    diag.record_event("ignored", "no active run")  # should not crash
    assert diag.get_runs() == ()

    diag.begin_run(pcb_path="/tmp/foo.kicad_pcb")
    diag.record_event("dialog", "open")
    diag.record_event("generate", "fab=jlc")
    diag.end_run()

    runs = diag.get_runs()
    assert len(runs) == 1
    run = runs[0]
    assert run.pcb_path == "/tmp/foo.kicad_pcb"
    assert run.ended_at is not None
    assert [e.stage for e in run.events] == ["dialog", "generate"]


def test_lifecycle_retains_multiple_runs() -> None:
    """Each begin_run() appends a new run; prior runs are retained."""
    diag.begin_run(pcb_path="/tmp/a.kicad_pcb")
    diag.record_event("dialog", "open")
    diag.end_run()

    diag.begin_run(pcb_path="/tmp/b.kicad_pcb")
    diag.record_event("dialog", "open")
    diag.end_run()

    runs = diag.get_runs()
    assert len(runs) == 2
    assert runs[0].pcb_path.endswith("a.kicad_pcb")
    assert runs[1].pcb_path.endswith("b.kicad_pcb")


def test_lifecycle_caps_retained_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Oldest runs are dropped when the retention cap is exceeded."""
    monkeypatch.setattr(diag, "_MAX_RETAINED_RUNS", 3)
    for index in range(5):
        diag.begin_run(pcb_path=f"/tmp/{index}.kicad_pcb")
        diag.end_run()
    runs = diag.get_runs()
    assert len(runs) == 3
    assert runs[0].pcb_path.endswith("2.kicad_pcb")
    assert runs[-1].pcb_path.endswith("4.kicad_pcb")


def test_render_lifecycle_handles_no_runs() -> None:
    """Empty run list renders a friendly placeholder string."""
    assert diag.render_lifecycle(()) == "(no runs recorded)"


def test_render_text_report_combines_all_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``render_text_report`` emits the three section headers."""
    monkeypatch.delenv("JBOM_PLUGIN_BOOTSTRAP_INFO", raising=False)
    env = diag.capture_environment(force=True)

    diag.begin_run(pcb_path="/tmp/x.kicad_pcb")
    diag.record_event("dialog", "open")
    diag.end_run()

    report = diag.render_text_report(env, None, diag.get_runs())
    assert "=== Environment ===" in report
    assert "=== Profile subsystem ===" in report
    assert "=== Lifecycle ===" in report
    assert "/tmp/x.kicad_pcb" in report
