from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from jbom.common.value_parsing import (  # noqa: E402
    cap_unit_multiplier,
    farad_to_eia,
    henry_to_eia,
    ind_unit_multiplier,
    ohms_to_eia,
    parse_cap_to_farad,
    parse_ind_to_henry,
    parse_res_to_ohms,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("47", 47.0),
        ("47R", 47.0),
        ("4R7", 4.7),
        ("R47", 0.47),
        ("0R22", 0.22),
        ("10K", 10_000.0),
        ("10k", 10_000.0),
        ("10K0", 10_000.0),
        ("2K2", 2_200.0),
        ("2.2K", 2_200.0),
        ("1M", 1_000_000.0),
        ("1M0", 1_000_000.0),
        ("2M2", 2_200_000.0),
        ("10Ω", 10.0),
        ("10 ohm", 10.0),
        ("10K+", 10_000.0),
    ],
)
def test_parse_res_to_ohms_positive(value: str, expected: float) -> None:
    assert parse_res_to_ohms(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "abc",
        "10G",
        "--",
    ],
)
def test_parse_res_to_ohms_negative(value: str) -> None:
    assert parse_res_to_ohms(value) is None


@pytest.mark.parametrize(
    ("ohms", "expected"),
    [
        (None, ""),
        (47.0, "47R"),
        (4.7, "4R7"),
        (0.22, "0R22"),
        (10_000.0, "10K"),
        (2_200_000.0, "2M2"),
    ],
)
def test_ohms_to_eia_basic(ohms: float | None, expected: str) -> None:
    assert ohms_to_eia(ohms) == expected


def test_ohms_to_eia_force_trailing_zero() -> None:
    assert ohms_to_eia(10_000.0, force_trailing_zero=True) == "10K0"
    assert ohms_to_eia(1_000_000.0, force_trailing_zero=True) == "1M0"


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("p", 1e-12),
        ("n", 1e-9),
        ("u", 1e-6),
        ("m", 1e-3),
        ("", 1.0),
        ("X", 1.0),
    ],
)
def test_cap_unit_multiplier(unit: str, expected: float) -> None:
    assert cap_unit_multiplier(unit) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("100nF", 1e-7),
        ("100n", 1e-7),
        ("100n0", 1e-7),
        ("1uF", 1e-6),
        ("1u0", 1e-6),
        ("4.7uF", 4.7e-6),
        ("4.7μF", 4.7e-6),
        ("220pF", 220e-12),
        (" 220 PF ", 220e-12),
    ],
)
def test_parse_cap_to_farad_positive(value: str, expected: float) -> None:
    assert parse_cap_to_farad(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "abc",
        "10uuF",
    ],
)
def test_parse_cap_to_farad_negative(value: str) -> None:
    assert parse_cap_to_farad(value) is None


def test_parse_cap_to_farad_unitless_is_farads() -> None:
    # Ported behavior: no suffix means "farads".
    assert parse_cap_to_farad("10") == pytest.approx(10.0)


@pytest.mark.parametrize(
    ("farad", "expected"),
    [
        (None, ""),
        (1e-6, "1uF"),
        (4.7e-6, "4u7F"),
        (1e-7, "100nF"),
        (220e-12, "220pF"),
    ],
)
def test_farad_to_eia(farad: float | None, expected: str) -> None:
    assert farad_to_eia(farad) == expected


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("n", 1e-9),
        ("u", 1e-6),
        ("m", 1e-3),
        ("", 1.0),
        ("X", 1.0),
    ],
)
def test_ind_unit_multiplier(unit: str, expected: float) -> None:
    assert ind_unit_multiplier(unit) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10uH", 10e-6),
        ("10u", 10e-6),
        ("10μH", 10e-6),
        ("2m2", 0.0022),
        ("2m2H", 0.0022),
        ("3.3n", 3.3e-9),
        ("1H", 1.0),
    ],
)
def test_parse_ind_to_henry_positive(value: str, expected: float) -> None:
    assert parse_ind_to_henry(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "abc",
        "10uuH",
    ],
)
def test_parse_ind_to_henry_negative(value: str) -> None:
    assert parse_ind_to_henry(value) is None


@pytest.mark.parametrize(
    ("henry", "expected"),
    [
        (None, ""),
        (1e-3, "1mH"),
        (2.2e-3, "2m2H"),
        (1e-6, "1uH"),
        (4.7e-6, "4u7H"),
        (1e-9, "1nH"),
    ],
)
def test_henry_to_eia(henry: float | None, expected: str) -> None:
    assert henry_to_eia(henry) == expected


def test_resistor_round_trip_examples() -> None:
    for s in ["0R22", "4R7", "10K", "2M2", "10K0"]:
        parsed = parse_res_to_ohms(s)
        assert parsed is not None
        assert parse_res_to_ohms(ohms_to_eia(parsed)) == pytest.approx(parsed)
