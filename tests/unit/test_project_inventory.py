"""Unit tests for ProjectInventoryGenerator multi-pass classification (issue #166)."""

from __future__ import annotations

from pathlib import Path

from jbom.common.types import Component
from jbom.services.project_inventory import ProjectInventoryGenerator


def _comp(
    lib_id: str,
    value: str,
    footprint: str = "",
    reference: str = "",
    description: str = "",
    keywords: str = "",
    extra_props: dict[str, str] | None = None,
) -> Component:
    props: dict[str, str] = {}
    if description:
        props["Description"] = description
    if keywords:
        props["Keywords"] = keywords
    if extra_props:
        props.update(extra_props)
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


def test_load_per_instance_maps_manufacturer_aliases_to_canonical_fields() -> None:
    """Schematic alias properties populate canonical manufacturer and mfgpn fields."""

    comp = _comp(
        lib_id="Device:Relay",
        value="CPC1709J",
        footprint="Relay_THT:Relay_SPST",
        reference="K1",
        extra_props={
            "Manufacturer_Name": "LITTELFUSE",
            "Manufacturer_Part_Number": "CPC1709J",
        },
    )
    gen = ProjectInventoryGenerator([comp])
    items, _ = gen.load_per_instance()

    assert len(items) == 1
    assert items[0].manufacturer == "LITTELFUSE"
    assert items[0].mfgpn == "CPC1709J"


# ---------------------------------------------------------------------------
# component_id_fields: per-category optional field filtering
# ---------------------------------------------------------------------------


def test_led_with_and_without_voltage_produce_identical_component_ids() -> None:
    """LED with V=5V and LED without V collapse to the same ComponentID.

    Regression for the original WS2812B phantom-duplicate bug: inconsistent
    schematic annotation of 'V=5V' caused two identical components to be
    treated as different requirements.
    """
    comp_with_v = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        reference="LED1",
        extra_props={"Voltage": "5V"},
    )
    comp_without_v = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        reference="LED2",
    )
    gen = ProjectInventoryGenerator([comp_with_v, comp_without_v])
    items, _ = gen.load()

    assert (
        len(items) == 1
    ), f"Expected 1 group (same LED), got {len(items)}: " + ", ".join(
        i.component_id for i in items
    )
    assert (
        "V=" not in items[0].component_id
    ), f"LED ComponentID must not include voltage, got {items[0].component_id!r}"


def test_res_voltage_still_included_in_component_id() -> None:
    """Resistor with a Voltage property retains V= in the ComponentID.

    Voltage is a meaningful derating spec for resistors — it must remain in
    the ComponentID even after the LED voltage-exclusion change.
    """
    comp = _comp(
        lib_id="Device:R",
        value="10K",
        footprint="Resistor_SMD:R_0603_1608Metric",
        reference="R1",
        extra_props={"Voltage": "100V"},
    )
    gen = ProjectInventoryGenerator([comp])
    items, _ = gen.load()

    assert len(items) == 1
    assert (
        "V=100V" in items[0].component_id
    ), f"Resistor ComponentID must include voltage, got {items[0].component_id!r}"


def test_led_component_id_fields_overridable_via_jbom_dir(tmp_path: Path) -> None:
    """A project .jbom/ generic override can re-add voltage to LED ComponentIDs.

    Exercises the full profile-search path: a ``generic.defaults.yaml`` in the
    project's ``.jbom/`` directory overrides the built-in generic profile.
    ``ProjectInventoryGenerator(cwd=tmp_path)`` picks it up automatically.
    """
    jbom_dir = tmp_path / ".jbom"
    jbom_dir.mkdir()
    # Shadow the built-in 'generic' profile for this project directory.
    # Note: do NOT use 'extends: generic' here — this file IS the 'generic' profile
    # for this cwd, so extending 'generic' would create a circular reference.
    # For this test we only need component_id_fields; other sections are omitted.
    (jbom_dir / "generic.defaults.yaml").write_text(
        "component_id_fields:\n"
        "  led:\n"
        "    - type\n"
        "    - voltage\n"  # re-add voltage so these two LEDs produce different IDs
    )

    comp_with_v = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        reference="LED1",
        extra_props={"Voltage": "5V"},
    )
    comp_without_v = _comp(
        lib_id="SPCoast:WS2812B",
        value="WS2812B",
        footprint="PCM_SPCoast:WS2812B5050",
        reference="LED2",
    )
    # cwd=tmp_path → the generator discovers .jbom/generic.defaults.yaml and
    # uses it automatically — no config injection required.
    gen = ProjectInventoryGenerator([comp_with_v, comp_without_v], cwd=tmp_path)
    items, _ = gen.load()

    # With voltage back in, the two components now differ — two groups.
    assert (
        len(items) == 2
    ), f"Expected 2 groups (voltage now discriminates), got {len(items)}"
    cids = {i.component_id for i in items}
    assert any("V=5V" in cid for cid in cids)
