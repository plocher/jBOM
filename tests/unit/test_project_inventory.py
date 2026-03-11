"""Unit tests for ProjectInventoryGenerator multi-pass classification (issue #166)."""

from __future__ import annotations

from jbom.common.types import Component
from jbom.services.project_inventory import ProjectInventoryGenerator


def _comp(
    lib_id: str,
    value: str,
    footprint: str = "",
    reference: str = "",
    description: str = "",
    keywords: str = "",
) -> Component:
    props: dict[str, str] = {}
    if description:
        props["Description"] = description
    if keywords:
        props["Keywords"] = keywords
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        uuid="",
        properties=props,
    )


# ---------------------------------------------------------------------------
# Phase 1 integration: description/keywords reach the classifier at harvest time
# ---------------------------------------------------------------------------


def test_load_per_instance_uses_description_to_classify() -> None:
    """WS2812B with Description='RGB LED Neopixel' in schematic properties → category LED."""
    comp = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        description="RGB LED Neopixel",
    )
    gen = ProjectInventoryGenerator([comp])
    items, _ = gen.load_per_instance()
    assert len(items) == 1
    assert items[0].category == "LED", f"expected LED, got {items[0].category!r}"


def test_load_per_instance_no_description_stays_unknown() -> None:
    """WS2812B with no Description and no other signals stays Unknown (pre-Phase-2)."""
    comp = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
    )
    gen = ProjectInventoryGenerator([comp])
    items, _ = gen.load_per_instance()
    # No description, no other signals → still Unknown (Phase 2 has no peer to propagate from)
    assert items[0].category == "Unknown"


# ---------------------------------------------------------------------------
# Phase 2: value-consensus propagation
# ---------------------------------------------------------------------------


def test_load_per_instance_propagates_category_to_descriptionless_sibling() -> None:
    """WS2812B without Description inherits LED from same-value sibling that has one."""
    comp_with_desc = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        description="RGB LED Neopixel",
    )
    comp_without_desc = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
    )
    gen = ProjectInventoryGenerator([comp_with_desc, comp_without_desc])
    items, _ = gen.load_per_instance()

    categories = {item.category for item in items}
    assert categories == {
        "LED"
    }, f"expected all LED after propagation, got {categories}"


def test_load_per_instance_does_not_propagate_already_classified_items() -> None:
    """Classified items keep their category; propagation only fills Unknown slots."""
    res = _comp("Device:R", "10K", "Resistor_SMD:R_0603_1608Metric", "R1")
    unknown = _comp("Custom:XYZZY", "SOMETHING_UNIQUE_9999")

    gen = ProjectInventoryGenerator([res, unknown])
    items, _ = gen.load_per_instance()

    res_item = next(i for i in items if i.value == "10K")
    unk_item = next(i for i in items if i.value == "SOMETHING_UNIQUE_9999")
    assert res_item.category == "RES"
    assert unk_item.category == "Unknown"  # no classified peer → stays Unknown


def test_load_per_instance_skips_propagation_when_value_is_ambiguous() -> None:
    """When a value maps to two distinct categories, Unknown siblings are not promoted."""
    comp_res = _comp("Device:R", "AMBIG", "Resistor_SMD:R_0603_1608Metric", "R1")
    comp_cap = _comp("Device:C", "AMBIG", "Capacitor_SMD:C_0603_1608Metric", "C1")
    comp_unk = _comp("Custom:AMBIG_PART", "AMBIG")

    gen = ProjectInventoryGenerator([comp_res, comp_cap, comp_unk])
    items, _ = gen.load_per_instance()

    unk_item = next(
        i for i in items if i.symbol_lib == "Custom" and i.symbol_name == "AMBIG_PART"
    )
    assert (
        unk_item.category == "Unknown"
    ), f"ambiguous value should not be propagated, got {unk_item.category!r}"


def test_load_aggregated_propagates_category_to_unknown_sibling() -> None:
    """In aggregated load(), value propagation correctly merges Unknown into LED group."""
    comp_with_desc = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        description="RGB LED Neopixel",
    )
    comp_without_desc = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
    )
    gen = ProjectInventoryGenerator([comp_with_desc, comp_without_desc])
    items, _ = gen.load()

    # Both components have same value+footprint+category after propagation → one group
    assert len(items) == 1
    assert items[0].category == "LED"


# ---------------------------------------------------------------------------
# LED-prefix reference signal (follow-up to #166)
# ---------------------------------------------------------------------------


def test_led_ref_prefix_classifies_ws2812b_with_no_description() -> None:
    """WS2812B5050 with 'LED1' reference and no description classifies as LED via ref signal."""
    comp = _comp(
        lib_id="SPCoast:WS2812B5050",
        value="WS2812B5050",
        footprint="PCM_SPCoast:WS2812B5050",
        reference="LED1",
    )
    gen = ProjectInventoryGenerator([comp])
    items, _ = gen.load_per_instance()
    assert (
        items[0].category == "LED"
    ), f"expected LED via LED-ref, got {items[0].category!r}"


def test_led_ref_prefix_component_id_matches_category() -> None:
    """ComponentID must reflect the classified LED category, not 'UNK'.

    Regression for the bug where _create_inventory_item() re-derived the
    ComponentID from scratch (ignoring the multi-pass category_override),
    producing CAT=UNK even when the category field was correctly LED.
    """
    comp = _comp(
        lib_id="SPCoast:WS2812B5050",
        value="WS2812B5050",
        footprint="PCM_SPCoast:WS2812B5050",
        reference="LED1",
    )
    gen = ProjectInventoryGenerator([comp])
    items, _ = gen.load_per_instance()
    assert items[0].category == "LED"
    assert (
        "CAT=LED" in items[0].component_id
    ), f"ComponentID should contain CAT=LED, got {items[0].component_id!r}"
    assert "CAT=UNK" not in items[0].component_id


def test_phase2_propagated_category_reflected_in_component_id() -> None:
    """ComponentID reflects Phase-2-propagated category, not the re-derived UNK.

    When Phase 2 value-consensus promotes a component from Unknown to LED,
    the ComponentID must show CAT=LED to match the category field and the
    grouping key used in load().
    """
    comp_with_desc = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        description="RGB LED Neopixel",
    )
    comp_without_desc = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
    )
    gen = ProjectInventoryGenerator([comp_with_desc, comp_without_desc])
    items, _ = gen.load_per_instance()

    for item in items:
        assert item.category == "LED"
        assert "CAT=LED" in item.component_id, (
            f"component_id should contain CAT=LED after Phase-2 propagation, "
            f"got {item.component_id!r}"
        )
