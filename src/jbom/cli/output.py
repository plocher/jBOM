"""Shared CLI output helpers.

Centralizes `-o/--output` semantics across subcommands:
- `-o console` => console output
- `-o -` => CSV to stdout
- `-o <path>` => write CSV to file
- omitted `-o` => command-specific default (console or file path)

Also centralizes overwrite protection via `-F/--force/--Force`.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, TextIO

from jbom.common.types import Diagnostic


class OutputKind(str, Enum):
    """High-level output destination kind."""

    CONSOLE = "console"
    STDOUT = "stdout"
    FILE = "file"


@dataclass(frozen=True)
class OutputDestination:
    """Resolved output destination."""

    kind: OutputKind
    path: Path | None = None


def add_force_argument(parser: argparse.ArgumentParser) -> None:
    """Add a common overwrite flag.

    Uses `-F/--force/--Force` as requested.
    """

    parser.add_argument(
        "-F",
        "--force",
        "--Force",
        action="store_true",
        help="Overwrite existing output files",
    )


def resolve_output_destination(
    output: str | None,
    *,
    default_destination: OutputDestination,
) -> OutputDestination:
    """Resolve CLI output argument into a normalized OutputDestination.

    Args:
        output: Raw CLI `-o/--output` value.
        default_destination: Destination to use when `output` is omitted.

    Returns:
        Resolved destination.
    """

    if output is None:
        return default_destination

    out = (output or "").strip()
    if out == "console":
        return OutputDestination(OutputKind.CONSOLE)

    if out == "-":
        return OutputDestination(OutputKind.STDOUT)

    return OutputDestination(OutputKind.FILE, path=Path(out))


def print_diagnostics(
    diagnostics: Iterable[Diagnostic],
    *,
    file: TextIO | None = None,
) -> None:
    """Render diagnostics honoring the global `-q/--quiet` (`JBOM_QUIET`) flag.

    `info` and `warning` severities are suppressed when `JBOM_QUIET` is set
    (see `-q/--quiet` in `jbom/cli/main.py`). `error` severity is always
    printed regardless of quiet mode. All diagnostics are written to `file`
    (stderr by default), never to stdout, preserving stdout CSV purity for
    `-o -` output.

    Args:
        diagnostics: Diagnostics to render.
        file: Stream to write rendered diagnostics to (defaults to the
            current `sys.stderr`, resolved at call time).
    """

    destination = file if file is not None else sys.stderr
    quiet = bool(os.environ.get("JBOM_QUIET"))
    for diagnostic in diagnostics:
        if quiet and diagnostic.severity != "error":
            continue
        print(diagnostic, file=destination)


class OutputRefusedError(RuntimeError):
    """Raised when output cannot be written (e.g. overwrite protection)."""


def open_output_text_file(
    path: Path,
    *,
    force: bool,
    refused_message: str,
    make_backup: Callable[[Path], Path | None] | None = None,
) -> TextIO:
    """Open an output file for writing with overwrite protection.

    Args:
        path: Output path.
        force: If True, allow overwriting an existing file.
        refused_message: Message to use if overwriting is refused.
        make_backup: Optional function invoked when overwriting an existing file.

    Raises:
        OutputRefusedError: If the file exists and force is False.

    Returns:
        Open file handle.
    """

    if path.exists() and not force:
        raise OutputRefusedError(refused_message)

    if path.exists() and force and make_backup is not None:
        make_backup(path)

    # Always overwrite when force is True or the file does not exist.
    return path.open("w", newline="", encoding="utf-8")
