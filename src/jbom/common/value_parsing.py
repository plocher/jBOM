"""Value parsing utilities.

This module contains pure functions for parsing common EIA-style component values
and formatting numeric values back into common schematic/inventory strings.

Ported from legacy jBOM `src/jbom/common/values.py` as part of Phase 1 matcher
extraction.

The functions here are intentionally simple and side-effect free.
"""

from __future__ import annotations

import re
from typing import Optional

from jbom.common.component_classification import normalize_component_type

__all__ = [
    "parse_res_to_ohms",
    "parse_value_to_normal",
    "ohms_to_eia",
    "cap_unit_multiplier",
    "parse_cap_to_farad",
    "farad_to_eia",
    "ind_unit_multiplier",
    "parse_ind_to_henry",
    "henry_to_eia",
]

_OHM_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([kKmMrR]?)\s*\+?\s*$")


def _parse_voltage_to_volts(value: str) -> Optional[float]:
    """Parse a voltage string into volts.

    Examples:
        - "3.3V" -> 3.3
        - "600mV" -> 0.6

    Returns:
        Parsed voltage in volts, or None if parsing fails.
    """

    if not value:
        return None

    t = str(value).strip().lower().replace(" ", "")
    t = t.replace("μ", "u").replace("µ", "u")

    # Common forms: 3.3v, 600mv
    m = re.match(r"^([0-9]*\.?[0-9]+)(mv|v)$", t)
    if not m:
        return None

    num = float(m.group(1))
    unit = m.group(2)
    if unit == "mv":
        return num * 1e-3
    return num


def parse_value_to_normal(category: str, text: str) -> Optional[float]:
    """Parse a value string to SI base units for the given component category.

    Args:
        category: Normalized component type string as returned by
            normalize_component_type() — e.g. "RES", "CAP", "IND", "REG".
        text: Raw value string from inventory or supplier attribute.

    Returns:
        float in SI base units (ohms, farads, henries, volts), or None if the value
        is unparseable or the category is unsupported.

    Notes:
        This API intentionally returns numeric canonical values only. For component
        categories whose "Value" field is not meaningfully numeric (e.g. LEDs as
        color, diodes as part numbers), this returns None.
    """

    cat = normalize_component_type(category or "")
    if not cat:
        return None

    if cat == "RES":
        return parse_res_to_ohms(text)
    if cat == "CAP":
        return parse_cap_to_farad(text)
    if cat == "IND":
        return parse_ind_to_henry(text)
    if cat == "REG":
        return _parse_voltage_to_volts(text)

    return None


def parse_res_to_ohms(value: str) -> Optional[float]:
    """Parse a resistor value string into ohms.

    Supports EIA-style formats commonly seen in KiCad fields and inventory files.

    Examples:
        - "10K" -> 10000.0
        - "2M2" -> 2200000.0
        - "0R22" -> 0.22
        - "4R7" -> 4.7
        - "47" -> 47.0

    Args:
        value: Resistance string.

    Returns:
        Parsed resistance in ohms, or None if parsing fails.
    """
    if not value:
        return None

    t = value.strip()
    t = t.replace("Ω", "").replace("ω", "")
    t = re.sub(r"(?i)ohms?", "", t)
    t = t.replace(" ", "")
    t = t.upper()

    # Decimal marked via R/K/M, e.g. 0R22, 4K7, 2M2.
    m = re.match(r"^([0-9]*)R([0-9]+)$", t)
    if m:
        left = m.group(1) or "0"
        right = m.group(2)
        return float(f"{left}.{right}")

    m = re.match(r"^([0-9]*)K([0-9]*)$", t)
    if m:
        left = m.group(1) or "0"
        right = m.group(2) or "0"
        return float(f"{left}.{right}") * 1e3

    m = re.match(r"^([0-9]*)M([0-9]*)$", t)
    if m:
        left = m.group(1) or "0"
        right = m.group(2) or "0"
        return float(f"{left}.{right}") * 1e6

    # Basic forms: 10K, 47R, 1.2K.
    m = _OHM_RE.match(t)
    if not m:
        # Handle compact forms like 10K0, 1M0.
        m2 = re.match(r"^([0-9]+)([RKM])[0]+$", t)
        if m2:
            base = float(m2.group(1))
            unit = m2.group(2)
            if unit == "R":
                return base
            if unit == "K":
                return base * 1e3
            if unit == "M":
                return base * 1e6
        return None

    num = float(m.group(1))
    suffix = m.group(2).upper()
    if suffix == "K":
        num *= 1e3
    elif suffix == "M":
        num *= 1e6

    return num


def ohms_to_eia(ohms: Optional[float], *, force_trailing_zero: bool = False) -> str:
    """Format an ohms value into an EIA-style resistor string.

    Examples:
        - 10000 -> "10K"
        - 2200000 -> "2M2"
        - 0.22 -> "0R22"

    Args:
        ohms: Resistance in ohms.
        force_trailing_zero: If True, formats 10k as "10K0" / 1M as "1M0".

    Returns:
        EIA-style resistance string, or empty string if input is None.
    """
    if ohms is None:
        return ""

    if ohms >= 1e6:
        val = ohms / 1e6
        s = f"{val:.3g}"
        if s.endswith(".0"):
            s = s[:-2]
        if "." in s:
            return s.replace(".", "M")
        return s + ("M0" if force_trailing_zero else "M")

    if ohms >= 1e3:
        val = ohms / 1e3
        s = f"{val:.3g}"
        if s.endswith(".0"):
            s = s[:-2]
        if "." in s:
            return s.replace(".", "K")
        return s + ("K0" if force_trailing_zero else "K")

    if ohms >= 1:
        if abs(ohms - round(ohms)) < 1e-9:
            return f"{int(round(ohms))}R"
        s = f"{ohms:.3g}".rstrip("0").rstrip(".")
        return s.replace(".", "R")

    s = f"{ohms:.2g}"
    if "." in s:
        left, right = s.split(".")
        return f"{left}R{right}"
    return f"0R{s}"


def cap_unit_multiplier(unit: str) -> float:
    """Get the multiplier for a capacitor unit prefix.

    Args:
        unit: One of "p", "n", "u", "m", "f" (case-insensitive). "" means farads.

    Returns:
        Multiplier to convert the numeric part into farads.
    """
    u = unit.lower()
    return {
        "f": 1.0,
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "": 1.0,
    }.get(u, 1.0)


def parse_cap_to_farad(value: str) -> Optional[float]:
    """Parse a capacitor value string into farads.

    Examples:
        - "100nF" -> 1e-7
        - "1u0" -> 1e-6
        - "220pF" -> 2.2e-10

    Args:
        value: Capacitance string.

    Returns:
        Parsed capacitance in farads, or None if parsing fails.
    """
    if not value:
        return None

    t = value.strip().lower().replace("μ", "u").replace("µ", "u")
    t = t.replace(" ", "")

    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([fpnum]?)(f)?$", t)
    if not m:
        # Handle compact forms like 100n0.
        m2 = re.match(r"^([0-9]+)([fpnum])0$", t)
        if m2:
            base = float(m2.group(1))
            unit = m2.group(2)
            return base * cap_unit_multiplier(unit)
        return None

    val = float(m.group(1))
    unit = m.group(2) or ""
    return val * cap_unit_multiplier(unit)


def farad_to_eia(farad: Optional[float]) -> str:
    """Format a farad value into a compact capacitor string.

    Examples:
        - 1e-6 -> "1uF"
        - 1e-7 -> "100nF"
        - 2.2e-10 -> "220pF"

    Args:
        farad: Capacitance in farads.

    Returns:
        Capacitor value string (with unit suffix), or empty string if input is None.
    """
    if farad is None:
        return ""

    if farad >= 1e-6:
        v = farad / 1e-6
        s = f"{v:.3g}"
        if s.endswith(".0"):
            s = s[:-2]
        if "." in s:
            return s.replace(".", "u") + "F"
        return s + "uF"

    if farad >= 1e-9:
        v = farad / 1e-9
        s = f"{v:.3g}"
        if s.endswith(".0"):
            s = s[:-2]
        if "." in s:
            return s.replace(".", "n") + "F"
        return s + "nF"

    v = farad / 1e-12
    s = f"{v:.3g}"
    if s.endswith(".0"):
        s = s[:-2]
    if "." in s:
        return s.replace(".", "p") + "F"
    return s + "pF"


def ind_unit_multiplier(unit: str) -> float:
    """Get the multiplier for an inductor unit prefix.

    Args:
        unit: One of "n", "u", "m" (case-insensitive). "" means henries.

    Returns:
        Multiplier to convert the numeric part into henries.
    """
    u = unit.lower()
    return {
        "": 1.0,
        "m": 1e-3,
        "u": 1e-6,
        "n": 1e-9,
    }.get(u, 1.0)


def parse_ind_to_henry(value: str) -> Optional[float]:
    """Parse an inductor value string into henries.

    Examples:
        - "10uH" -> 1e-5
        - "2m2" -> 0.0022

    Args:
        value: Inductance string.

    Returns:
        Parsed inductance in henries, or None if parsing fails.
    """
    if not value:
        return None

    t = value.strip().lower().replace("μ", "u").replace("µ", "u")
    t = t.replace(" ", "")
    t = t.replace("h", "")

    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([num]?)$", t)
    if not m:
        # Handle compact forms like 2m2.
        m2 = re.match(r"^([0-9]+)([num])([0-9]+)$", t)
        if m2:
            left = m2.group(1)
            unit = m2.group(2)
            right = m2.group(3)
            val = float(f"{left}.{right}")
            return val * ind_unit_multiplier(unit)
        return None

    val = float(m.group(1))
    unit = m.group(2) or ""
    return val * ind_unit_multiplier(unit)


def henry_to_eia(henry: Optional[float]) -> str:
    """Format a henry value into a compact inductor string.

    Examples:
        - 1e-3 -> "1mH"
        - 1e-6 -> "1uH"
        - 1e-9 -> "1nH"

    Args:
        henry: Inductance in henries.

    Returns:
        Inductor value string (with unit suffix), or empty string if input is None.
    """
    if henry is None:
        return ""

    if henry >= 1e-3:
        v = henry / 1e-3
        s = f"{v:.3g}"
        if s.endswith(".0"):
            s = s[:-2]
        if "." in s:
            return s.replace(".", "m") + "H"
        return s + "mH"

    if henry >= 1e-6:
        v = henry / 1e-6
        s = f"{v:.3g}"
        if s.endswith(".0"):
            s = s[:-2]
        if "." in s:
            return s.replace(".", "u") + "H"
        return s + "uH"

    v = henry / 1e-9
    s = f"{v:.3g}"
    if s.endswith(".0"):
        s = s[:-2]
    if "." in s:
        return s.replace(".", "n") + "H"
    return s + "nH"
