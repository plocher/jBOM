"""Unit tests for jbom.common.cli_fabricator helpers."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import jbom.common.cli_fabricator as cli_fabricator


def test_add_fabricator_arguments_reuses_cached_metadata(
    monkeypatch,
) -> None:
    cli_fabricator.clear_fabricator_argument_cache()

    monkeypatch.setattr(
        cli_fabricator, "get_available_fabricators", lambda: ["jlc", "pcbway"]
    )
    call_counter = {"load_fabricator": 0}

    def _fake_load_fabricator(fid: str) -> SimpleNamespace:
        call_counter["load_fabricator"] += 1
        return SimpleNamespace(name=fid.upper())

    monkeypatch.setattr(cli_fabricator, "load_fabricator", _fake_load_fabricator)

    parser_a = argparse.ArgumentParser()
    cli_fabricator.add_fabricator_arguments(parser_a)
    parser_b = argparse.ArgumentParser()
    cli_fabricator.add_fabricator_arguments(parser_b)

    assert call_counter["load_fabricator"] == 2


def test_resolve_fabricator_selection_from_shorthand_flag(monkeypatch) -> None:
    cli_fabricator.clear_fabricator_argument_cache()
    monkeypatch.setattr(cli_fabricator, "get_available_fabricators", lambda: ["jlc"])
    monkeypatch.setattr(
        cli_fabricator,
        "load_fabricator",
        lambda _fid: SimpleNamespace(name="JLC"),
    )

    parser = argparse.ArgumentParser()
    cli_fabricator.add_fabricator_arguments(parser)
    args = parser.parse_args(["--jlc"])

    selected, is_explicit = cli_fabricator.resolve_fabricator_selection_from_args(args)
    assert selected == "jlc"
    assert is_explicit is True
