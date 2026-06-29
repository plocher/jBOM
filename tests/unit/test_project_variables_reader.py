"""Unit tests for :mod:`jbom.services.project_variables_reader`.

Pins down ``.kicad_pro`` ``text_variables`` ingestion behaviour added in
issue #332:

* When the project file declares a ``text_variables`` map, its entries
  surface verbatim through :class:`ProjectTextVariables`.
* When ``text_variables`` is absent (the modal case for legacy or
  hand-edited projects), the artifact carries an empty map \u2014 *not* a
  diagnostic.  Absence is normal.
* Bad inputs (missing file, wrong extension, malformed JSON) raise on
  ingest so the resolver path can decide how to react.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jbom.services.project_variables_reader import (
    ProjectTextVariables,
    read_text_variables,
)


def _write_project_file(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestReadTextVariablesPresent:
    """``.kicad_pro`` with a populated ``text_variables`` map."""

    def test_returns_text_variables_verbatim(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        _write_project_file(
            project,
            {
                "meta": {"filename": "demo.kicad_pro", "version": 1},
                "text_variables": {
                    "DESIGNER": "John Plocher",
                    "STATUS": "released",
                },
            },
        )
        result = read_text_variables(project)
        assert isinstance(result, ProjectTextVariables)
        assert dict(result.variables) == {
            "DESIGNER": "John Plocher",
            "STATUS": "released",
        }
        assert result.source_path == project

    def test_preserves_raw_values(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        raw = "  spaced  with\ttabs  "
        _write_project_file(project, {"text_variables": {"NOTE": raw}})
        result = read_text_variables(project)
        assert result.variables["NOTE"] == raw


class TestReadTextVariablesAbsent:
    """Missing or empty ``text_variables`` is the modal case \u2014 no diagnostic."""

    def test_missing_text_variables_key_yields_empty_map(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        _write_project_file(project, {"meta": {"version": 1}})
        result = read_text_variables(project)
        assert dict(result.variables) == {}
        assert result.source_path == project

    def test_empty_text_variables_object_yields_empty_map(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        _write_project_file(project, {"text_variables": {}})
        result = read_text_variables(project)
        assert dict(result.variables) == {}

    def test_text_variables_set_to_null_yields_empty_map(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        _write_project_file(project, {"text_variables": None})
        result = read_text_variables(project)
        assert dict(result.variables) == {}


class TestReadTextVariablesErrors:
    """Bad inputs surface as exceptions so callers can decide policy."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_text_variables(tmp_path / "nope.kicad_pro")

    def test_wrong_extension_raises_value_error(self, tmp_path: Path) -> None:
        bogus = tmp_path / "demo.txt"
        bogus.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match=r"\.kicad_pro"):
            read_text_variables(bogus)

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        project.write_text("{not-json", encoding="utf-8")
        with pytest.raises(ValueError):
            read_text_variables(project)


class TestProjectTextVariablesDataclass:
    """The artifact is a frozen dataclass with a read-only variables map.\"\"\" """

    def test_is_frozen(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        _write_project_file(project, {"text_variables": {"A": "1"}})
        artifact = read_text_variables(project)
        with pytest.raises(AttributeError):
            artifact.source_path = tmp_path  # type: ignore[misc]

    def test_variables_mapping_is_read_only(self, tmp_path: Path) -> None:
        project = tmp_path / "demo.kicad_pro"
        _write_project_file(project, {"text_variables": {"A": "1"}})
        artifact = read_text_variables(project)
        with pytest.raises(TypeError):
            artifact.variables["B"] = "2"  # type: ignore[index]
