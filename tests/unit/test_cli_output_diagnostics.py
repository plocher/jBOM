"""Unit tests for jbom.cli.output.print_diagnostics (Issue #375).

Covers the `-q/--quiet` (`JBOM_QUIET`) contract: `info`/`warning`
severities are suppressed when quiet, `error` severity is always
printed, and output always goes to the given stream (stderr by
default), never stdout.
"""
from __future__ import annotations

import io

import pytest

from jbom.cli.output import print_diagnostics
from jbom.common.types import Diagnostic


@pytest.fixture(autouse=True)
def _clean_jbom_quiet_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure JBOM_QUIET starts unset for every test in this module."""
    monkeypatch.delenv("JBOM_QUIET", raising=False)


def test_info_and_warning_print_when_not_quiet() -> None:
    diagnostics = [
        Diagnostic("info", "Selected fields: reference,value"),
        Diagnostic("warning", "Warning: Missing important generic fields: value"),
    ]
    buffer = io.StringIO()
    print_diagnostics(diagnostics, file=buffer)
    output = buffer.getvalue()
    assert "Selected fields" in output
    assert "Missing important generic fields" in output


def test_info_and_warning_suppressed_when_quiet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JBOM_QUIET", "1")
    diagnostics = [
        Diagnostic("info", "Selected fields: reference,value"),
        Diagnostic("warning", "Warning: Missing important generic fields: value"),
    ]
    buffer = io.StringIO()
    print_diagnostics(diagnostics, file=buffer)
    assert buffer.getvalue() == ""


def test_error_always_prints_even_when_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JBOM_QUIET", "1")
    diagnostics = [
        Diagnostic("info", "Selected fields: reference,value"),
        Diagnostic("error", "Inventory file not found: missing.csv"),
    ]
    buffer = io.StringIO()
    print_diagnostics(diagnostics, file=buffer)
    output = buffer.getvalue()
    assert "Selected fields" not in output
    assert "Inventory file not found" in output


def test_no_diagnostics_produces_no_output() -> None:
    buffer = io.StringIO()
    print_diagnostics([], file=buffer)
    assert buffer.getvalue() == ""


def test_empty_string_jbom_quiet_is_not_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty-string JBOM_QUIET is falsy, matching bool(os.environ.get(...))."""
    monkeypatch.setenv("JBOM_QUIET", "")
    diagnostics = [Diagnostic("warning", "Warning: something")]
    buffer = io.StringIO()
    print_diagnostics(diagnostics, file=buffer)
    assert "Warning: something" in buffer.getvalue()
