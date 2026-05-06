"""Unit tests for sophisticated matcher primary filtering (Task 1.5b)."""

from __future__ import annotations

from jbom.common.types import Component, InventoryItem
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _make_component(
    *,
    lib_id: str,
    value: str = "",
    footprint: str = "",
    reference: str = "R1",
    properties: dict[str, str] | None = None,
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        properties=properties or {},
    )


def _make_inventory_item(
    *,
    ipn: str = "IPN-1",
    category: str,
    value: str = "",
    package: str = "",
    item_type: str = "",
    description: str = "",
    tolerance: str = "",
    spn: str = "",
    name: str = "",
    aliases: str = "",
    mfgpn: str = "",
    footprint_full: str = "",
    pins: str = "",
    pitch: str = "",
    raw_data: dict[str, str] | None = None,
) -> InventoryItem:
    row = raw_data or {}
    return InventoryItem(
        ipn=ipn,
        keywords="",
        category=category,
        description=description,
        smd="",
        value=value,
        type=item_type,
        tolerance=tolerance,
        voltage="",
        amperage="",
        wattage="",
        spn=spn,
        manufacturer="",
        mfgpn=mfgpn,
        datasheet="",
        package=package,
        footprint_full=footprint_full,
        pins=pins,
        pitch=pitch,
        name=name,
        aliases=aliases,
        raw_data=row,
    )


def test_type_filter_rejects_mismatched_category() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )
    item = _make_inventory_item(category="CAP", value="10K", package="0603")

    assert matcher._passes_primary_filters(component, item) is False


def test_type_filter_skipped_when_component_type_unknown() -> None:
    # Use a neutral reference ("M1") that carries no RefDes signal, so that
    # lib_id="Foo:ABC" produces no classification and the type filter is skipped.
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(lib_id="Foo:ABC", reference="M1")
    item = _make_inventory_item(category="CAP")

    assert matcher._passes_primary_filters(component, item) is True


def test_non_passive_soic_and_so8_package_aliases_are_compatible() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="Q4",
        lib_id="Device:Q_NMOS_GSD",
        value="DMN4468LSS-13",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    )
    item = _make_inventory_item(
        ipn="Q_N-FET_10A_SOT-23_DMN4468",
        category="Q",
        value="DMN4468",
        package="SO-8",
        aliases="DMN4468LSS-13",
    )

    assert matcher._passes_primary_filters(component, item) is True


def test_non_passive_aliases_provide_identity_signal() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="U9",
        lib_id="Device:U",
        value="TLV272CS-13",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    )
    item = _make_inventory_item(
        ipn="IC_LM358D_SOP-8",
        category="IC",
        value="LM358D",
        package="SOP-8",
        aliases="LM6132A TLV272CS-13",
    )

    assert matcher._passes_primary_filters(component, item) is True


def test_package_filter_rejects_when_extracted_package_not_in_inventory_package() -> (
    None
):
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )
    item = _make_inventory_item(category="RES", value="10K", package="0805")

    assert matcher._passes_primary_filters(component, item) is False


def test_resistor_value_filter_numeric_equality() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )

    ok = _make_inventory_item(category="RES", value="10k", package="0603")
    bad = _make_inventory_item(category="RES", value="11K", package="0603")

    assert matcher._passes_primary_filters(component, ok) is True
    assert matcher._passes_primary_filters(component, bad) is False


def test_non_passive_connector_value_token_overlap_matches_ipn() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="J10",
        lib_id="SPCoast:Conn_01x02_Socket",
        value="Conn_01x02_Socket",
        footprint="SPCoast:PinSocket_1x02_P2.54mm_Vertical",
    )
    item = _make_inventory_item(
        ipn="CON_1x02-0.100-socket",
        category="CON",
        value="1x02-0.100-socket",
        raw_data={"Footprint": "SPCoast:PinSocket_1x02_P2.54mm_Vertical"},
    )

    assert matcher._passes_primary_filters(component, item) is True


def test_non_passive_soic_and_sop_package_aliases_are_compatible() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="U2",
        lib_id="cpNode-ProMini-eagle-import:SparkFun_NE555P",
        value="NE555D",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    )
    item = _make_inventory_item(
        ipn="IC_NE555D_SOP-8",
        category="IC",
        value="NE555D",
        package="SOP-8",
    )

    assert matcher._passes_primary_filters(component, item) is True


def test_non_passive_footprint_signal_recovers_free_form_value_mismatch() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="J3",
        lib_id="cpNode-ProMini-eagle-import:SPCoast_CONNECTOR-DC-POWER-RA",
        value="2.1mm",
        footprint="SPCoast:DCJ0202",
    )
    item = _make_inventory_item(
        ipn="CON_DCJ0202",
        category="CON",
        value="DCJ0202",
        raw_data={"Footprint": "SPCoast:DCJ0202"},
    )

    assert matcher._passes_primary_filters(component, item) is True


def test_socket_candidate_with_xu_ref_and_dip_structure_passes_non_passive_gate() -> (
    None
):
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="XU1",
        lib_id="SPCoast:Socket",
        value="DIP14",
        footprint="SPCoast:XS-DIP14",
    )
    item = _make_inventory_item(
        ipn="CON_DIP-14",
        category="CON",
        value="DIP-14",
        package="DIP-14",
        item_type="Socket",
        description="14P DIP IC Socket",
        footprint_full="Package_DIP:DIP-14_W7.62mm_Socket",
        pins="2x7",
        pitch="2.54mm",
        raw_data={
            "Footprint": "Package_DIP:DIP-14_W7.62mm_Socket",
            "Pins": "2x7",
            "Pitch": "2.54mm",
            "Type": "Socket",
            "Description": "14P DIP IC Socket",
        },
    )

    assert matcher._passes_primary_filters(component, item) is True


def test_socket_category_compatibility_requires_socket_intent_on_component() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="U2",
        lib_id="cpNode-ProMini-eagle-import:SparkFun_NE555P",
        value="NE555D",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    )
    item = _make_inventory_item(
        ipn="CON_DIP-14",
        category="CON",
        value="DIP-14",
        package="DIP-14",
        item_type="Socket",
        description="14P DIP IC Socket",
        footprint_full="Package_DIP:DIP-14_W7.62mm_Socket",
        pins="2x7",
        pitch="2.54mm",
        raw_data={"Footprint": "Package_DIP:DIP-14_W7.62mm_Socket", "Pins": "2x7"},
    )

    assert matcher._passes_primary_filters(component, item) is False


def test_lcsc_validation_rejects_conflicting_candidate_when_component_has_lcsc() -> (
    None
):
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="R1",
        lib_id="Device:R",
        value="10K",
        footprint="R_0603_1608Metric",
        properties={"LCSC": "C12345"},
    )
    wrong = _make_inventory_item(
        category="RES",
        value="10K",
        package="0603",
        spn="C99999",
    )

    assert matcher._passes_primary_filters(component, wrong) is False


def test_cross_category_numeric_value_signal_rejects_capacitor_value_for_ic() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="U1",
        lib_id="Device:U",
        value="0.1uF",
        footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    )
    item = _make_inventory_item(
        category="IC",
        value="0.1uF",
        package="SOIC-8",
    )

    assert matcher._passes_primary_filters(component, item) is False


def test_resistor_value_filter_uses_default_tolerance_for_nearby_values() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="10K", footprint="R_0603_1608Metric"
    )

    near = _make_inventory_item(category="RES", value="10K1", package="0603")
    far = _make_inventory_item(category="RES", value="12K", package="0603")

    assert matcher._passes_primary_filters(component, near) is True
    assert matcher._passes_primary_filters(component, far) is False


def test_resistor_tolerance_requirement_rejects_looser_candidate_tolerance() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R",
        value="10K",
        footprint="R_0603_1608Metric",
        properties={"Tolerance": "10%"},
    )

    tighter = _make_inventory_item(
        category="RES", value="10K1", package="0603", tolerance="1%"
    )
    looser = _make_inventory_item(
        category="RES", value="10K1", package="0603", tolerance="20%"
    )
    missing = _make_inventory_item(category="RES", value="10K1", package="0603")

    assert matcher._passes_primary_filters(component, tighter) is True
    assert matcher._passes_primary_filters(component, looser) is False
    assert matcher._passes_primary_filters(component, missing) is True


def test_tilde_component_value_is_treated_as_blank_constraint() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:R", value="~", footprint="R_0603_1608Metric"
    )
    item = _make_inventory_item(category="RES", value="47K", package="0603")

    # "~" means no value constraint from component side, so this passes
    # even though item.value differs.
    assert matcher._passes_primary_filters(component, item) is True


def test_capacitor_value_filter_numeric_equivalence_across_units() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:C", value="100nF", footprint="C_0603_1608Metric"
    )

    ok = _make_inventory_item(category="CAP", value="0.1uF", package="0603")
    bad = _make_inventory_item(category="CAP", value="10nF", package="0603")

    assert matcher._passes_primary_filters(component, ok) is True
    assert matcher._passes_primary_filters(component, bad) is False


def test_non_passive_value_filter_uses_normalized_string_comparison() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="Device:U", value="ATmega328", footprint="TQFP-32"
    )

    ok = _make_inventory_item(category="IC", value=" atmega328 ", package="tqfp")
    bad = _make_inventory_item(category="IC", value="ATmega328P", package="tqfp")

    assert matcher._passes_primary_filters(component, ok) is True
    assert matcher._passes_primary_filters(component, bad) is False
