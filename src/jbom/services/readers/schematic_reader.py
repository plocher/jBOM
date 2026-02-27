"""KiCad schematic parsing helpers.

This module provides a stable import path for the low-level schematic parsing
functions used by :class:`jbom.services.schematic_reader.SchematicReader`.

Unit tests patch these symbols to avoid invoking the real S-expression parser.
"""

from __future__ import annotations

from jbom.common.sexp_parser import load_kicad_file, walk_nodes

__all__ = ["load_kicad_file", "walk_nodes"]
