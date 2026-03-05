"""Unit tests for PartsListGenerator electro-mechanical aggregation behavior."""

from __future__ import annotations

from jbom.common.types import Component
from jbom.services.parts_list_generator import PartsListGenerator


def _component(
    reference: str,
    value: str,
    footprint: str,
    *,
    package: str = "",
    part_type: str = "",
    tolerance: str = "",
    voltage: str = "",
    dielectric: str = "",
    manufacturer: str = "",
) -> Component:
    properties: dict[str, str] = {}
    if package:
        properties["Package"] = package
    if part_type:
        properties["Type"] = part_type
    if tolerance:
        properties["Tolerance"] = tolerance
    if voltage:
        properties["Voltage"] = voltage
    if dielectric:
        properties["Dielectric"] = dielectric
    if manufacturer:
        properties["Manufacturer"] = manufacturer

    return Component(
        reference=reference,
        lib_id="Device:Generic",
        value=value,
        footprint=footprint,
        properties=properties,
    )


def test_parts_are_aggregated_by_electro_mechanical_identity() -> None:
    components = [
        _component(
            "R1",
            "10K",
            "R_0603_1608",
            package="0603",
            part_type="ThickFilm",
            tolerance="1%",
            voltage="50V",
            manufacturer="Yageo",
        ),
        _component(
            "R2",
            "10K",
            "R_0603_1608",
            package="0603",
            part_type="ThickFilm",
            tolerance="1%",
            voltage="50V",
            manufacturer="Vishay",
        ),
        _component(
            "C1",
            "100nF",
            "C_0603_1608",
            package="0603",
            part_type="Ceramic",
            tolerance="10%",
            voltage="25V",
            dielectric="X7R",
        ),
    ]

    data = PartsListGenerator().generate_parts_list_data(
        components, project_name="Test"
    )

    assert len(data.entries) == 2
    resistors = [e for e in data.entries if e.value == "10K"]
    assert len(resistors) == 1
    assert resistors[0].refs == ["R1", "R2"]


def test_parts_do_not_aggregate_when_package_differs() -> None:
    components = [
        _component("R1", "10K", "R_0805_2012", package="0603"),
        _component("R2", "10K", "R_0805_2012", package="0805"),
    ]

    data = PartsListGenerator().generate_parts_list_data(
        components, project_name="Test"
    )

    assert len(data.entries) == 2
    assert data.entries[0].refs == ["R1"]
    assert data.entries[1].refs == ["R2"]


def test_refs_are_sorted_naturally_within_aggregated_row() -> None:
    components = [
        _component("R10", "10K", "R_0603_1608"),
        _component("R2", "10K", "R_0603_1608"),
        _component("R1", "10K", "R_0603_1608"),
    ]

    data = PartsListGenerator().generate_parts_list_data(
        components, project_name="Test"
    )

    assert len(data.entries) == 1
    assert data.entries[0].refs == ["R1", "R2", "R10"]
