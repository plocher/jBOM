"""Unit tests for field namespace prefix handling."""

from jbom.common.field_parser import parse_fields_argument
from jbom.common.fields import field_to_header, normalize_field_name


def test_normalize_field_name_preserves_supported_namespace_prefixes() -> None:
    assert normalize_field_name("s:Footprint") == "s:footprint"
    assert normalize_field_name("p:Mount Type") == "p:mount_type"
    assert normalize_field_name("a:Value") == "a:value"
    assert normalize_field_name("i:Package") == "i:package"


def test_field_to_header_formats_supported_namespace_prefixes() -> None:
    assert field_to_header("s:footprint") == "S:Footprint"
    assert field_to_header("p:mount_type") == "P:Mount Type"
    assert field_to_header("a:value") == "A:Value"
    assert field_to_header("c:value") == "C:value"
    assert field_to_header("i:package") == "I:Package"


def test_parse_fields_argument_accepts_namespace_prefixed_tokens() -> None:
    available = {
        "reference": "Reference",
        "quantity": "Quantity",
        "value": "Value",
    }

    selected = parse_fields_argument(
        "reference,s:footprint,p:mount_type,a:value,i:package",
        available,
        fabricator_id="generic",
        context="bom",
    )

    assert selected == [
        "reference",
        "s:footprint",
        "p:mount_type",
        "a:value",
        "i:package",
    ]
