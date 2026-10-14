"""Unit tests for connector matching signals (issues #403 and #404).

Covers:
- Socket intent must not be inferred from KiCad tool metadata properties
  such as ``KiLib_Generator: connector/pin_header_socket`` (#403).
- Connector gender (male/female) match and conflict signals (#404).
- Connector pin-count consistency between component footprint and
  inventory item outside the socket-pair path (#404).
"""

from __future__ import annotations

from jbom.common.types import Component, InventoryItem
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _make_component(
    *,
    reference: str = "J1",
    lib_id: str = "SPCoast:Conn_01x02",
    value: str = "",
    footprint: str = "",
    properties: dict | None = None,
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        properties=properties or {},
    )


def _make_connector_item(
    *,
    ipn: str,
    value: str,
    item_type: str = "",
    description: str = "",
    name: str = "",
    package: str = "",
    pins: str = "",
    pitch: str = "",
    keywords: str = "",
    footprint_full: str = "",
    raw_data: dict | None = None,
) -> InventoryItem:
    return InventoryItem(
        ipn=ipn,
        keywords=keywords,
        category="CON",
        description=description,
        smd="PTH",
        value=value,
        type=item_type,
        tolerance="",
        voltage="",
        amperage="",
        wattage="",
        spn="",
        manufacturer="",
        mfgpn="",
        datasheet="",
        package=package,
        footprint_full=footprint_full,
        pins=pins,
        pitch=pitch,
        name=name,
        aliases="",
        raw_data=raw_data or {},
    )


# ---------------------------------------------------------------------------
# Issue #403: tool metadata must not create socket intent
# ---------------------------------------------------------------------------


def test_socket_intent_not_inferred_from_kilib_generator_metadata() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="J12",
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        properties={"KiLib_Generator": "connector/pin_header_socket"},
    )

    assert matcher._component_has_socket_intent(component) is False


def test_socket_intent_ignores_assorted_tool_metadata_keys() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="J12",
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        properties={
            "KiLib_Generator": "connector/pin_header_socket",
            "ki_fp_filters": "PinSocket*:*_1x??_*",
            "ki_keywords": "socket header",
        },
    )

    assert matcher._component_has_socket_intent(component) is False


def test_socket_intent_handles_non_string_property_keys() -> None:
    """PCB-synthesized properties may use non-str keys (e.g. sexpdata Symbol)."""

    class FakeSymbol:
        def __init__(self, name: str) -> None:
            self._name = name

        def __str__(self) -> str:
            return self._name

        def __hash__(self) -> int:
            return hash(self._name)

        def __eq__(self, other: object) -> bool:
            return str(self) == str(other)

    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="J12",
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        properties={FakeSymbol("ki_fp_filters"): "PinSocket*:*_1x??_*"},
    )

    assert matcher._component_has_socket_intent(component) is False


def test_socket_intent_still_detected_from_user_fields() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    by_value = _make_component(
        value="Conn_01x02_Socket",
        footprint="Connector_PinSocket_2.54mm:PinSocket_1x02_P2.54mm_Vertical",
    )
    by_user_property = _make_component(
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        properties={"Note": "use machined socket here"},
    )

    assert matcher._component_has_socket_intent(by_value) is True
    assert matcher._component_has_socket_intent(by_user_property) is True


def test_regression_male_pin_header_outranks_socket_rows() -> None:
    """Regression for the cpNode-Xiao J12/J13 mismatch (#403).

    A male 1x02 pin header carrying the KiCad generator metadata (and even a
    stale 1x04 schematic value) must match the male 1x02 header row, not a
    female socket row.
    """

    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        reference="J12",
        value="1x04-2.54",  # stale value: physically a 1x02 part
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        properties={"KiLib_Generator": "connector/pin_header_socket"},
    )

    male_1x02 = _make_connector_item(
        ipn="CON_1x02-2.54",
        value="1x02-2.54",
        item_type="Male Header",
        description="1x02 0.100 / 2.54mm Header",
        name="1x02-2.54",
        package="1x02-0.100",
        keywords="1x02-2.54 CON Male Header",
        raw_data={
            "Footprint": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
        },
    )
    male_1x04 = _make_connector_item(
        ipn="CON_1x04-2.54",
        value="1x04-2.54",
        item_type="Male Header",
        description="1x04 0.100 / 2.54mm Header",
        name="1x04-2.54",
        package="1x04-0.100",
        keywords="1x04-2.54 CON Male Header",
    )
    socket_1x04 = _make_connector_item(
        ipn="CON_1x04-2.54-socket",
        value="1x04-2.54-socket",
        item_type="Female Socket",
        description="1x04 0.100 / 2.54mm Through Hole Top Female Socket",
        name="1x04-2.54-socket",
        pitch="2.54 mm",
        keywords="1x04-2.54-socket CON Female Socket",
    )
    socket_1x02 = _make_connector_item(
        ipn="CON_1x02-2.54-socket",
        value="1x02-2.54-socket",
        item_type="Female Socket",
        description="1x02 0.100 / 2.54mm Through Hole Top Female Socket",
        name="1x02-2.54-socket",
        pitch="2.54 mm",
        keywords="1x02-2.54-socket CON Female Socket",
    )

    matches = matcher.find_matches(
        component, [socket_1x04, male_1x04, socket_1x02, male_1x02]
    )

    assert matches, "expected at least one match"
    assert matches[0].inventory_item.ipn == "CON_1x02-2.54"


# ---------------------------------------------------------------------------
# Issue #404: connector gender signal
# ---------------------------------------------------------------------------


def test_connector_gender_classification() -> None:
    gender = SophisticatedInventoryMatcher._connector_gender

    assert gender("Male Header") == "male"
    assert gender("PinHeader_1x02_P2.54mm_Vertical") == "male"
    assert gender("Female Socket") == "female"
    assert gender("Female Header") == "female"
    assert gender("PinSocket_1x02_P2.54mm_Vertical") == "female"
    assert gender("1x02-2.54") == ""
    # Mixed evidence is ambiguous.
    assert gender("connector/pin_header_socket") == ""


def test_gender_conflict_prefers_matching_gender() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )

    male = _make_connector_item(
        ipn="CON_1x02-2.54",
        value="1x02-2.54",
        item_type="Male Header",
        description="1x02 0.100 / 2.54mm Header",
    )
    female = _make_connector_item(
        ipn="CON_1x02-2.54-socket",
        value="1x02-2.54",
        item_type="Female Socket",
        description="1x02 0.100 / 2.54mm Female Socket",
    )

    matches = matcher.find_matches(component, [female, male])

    assert matches
    assert matches[0].inventory_item.ipn == "CON_1x02-2.54"
    scores = {m.inventory_item.ipn: m.score for m in matches}
    if "CON_1x02-2.54-socket" in scores:
        assert scores["CON_1x02-2.54"] > scores["CON_1x02-2.54-socket"]


def test_female_component_prefers_female_item() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        lib_id="SPCoast:Conn_01x02_Socket",
        value="Conn_01x02_Socket",
        footprint="Connector_PinSocket_2.54mm:PinSocket_1x02_P2.54mm_Vertical",
    )

    male = _make_connector_item(
        ipn="CON_1x02-2.54",
        value="1x02-2.54",
        item_type="Male Header",
        description="1x02 0.100 / 2.54mm Header",
    )
    female = _make_connector_item(
        ipn="CON_1x02-2.54-socket",
        value="1x02-2.54-socket",
        item_type="Female Socket",
        description="1x02 0.100 / 2.54mm Female Socket",
        pitch="2.54 mm",
    )

    matches = matcher.find_matches(component, [male, female])

    assert matches
    assert matches[0].inventory_item.ipn == "CON_1x02-2.54-socket"


# ---------------------------------------------------------------------------
# Issue #404: connector pin-count consistency (non-socket path)
# ---------------------------------------------------------------------------


def test_pin_count_conflict_rejects_wrong_size_connector() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        value="1x04-2.54",  # stale value says 4 pins
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )
    male_1x04 = _make_connector_item(
        ipn="CON_1x04-2.54",
        value="1x04-2.54",
        item_type="Male Header",
        description="1x04 0.100 / 2.54mm Header",
        package="1x04-0.100",
    )

    assert matcher._passes_primary_filters(component, male_1x04) is False


def test_pin_count_match_accepts_right_size_connector() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )
    male_1x02 = _make_connector_item(
        ipn="CON_1x02-2.54",
        value="1x02-2.54",
        item_type="Male Header",
        description="1x02 0.100 / 2.54mm Header",
        package="1x02-0.100",
    )

    assert matcher._passes_primary_filters(component, male_1x02) is True


def test_pin_count_check_noop_when_item_has_no_pin_info() -> None:
    matcher = SophisticatedInventoryMatcher(MatchingOptions())

    component = _make_component(
        value="1x02-2.54",
        footprint="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    )
    vague_item = _make_connector_item(
        ipn="CON_header-generic",
        value="1x02-2.54",
        item_type="Male Header",
        description="breakaway header strip",
    )

    assert matcher._passes_primary_filters(component, vague_item) is True
