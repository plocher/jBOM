"""Unit tests for field namespace prefix handling."""

from jbom.common.field_parser import parse_fields_argument
from jbom.common.fields import field_to_header, normalize_field_name


def test_normalize_field_name_preserves_supported_namespace_prefixes() -> None:
    assert normalize_field_name("sch:Footprint") == "sch:footprint"
    assert normalize_field_name("pcb:Mount Type") == "pcb:mount_type"
    assert normalize_field_name("ann:Value") == "ann:value"
    assert normalize_field_name("inv:Package") == "inv:package"


def test_field_to_header_formats_supported_namespace_prefixes() -> None:
    assert field_to_header("sch:footprint") == "SCH:Footprint"
    assert field_to_header("pcb:mount_type") == "PCB:Mount Type"
    assert field_to_header("ann:value") == "ANN:Value"
    assert field_to_header("c:value") == "C:value"
    assert field_to_header("inv:package") == "INV:Package"


def test_parse_fields_argument_accepts_namespace_prefixed_tokens() -> None:
    available = {
        "reference": "Reference",
        "quantity": "Quantity",
        "value": "Value",
    }

    selected = parse_fields_argument(
        "reference,sch:footprint,pcb:mount_type,ann:value,inv:package",
        available,
        fabricator_id="generic",
        context="bom",
    )

    assert selected == [
        "reference",
        "sch:footprint",
        "pcb:mount_type",
        "ann:value",
        "inv:package",
    ]
