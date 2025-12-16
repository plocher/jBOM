#!/usr/bin/env python3
"""
KiCad BOM plugin wrapper for jBOM v3.0.

This is a thin wrapper that translates KiCad's plugin interface to jBOM CLI calls.
No logic duplication - just argument translation.

Usage in KiCad (Eeschema -> Tools -> Generate BOM):
  Command: python3 /absolute/path/to/kicad_jbom_plugin.py %I
           -i /path/to/INVENTORY.xlsx -o %O [-v] [-d] [-f FIELDS]

Plugin Arguments:
  %I         - KiCad schematic path (provided by KiCad)
  %O         - Output BOM file path (provided by KiCad)
  -i FILE    - Inventory file (.csv/.xlsx/.xls/.numbers)
  -v         - Verbose mode (adds match quality columns)
  -d         - Debug mode (adds matching diagnostics)
  -f FIELDS  - Field specification (e.g., +jlc or Reference,Value,LCSC)

Examples:
  # Basic usage with inventory
  python3 kicad_jbom_plugin.py %I -i inventory.xlsx -o %O

  # With JLCPCB preset
  python3 kicad_jbom_plugin.py %I -i inventory.xlsx -o %O -f +jlc

  # Verbose mode with custom fields
  python3 kicad_jbom_plugin.py %I -i inventory.xlsx -o %O -v -f "Reference,Value,LCSC,Package"
"""
import sys
import subprocess


def main():
    """
    Translate KiCad plugin arguments to jBOM CLI and execute.

    KiCad calls:    kicad_jbom_plugin.py SCHEMATIC -i INV -o OUT [OPTIONS]
    We execute:     jbom bom SCHEMATIC -i INV -o OUT [OPTIONS]

    The only difference is inserting the 'bom' subcommand.
    All other arguments pass through unchanged.
    """
    # sys.argv[1:] = [SCHEMATIC, -i, INV, -o, OUT, ...]
    # We need:       [bom, SCHEMATIC, -i, INV, -o, OUT, ...]
    jbom_args = ["bom"] + sys.argv[1:]

    # Execute jBOM CLI using the same Python interpreter
    result = subprocess.run([sys.executable, "-m", "jbom.cli.main"] + jbom_args)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
