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


def test_parse_footprint_node_preserves_canonical_fpid_over_schematic_footprint_property() -> (
    None
):
    """PCB-first contract: ``footprint_name`` must be the FPID from the
    ``(footprint "Lib:Name" ...)`` opener.  When the footprint block also
    carries a ``(property "Footprint" ...)`` field (which mirrors the
    schematic-side hint and can disagree with the actual PCB FPID), the
    reader must record it under ``attributes['schematic_footprint']`` and
    NOT overwrite ``footprint_name``.  Otherwise the BOM ends up reporting
    a footprint that doesn't match what's physically on the board (the
    LEDStripDriver / cpOD-updated provenance bug).
    """

    reader = DefaultKiCadReaderService()
    node: list[object] = [
        Symbol("footprint"),
        "VendorLib:0805-CAP",  # canonical FPID
        [Symbol("layer"), "F.Cu"],
        [Symbol("at"), "10", "20", "0"],
        [Symbol("property"), "Reference", "C1"],
        [Symbol("property"), "Value", "1uF"],
        # Schematic-side hint that disagrees with the placed FPID.
        [Symbol("property"), "Footprint", "Capacitor_SMD:C_0805_2012Metric"],
    ]

    parsed = reader._parse_footprint_node(node)

    assert parsed is not None
    # The canonical PCB FPID survives unchanged.
    assert parsed.footprint_name == "VendorLib:0805-CAP"
    # The schematic-side hint is preserved alongside it for diagnostics.
    assert parsed.attributes["schematic_footprint"] == "Capacitor_SMD:C_0805_2012Metric"
