"""Unit tests for global CLI --defaults profile selection."""

from __future__ import annotations

from jbom.cli.main import create_parser, main
from jbom.config.defaults import (
    get_active_defaults_profile,
    set_active_defaults_profile,
)


def test_all_subcommands_accept_defaults_argument() -> None:
    parser = create_parser()
    custom = "custom-profile"

    cases = [
        ["annotate", ".", "--defaults", custom],
        ["audit", ".", "--defaults", custom],
        ["bom", ".", "--defaults", custom],
        ["inventory", ".", "--defaults", custom],
        ["parts", ".", "--defaults", custom],
        ["pos", ".", "--defaults", custom],
        ["search", "10k resistor", "--defaults", custom],
    ]

    for argv in cases:
        args = parser.parse_args(argv)
        assert args.defaults == custom


def test_all_subcommands_default_defaults_profile_to_generic() -> None:
    parser = create_parser()

    cases = [
        ["annotate", "."],
        ["audit", "."],
        ["bom", "."],
        ["inventory", "."],
        ["parts", "."],
        ["pos", "."],
        ["search", "10k resistor"],
    ]

    for argv in cases:
        args = parser.parse_args(argv)
        assert args.defaults == "generic"


def test_main_sets_active_defaults_profile_for_handler(monkeypatch) -> None:
    captured: dict[str, str] = {}
    custom = "custom-profile"

    def _fake_handle_search(_args) -> int:
        captured["active_profile"] = get_active_defaults_profile()
        return 0

    monkeypatch.setattr("jbom.cli.search.handle_search", _fake_handle_search)

    previous = get_active_defaults_profile()
    set_active_defaults_profile("generic")
    try:
        rc = main(["search", "10k resistor", "--defaults", custom])
        assert rc == 0
        assert captured["active_profile"] == custom
        assert get_active_defaults_profile() == "generic"
    finally:
        set_active_defaults_profile(previous)
