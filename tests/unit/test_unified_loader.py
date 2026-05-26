"""Unit tests for the unified ``*.jbom.yaml`` merge engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import jbom.config.unified as unified


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def _patch_search_dirs(monkeypatch: pytest.MonkeyPatch, dirs: list[Path]) -> None:
    monkeypatch.setattr(unified, "profile_search_dirs", lambda *, cwd=None: dirs)


def test_load_unified_applies_null_delete_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    level = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _patch_search_dirs(monkeypatch, [level])

    _write_yaml(
        builtin / "generic.jbom.yaml",
        {
            "fab": {
                "bom_columns": {"Designator": "reference", "Surface Mount": "smd"},
            }
        },
    )
    _write_yaml(
        level / "custom.jbom.yaml",
        {
            "extends": "generic",
            "fab": {
                "bom_columns": {
                    "Surface Mount": None,
                }
            },
        },
    )

    merged = unified.load_unified("custom", cwd=level, builtin_dir=builtin)
    bom_columns = merged["fab"]["bom_columns"]
    assert "Designator" in bom_columns
    assert "Surface Mount" not in bom_columns


def test_load_unified_applies_list_replace_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    level = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _patch_search_dirs(monkeypatch, [level])

    _write_yaml(
        builtin / "generic.jbom.yaml",
        {
            "fab": {
                "suppliers": ["lcsc", "mouser", "digikey"],
            }
        },
    )
    _write_yaml(
        level / "jlc-short.jbom.yaml",
        {
            "extends": "generic",
            "fab": {
                "suppliers": ["lcsc"],
            },
        },
    )

    merged = unified.load_unified("jlc-short", cwd=level, builtin_dir=builtin)
    assert merged["fab"]["suppliers"] == ["lcsc"]


def test_load_unified_detects_circular_extends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    level = tmp_path / "project"
    _patch_search_dirs(monkeypatch, [level])

    _write_yaml(level / "a.jbom.yaml", {"extends": "b", "fab": {}})
    _write_yaml(level / "b.jbom.yaml", {"extends": "a", "fab": {}})

    with pytest.raises(ValueError, match="Circular extends chain detected"):
        unified.load_unified("a", cwd=level, builtin_dir=tmp_path / "builtin")


def test_load_unified_merges_common_chain_from_all_levels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    high = tmp_path / "high"
    mid = tmp_path / "mid"
    low = tmp_path / "low"
    builtin = tmp_path / "builtin"
    _patch_search_dirs(monkeypatch, [high, mid, low])

    _write_yaml(
        low / "common.jbom.yaml",
        {
            "defaults": {
                "domain_defaults": {
                    "resistor": {
                        "tolerance": "10%",
                        "wattage": "0.125W",
                    }
                }
            }
        },
    )
    _write_yaml(
        mid / "common.jbom.yaml",
        {
            "defaults": {
                "domain_defaults": {
                    "resistor": {
                        "voltage": "50V",
                    }
                }
            }
        },
    )
    _write_yaml(
        high / "common.jbom.yaml",
        {
            "defaults": {
                "domain_defaults": {
                    "resistor": {
                        "tolerance": "1%",
                    }
                }
            }
        },
    )
    _write_yaml(high / "jlc.jbom.yaml", {"fab": {"name": "JLC"}})

    merged = unified.load_unified("jlc", cwd=high, builtin_dir=builtin)
    resistor_defaults = merged["defaults"]["domain_defaults"]["resistor"]
    assert resistor_defaults["tolerance"] == "1%"
    assert resistor_defaults["voltage"] == "50V"
    assert resistor_defaults["wattage"] == "0.125W"


def test_load_unified_uses_named_profile_first_match_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _patch_search_dirs(monkeypatch, [project, builtin])

    _write_yaml(
        builtin / "jlc.jbom.yaml",
        {
            "marker": "builtin",
            "fab": {"name": "JLC Builtin"},
            "defaults": {"search": {"output_fields": {"default": ["mpn"]}}},
        },
    )
    _write_yaml(
        project / "jlc.jbom.yaml",
        {
            "marker": "project",
            "fab": {"name": "JLC Project"},
        },
    )

    merged = unified.load_unified("jlc", cwd=project, builtin_dir=builtin)
    assert merged["marker"] == "project"
    assert merged["fab"]["name"] == "JLC Project"
    assert "defaults" not in merged


def test_stanza_id_override_resolves_to_profile_name_for_lookup_and_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _patch_search_dirs(monkeypatch, [project, builtin])

    _write_yaml(
        builtin / "jlc.jbom.yaml",
        {
            "id": "jlc",
            "fab": {"name": "JLC"},
            "supplier": {"id": "lcsc", "name": "LCSC"},
        },
    )

    supplier_ids = unified.list_unified_stanza_ids(
        "supplier", cwd=project, builtin_dir=builtin
    )
    assert "lcsc" in supplier_ids

    resolved_profile = unified.resolve_profile_name_for_stanza_id(
        "supplier", "lcsc", cwd=project, builtin_dir=builtin
    )
    assert resolved_profile == "jlc"


def test_load_unified_returns_isolated_mappings_between_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _patch_search_dirs(monkeypatch, [project])

    _write_yaml(
        project / "generic.jbom.yaml",
        {
            "fab": {
                "name": "Generic",
                "bom_columns": {"Designator": "reference"},
            }
        },
    )

    first = unified.load_unified("generic", cwd=project, builtin_dir=builtin)
    second = unified.load_unified("generic", cwd=project, builtin_dir=builtin)

    first["fab"]["bom_columns"]["Designator"] = "changed"
    assert second["fab"]["bom_columns"]["Designator"] == "reference"
