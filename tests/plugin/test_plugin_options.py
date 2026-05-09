"""Unit tests for ``jbom.plugin.options``.

Covers:
- ``PluginOptions`` default values and field types
- ``PluginOptions.to_dict()`` / ``PluginOptions.from_dict()`` round-trip
- ``from_dict`` robustness: extra keys, empty fabricator fallback
- ``_find_git_root()`` with real and fake directories
- ``_options_file()`` path resolution (git root vs. home fallback)
- ``load_options()`` / ``save_options()`` filesystem round-trip
- ``load_options()`` graceful degradation on malformed JSON
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from jbom.plugin.options import (
    PluginOptions,
    _find_git_root,
    _options_file,
    load_options,
    save_options,
)


# ---------------------------------------------------------------------------
# PluginOptions dataclass
# ---------------------------------------------------------------------------


class TestPluginOptionsDefaults:
    def test_default_fabricator_is_jlc(self) -> None:
        opts = PluginOptions()
        assert opts.fabricator == "jlc"

    def test_default_inventory_path_is_empty(self) -> None:
        opts = PluginOptions()
        assert opts.inventory_path == ""

    def test_custom_values_are_stored(self) -> None:
        opts = PluginOptions(fabricator="pcbway", inventory_path="/tmp/inv.csv")
        assert opts.fabricator == "pcbway"
        assert opts.inventory_path == "/tmp/inv.csv"


class TestPluginOptionsSerialization:
    def test_to_dict_contains_expected_keys(self) -> None:
        opts = PluginOptions(fabricator="seeed", inventory_path="/a/b.csv")
        d = opts.to_dict()
        assert d == {"fabricator": "seeed", "inventory_path": "/a/b.csv"}

    def test_round_trip_via_dict(self) -> None:
        original = PluginOptions(fabricator="jlc", inventory_path="/inv/parts.csv")
        restored = PluginOptions.from_dict(original.to_dict())
        assert restored == original

    def test_from_dict_ignores_extra_keys(self) -> None:
        data = {
            "fabricator": "pcbway",
            "inventory_path": "",
            "unknown_future_field": 42,
        }
        opts = PluginOptions.from_dict(data)
        assert opts.fabricator == "pcbway"
        assert opts.inventory_path == ""

    def test_from_dict_empty_fabricator_falls_back_to_jlc(self) -> None:
        data = {"fabricator": "", "inventory_path": ""}
        opts = PluginOptions.from_dict(data)
        assert opts.fabricator == "jlc"

    def test_from_dict_whitespace_fabricator_falls_back_to_jlc(self) -> None:
        data = {"fabricator": "   ", "inventory_path": ""}
        opts = PluginOptions.from_dict(data)
        assert opts.fabricator == "jlc"

    def test_from_dict_missing_keys_use_defaults(self) -> None:
        opts = PluginOptions.from_dict({})
        assert opts.fabricator == "jlc"
        assert opts.inventory_path == ""

    def test_round_trip_through_json(self) -> None:
        original = PluginOptions(fabricator="generic", inventory_path="/x/y.xlsx")
        json_str = json.dumps(original.to_dict())
        restored = PluginOptions.from_dict(json.loads(json_str))
        assert restored == original


# ---------------------------------------------------------------------------
# _find_git_root
# ---------------------------------------------------------------------------


class TestFindGitRoot:
    def test_returns_path_inside_real_repo(self, tmp_path: Path) -> None:
        """jBOM is a real git repo; running from any subdir should find root."""
        # Use the test file's own directory — guaranteed to be in a git repo.
        result = _find_git_root(Path(__file__).parent)
        assert result is not None
        assert result.is_dir()
        assert (result / ".git").exists()

    def test_returns_none_outside_any_repo(self, tmp_path: Path) -> None:
        """A freshly created temp dir is not a git repo."""
        result = _find_git_root(tmp_path)
        assert result is None

    def test_returns_none_when_git_not_available(self, tmp_path: Path) -> None:
        """Handles the case where the ``git`` binary cannot be found."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = _find_git_root(tmp_path)
        assert result is None

    def test_returns_none_on_timeout(self, tmp_path: Path) -> None:
        """Handles timeout gracefully."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            result = _find_git_root(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# _options_file
# ---------------------------------------------------------------------------


class TestOptionsFile:
    def test_returns_path_under_git_root_when_in_repo(self, tmp_path: Path) -> None:
        """When inside a git repo, options file lives at $git_root/.jbom/."""
        fake_root = tmp_path / "myrepo"
        fake_root.mkdir()
        with patch("jbom.plugin.options._find_git_root", return_value=fake_root):
            path = _options_file(fake_root / "myboard.kicad_pcb")
        assert path == fake_root / ".jbom" / "jbom-options.json"

    def test_returns_path_under_home_when_no_git_root(self, tmp_path: Path) -> None:
        """When outside a git repo, options file falls back to ~/.jbom/."""
        with patch("jbom.plugin.options._find_git_root", return_value=None):
            path = _options_file(tmp_path / "board.kicad_pcb")
        assert path == Path.home() / ".jbom" / "jbom-options.json"

    def test_accepts_directory_as_project_path(self, tmp_path: Path) -> None:
        """A directory path (not a file) should resolve without error."""
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            path = _options_file(project_dir)
        assert path == tmp_path / ".jbom" / "jbom-options.json"


# ---------------------------------------------------------------------------
# load_options / save_options round-trip
# ---------------------------------------------------------------------------


class TestLoadSaveRoundTrip:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        opts = PluginOptions(fabricator="jlc", inventory_path="/inv/parts.csv")
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            save_options(opts, tmp_path)
        expected = tmp_path / ".jbom" / "jbom-options.json"
        assert expected.is_file()

    def test_save_creates_parent_dir(self, tmp_path: Path) -> None:
        opts = PluginOptions()
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            save_options(opts, tmp_path)
        assert (tmp_path / ".jbom").is_dir()

    def test_load_after_save_restores_values(self, tmp_path: Path) -> None:
        opts = PluginOptions(fabricator="pcbway", inventory_path="/x/y.csv")
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            save_options(opts, tmp_path)
            loaded = load_options(tmp_path)
        assert loaded == opts

    def test_load_returns_defaults_when_file_absent(self, tmp_path: Path) -> None:
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            loaded = load_options(tmp_path / "nofile.kicad_pcb")
        assert loaded == PluginOptions()

    def test_load_returns_defaults_on_malformed_json(self, tmp_path: Path) -> None:
        jbom_dir = tmp_path / ".jbom"
        jbom_dir.mkdir()
        (jbom_dir / "jbom-options.json").write_text("NOT VALID JSON", encoding="utf-8")
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            loaded = load_options(tmp_path)
        assert loaded == PluginOptions()

    def test_load_returns_defaults_on_empty_file(self, tmp_path: Path) -> None:
        jbom_dir = tmp_path / ".jbom"
        jbom_dir.mkdir()
        (jbom_dir / "jbom-options.json").write_text("", encoding="utf-8")
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            loaded = load_options(tmp_path)
        assert loaded == PluginOptions()

    def test_saved_json_is_human_readable(self, tmp_path: Path) -> None:
        """Verify the persisted file is indented JSON, not a compact blob."""
        opts = PluginOptions(fabricator="jlc", inventory_path="")
        with patch("jbom.plugin.options._find_git_root", return_value=tmp_path):
            save_options(opts, tmp_path)
            path = _options_file(tmp_path)
        content = path.read_text(encoding="utf-8")
        # Must be valid JSON
        parsed = json.loads(content)
        assert parsed["fabricator"] == "jlc"
        # Must be pretty-printed (indented)
        assert "\n" in content, "Expected indented JSON but got compact output"
