"""Tests for ``get_fabricators_with_names()`` introduced for the plugin dialog dropdown."""

from __future__ import annotations

from jbom.config.fabricators import get_fabricators_with_names


class TestGetFabricatorsWithNames:
    def test_returns_list_of_tuples(self) -> None:
        result = get_fabricators_with_names()
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_contains_known_fabricators(self) -> None:
        ids = [fid for fid, _ in get_fabricators_with_names()]
        assert "jlc" in ids
        assert "generic" in ids

    def test_jlc_display_name(self) -> None:
        mapping = dict(get_fabricators_with_names())
        assert mapping["jlc"] == "JLC"

    def test_generic_display_name(self) -> None:
        mapping = dict(get_fabricators_with_names())
        assert mapping["generic"] == "Generic"

    def test_pcbway_display_name(self) -> None:
        mapping = dict(get_fabricators_with_names())
        assert mapping.get("pcbway") == "PCBWay"

    def test_seeed_display_name(self) -> None:
        mapping = dict(get_fabricators_with_names())
        assert mapping.get("seeed") == "Seeed Studio"

    def test_result_is_sorted_by_id(self) -> None:
        ids = [fid for fid, _ in get_fabricators_with_names()]
        assert ids == sorted(ids)

    def test_display_names_are_non_empty(self) -> None:
        for fid, name in get_fabricators_with_names():
            assert name, f"Display name for {fid!r} must not be empty"
