"""Shared S-expression parsing utilities for KiCad files.

Provides low-level utilities for parsing both .kicad_sch and .kicad_pcb files
using the sexpdata library. Both formats use the same S-expression structure.
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterator, Optional, Any, List
from sexpdata import loads, Symbol

__all__ = [
    "load_kicad_file",
    "walk_nodes",
    "find_child",
    "find_all_children",
]


def load_kicad_file(path: Path) -> Any:
    """Load and parse a KiCad S-expression file.

    Args:
        path: Path to .kicad_sch or .kicad_pcb file

    Returns:
        Parsed S-expression tree (nested lists)

    Example:
        sexp = load_kicad_file(Path('project.kicad_sch'))
    """
    text = path.read_text(encoding="utf-8")
    return loads(text)


def walk_nodes(sexp: Any, node_type: str) -> Iterator[List]:
    """Generator that yields all nodes of a specific type.

    Recursively walks the S-expression tree and yields all nodes that
    match the specified type. Node types are identified by the first
    element being a Symbol with the matching name.

    Args:
        sexp: S-expression tree or subtree
        node_type: Type of nodes to find (e.g. 'symbol', 'footprint')

    Yields:
        Matching nodes (each is a list with Symbol as first element)

    Example:
        for footprint_node in walk_nodes(sexp, 'footprint'):
            # Process footprint node
            ref = find_child(footprint_node, 'reference')
    """
    def walk(n: Any) -> Iterator[List]:
        if isinstance(n, list) and n:
            if n[0] == Symbol(node_type):
                yield n
            else:
                for child in n:
                    yield from walk(child)

    yield from walk(sexp)


def find_child(node: List, child_type: str) -> Optional[List]:
    """Find first child node of given type.

    Args:
        node: Parent node (list)
        child_type: Type of child to find

    Returns:
        First matching child node, or None if not found

    Example:
        layer = find_child(footprint_node, 'layer')
        if layer and len(layer) >= 2:
            layer_name = layer[1]
    """
    for child in node[1:]:
        if isinstance(child, list) and child and child[0] == Symbol(child_type):
            return child
    return None


def find_all_children(node: List, child_type: str) -> List[List]:
    """Find all child nodes of given type.

    Args:
        node: Parent node (list)
        child_type: Type of children to find

    Returns:
        List of matching child nodes (may be empty)

    Example:
        properties = find_all_children(symbol_node, 'property')
        for prop in properties:
            key, value = prop[1], prop[2]
    """
    results = []
    for child in node[1:]:
        if isinstance(child, list) and child and child[0] == Symbol(child_type):
            results.append(child)
    return results
