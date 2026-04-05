"""Unit tests for PCB reader attribute extraction behavior."""

from __future__ import annotations

from sexpdata import Symbol

from jbom.services.pcb_reader import DefaultKiCadReaderService


def _footprint_node(
    attr_tokens: list[str],
    *,
    locked: bool = False,
) -> list[object]:
    """Build a minimal footprint S-expression node for parser unit tests."""

    node: list[object] = [
        Symbol("footprint"),
        "Resistor_SMD:R_0805_2012Metric",
        [Symbol("layer"), "F.Cu"],
        [Symbol("at"), "10", "20", "90"],
        [Symbol("property"), "Reference", "R1"],
        [Symbol("property"), "Value", "10K"],
    ]
    if attr_tokens:
        node.append([Symbol("attr"), *[Symbol(token) for token in attr_tokens]])
    if locked:
        node.append([Symbol("locked")])
    return node


def test_parse_footprint_node_records_all_attr_tokens_and_locked_flag() -> None:
    """PCB reader should preserve all `attr` tokens, layer, and locked metadata."""

    reader = DefaultKiCadReaderService()
    parsed = reader._parse_footprint_node(
        _footprint_node(
            ["smd", "exclude_from_pos_files", "exclude_from_bom"],
            locked=True,
        )
    )

    assert parsed is not None
    assert parsed.attributes["mount_type"] == "smd"
    assert parsed.attributes["smd"] == "yes"
    assert parsed.attributes["exclude_from_pos_files"] == "yes"
    assert parsed.attributes["exclude_from_bom"] == "yes"
    assert parsed.attributes["locked"] == "yes"
    assert parsed.attributes["layer"] == "F.Cu"


def test_parse_footprint_node_preserves_unknown_attr_tokens() -> None:
    """Unexpected attr tokens should still be recorded for downstream consumers."""

    reader = DefaultKiCadReaderService()
    parsed = reader._parse_footprint_node(_footprint_node(["custom_attr_flag"]))

    assert parsed is not None
    assert parsed.attributes["custom_attr_flag"] == "yes"
