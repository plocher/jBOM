"""Unit tests for POS CLI projection and field resolution helpers."""

from jbom.cli.pos import _get_pos_field_value, _resolve_pos_output_projection


def test_resolve_pos_output_projection_uses_jlc_defaults() -> None:
    selected_fields, headers, config = _resolve_pos_output_projection(
        selected_fields=None,
        fabricator="jlc",
        user_specified_fields=False,
    )

    assert config is not None
    assert selected_fields == ["reference", "x", "y", "side", "rotation", "package"]
    assert headers == ["Designator", "Mid X", "Mid Y", "Layer", "Rotation", "Package"]


def test_resolve_pos_output_projection_keeps_generic_user_headers() -> None:
    selected_fields, headers, config = _resolve_pos_output_projection(
        selected_fields=["reference", "x", "y", "side"],
        fabricator="generic",
        user_specified_fields=True,
    )

    assert config is not None
    assert selected_fields == ["reference", "x", "y", "side"]
    assert headers == ["Reference", "X", "Y", "Side"]


def test_fabricator_part_number_resolves_from_jlc_synonym_attribute() -> None:
    entry = {"jlcpcb_part_#": "C965799"}
    assert (
        _get_pos_field_value(
            entry,
            "fabricator_part_number",
            fabricator_id="jlc",
        )
        == "C965799"
    )


def test_fabricator_part_number_prefers_explicit_value() -> None:
    entry = {
        "fabricator_part_number": "JLC-OVERRIDE-777",
        "jlcpcb_part_#": "C965799",
    }
    assert (
        _get_pos_field_value(
            entry,
            "fabricator_part_number",
            fabricator_id="jlc",
        )
        == "JLC-OVERRIDE-777"
    )
