"""Unit tests for canonical field reference resolution."""

from __future__ import annotations

import re

from jbom.config.field_ref import FieldContext, FieldRefResolver


def test_resolver_returns_jbom_computed_quantity() -> None:
    context = FieldContext(computed={"quantity": 7})
    resolver = FieldRefResolver()

    assert resolver.resolve("jbom:quantity", context) == "7"


def test_resolver_returns_pcb_namespaced_footprint() -> None:
    context = FieldContext(pcb={"footprint": "Capacitors_SMD:C_0402"})
    resolver = FieldRefResolver()

    assert resolver.resolve("pcb:footprint", context) == "Capacitors_SMD:C_0402"


def test_resolver_evaluates_transform_expression_with_namespaced_field() -> None:
    def _strip_kicad_library_prefix_from_value(value: str) -> str:
        return re.sub(r"^[^:]+:", "", value)

    context = FieldContext(
        pcb={"footprint": "Capacitors_SMD:C_0402"},
        transforms={
            "strip_kicad_library_prefix_from_value": _strip_kicad_library_prefix_from_value
        },
    )
    resolver = FieldRefResolver()

    resolved = resolver.resolve(
        "strip_kicad_library_prefix_from_value(pcb:footprint)",
        context,
    )
    assert resolved == "C_0402"
