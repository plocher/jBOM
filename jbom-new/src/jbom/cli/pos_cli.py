"""Minimal CLI for POS default behavior.

Usage:
  python -m jbom.cli.pos_cli

Behavior:
- With no arguments, look in current directory for a .kicad_pcb and a KiCad project
  (.kicad_pro or legacy .pro). If none found, exit with non-zero and print an error.
- If a PCB is found, generate <project>.pos.csv in the same directory using the POS service.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jbom.plugins.pos.services.pos_generator import create_pos_generator
from jbom.cli.discovery import find_project_and_pcb, default_output_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    # Intentionally minimal; no options handled yet for this path
    _ = parser.parse_args(argv or [])

    cwd = Path.cwd()
    project, pcb = find_project_and_pcb(cwd)
    if not pcb:
        sys.stderr.write("Error: No .kicad_pcb file found in current directory\n")
        return 2

    # Determine default output file name: <project>.pos.csv if project exists, else pcb stem
    output = default_output_name(cwd, project, pcb, "pos.csv")

    gen = create_pos_generator()
    try:
        gen.generate_pos_file(pcb_file=pcb, output_file=output)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
