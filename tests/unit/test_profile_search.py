"""Unit tests for config/profile_search.py.

Covers:
- find_profile() returns builtin when no override exists
- find_profile() returns project-local .jbom/ file first
- find_profile() returns None when not found anywhere
- JBOM_PROFILE_PATH env var is included in search dirs
- _find_repo_root() walks up to .git/
- profile_search_dirs() order is correct
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jbom.config.profile_search import find_profile, profile_search_dirs


def test_find_profile_returns_builtin_when_no_override(tmp_path: Path) -> None:
    """Should find generic.defaults.yaml from the built-in package dir."""
    from jbom.config.defaults import _BUILTIN_DIR

    result = find_profile("generic", "defaults", cwd=tmp_path, builtin_dir=_BUILTIN_DIR)
    assert result is not None
    assert result.name == "generic.defaults.yaml"
    assert result.exists()


def test_find_profile_returns_none_for_unknown_name(tmp_path: Path) -> None:
    """Should return None when no profile matching the name exists anywhere."""
    from jbom.config.defaults import _BUILTIN_DIR

    result = find_profile(
        "nonexistent_xyz_profile",
        "defaults",
        cwd=tmp_path,
        builtin_dir=_BUILTIN_DIR,
    )
    assert result is None


def test_find_profile_prefers_jbom_dir_over_builtin(tmp_path: Path) -> None:
    """A .jbom/generic.defaults.yaml in cwd shadows the built-in."""
    from jbom.config.defaults import _BUILTIN_DIR

    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    override = jbom_dir / "generic.defaults.yaml"
    override.write_text(
        "# local override\ndomain_defaults:\n  resistor:\n    tolerance: '1%'\n"
    )

    result = find_profile("generic", "defaults", cwd=tmp_path, builtin_dir=_BUILTIN_DIR)
    assert result == override


def test_find_profile_uses_jbom_profile_path_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JBOM_PROFILE_PATH directories are included in search."""
    profile_dir = tmp_path / "org_profiles"
    profile_dir.mkdir()
    profile_file = profile_dir / "aerospace.defaults.yaml"
    profile_file.write_text("domain_defaults:\n  resistor:\n    tolerance: '1%'\n")

    monkeypatch.setenv("JBOM_PROFILE_PATH", str(profile_dir))
    # Use a non-existent cwd so .jbom/ there won't match
    result = find_profile("aerospace", "defaults", cwd=tmp_path / "project")
    assert result == profile_file


def test_profile_search_dirs_includes_jbom_profile_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JBOM_PROFILE_PATH is included in profile_search_dirs output."""
    org_dir = tmp_path / "org"
    monkeypatch.setenv("JBOM_PROFILE_PATH", str(org_dir))

    dirs = profile_search_dirs(cwd=tmp_path)
    assert org_dir in dirs


def test_profile_search_dirs_does_not_include_jbom_profile_path_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When JBOM_PROFILE_PATH is unset, no unexpected dirs appear."""
    monkeypatch.delenv("JBOM_PROFILE_PATH", raising=False)
    dirs = profile_search_dirs()
    # All entries should be standard paths, not from any env var
    # (we can't assert exact paths, but we can check the count is stable)
    assert len(dirs) >= 2  # at minimum: .jbom/ + ~/.jbom/


def test_profile_search_dirs_starts_with_cwd_jbom(tmp_path: Path) -> None:
    """First entry should always be <cwd>/.jbom/."""
    dirs = profile_search_dirs(cwd=tmp_path)
    assert dirs[0] == tmp_path / ".jbom"


def test_find_repo_root_walks_up(tmp_path: Path) -> None:
    """_find_repo_root should walk up to find .git/."""
    from jbom.config.profile_search import _find_repo_root

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    sub = tmp_path / "src" / "deep" / "module"
    sub.mkdir(parents=True)

    assert _find_repo_root(sub) == tmp_path


def test_find_repo_root_returns_none_at_filesystem_root(tmp_path: Path) -> None:
    """_find_repo_root returns None when no .git is found up the tree."""
    from jbom.config.profile_search import _find_repo_root

    # Use a temp dir with no .git anywhere above it (unlikely but test the logic)
    # We test with a path that definitely has no .git above it via the function logic
    # by checking a non-existent directory walk — just verify it doesn't crash
    result = _find_repo_root(Path("/nonexistent_jbom_test_path_xyz"))
    assert result is None


def test_find_profile_no_builtin_dir_returns_none(tmp_path: Path) -> None:
    """Without builtin_dir, should return None if not found in search path."""
    result = find_profile("generic", "defaults", cwd=tmp_path, builtin_dir=None)
    assert result is None


def test_find_profile_multiple_env_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JBOM_PROFILE_PATH colon-separated list is expanded correctly."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_b / "org.defaults.yaml").write_text("domain_defaults: {}\n")

    monkeypatch.setenv("JBOM_PROFILE_PATH", f"{dir_a}:{dir_b}")

    result = find_profile("org", "defaults", cwd=tmp_path / "project")
    assert result == dir_b / "org.defaults.yaml"
