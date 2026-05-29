"""Description-text and EM parser used by ``jbom promote``.

This is a deliberately small, pure-function parser that extracts the most
common electro-mechanical fields out of supplier-export descriptions and
identity columns.  The parser is intentionally conservative: it only emits a
field when the regex match has clear unit semantics.  Ambiguous matches are
left empty for downstream enrichment.

The shape used by downstream code is :class:`ParsedDescription`, which
includes a small ``provenance`` map so verbose CLI output can explain which
fields the parser populated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from jbom.common.value_parsing import (
    farad_to_eia,
    henry_to_eia,
    ohms_to_eia,
    parse_cap_to_farad,
    parse_ind_to_henry,
    parse_res_to_ohms,
)

__all__ = [
    "ParsedDescription",
    "normalize_description_text",
    "parse_description",
]


@dataclass
class ParsedDescription:
    """Structured fields extracted from a supplier-export description.

    All string fields default to empty.  Numeric typed fields are ``None``
    when not detected.  ``provenance`` maps populated field names to the
    matched text token (useful for verbose explanation).
    """

    category: str = ""
    value: str = ""
    package: str = ""
    tolerance: str = ""
    type: str = ""
    voltage: str = ""
    current: str = ""
    power: str = ""
    wavelength: str = ""
    mcd: str = ""
    angle: str = ""
    resistance: Optional[float] = None
    capacitance: Optional[float] = None
    inductance: Optional[float] = None
    provenance: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_description_text(text: str) -> str:
    """Return *text* with common unicode units normalized to ASCII."""

    if not text:
        return ""
    out = str(text)
    # Normalize micro sign variants to ASCII 'u'.
    out = out.replace("μ", "u").replace("µ", "u")
    # Normalize the ohm symbol so token regexes can be ASCII-only.
    out = out.replace("Ω", "Ohm").replace("ω", "Ohm")
    # Normalize the ± sign and stray whitespace.
    out = out.replace("±", "+/-")
    return out


_PACKAGE_TOKENS: tuple[str, ...] = (
    "0201",
    "0402",
    "0603",
    "0805",
    "1206",
    "1210",
    "1812",
    "2010",
    "2512",
    "2520",
    "2920",
    "3216",
    "3225",
    "4532",
    "5025",
    "6332",
    "SOT-23",
    "SOT23",
    "SOT-223",
    "SOT223",
    "SOT-89",
    "SOT89",
    "TO-220",
    "TO-92",
    "TO-252",
    "DPAK",
    "D2PAK",
    "SOIC-8",
    "SOIC-14",
    "SOIC-16",
    "SOIC",
    "DIP",
    "MSOP",
    "TSSOP",
    "QFN",
    "QFP",
    "TQFP",
    "LQFP",
    "BGA",
    "WLCSP",
    "SOD-123",
    "SOD-323",
    "SMA",
    "SMB",
    "SMC",
)

_PACKAGE_RE = re.compile(
    r"(?<![A-Za-z0-9])("
    + "|".join(re.escape(p) for p in _PACKAGE_TOKENS)
    + r")(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_package(text: str) -> str:
    """Return the first package token observed in *text*, or empty string."""

    if not text:
        return ""
    match = _PACKAGE_RE.search(text)
    if not match:
        return ""
    raw = match.group(1)
    # Normalize SOT-23, SOT23 etc. to a canonical "0603"-style or "SOT-23" form
    upper = raw.upper().replace(" ", "")
    if upper.startswith("SOT") and "-" not in upper:
        # SOT23 -> SOT-23 etc.
        digits = upper[3:]
        if digits.isdigit():
            return f"SOT-{digits}"
    return raw


# Tolerance like "5%", "1%", "10%", "+/-5%", "+/-10%", "100ppm".
_TOLERANCE_RE = re.compile(
    r"(?:\+/?-?\s*)?(\d+(?:\.\d+)?)\s*%|(\d+(?:\.\d+)?)\s*ppm",
    flags=re.IGNORECASE,
)


def _detect_tolerance(text: str) -> str:
    if not text:
        return ""
    match = _TOLERANCE_RE.search(text)
    if not match:
        return ""
    percent = match.group(1)
    ppm = match.group(2)
    if percent is not None:
        return f"{percent}%"
    return f"{ppm}ppm"


# Voltage: "50V", "25 V", "3.3V".  Avoid matching MV/KV by anchoring to a word boundary.
_VOLTAGE_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*V(?![A-Za-z0-9])",
)


def _detect_voltage(text: str) -> str:
    if not text:
        return ""
    match = _VOLTAGE_RE.search(text)
    if not match:
        return ""
    return f"{match.group(1)}V"


# Current: "100mA", "1A", "1.5A".  Avoid matching MA inside words.
_CURRENT_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*(mA|A)(?![A-Za-z0-9])",
)


def _detect_current(text: str) -> str:
    if not text:
        return ""
    match = _CURRENT_RE.search(text)
    if not match:
        return ""
    number = match.group(1)
    unit = match.group(2)
    return f"{number}{unit}"


# Power: "0.1W", "1W", "250mW".
_POWER_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*(mW|W)(?![A-Za-z0-9])",
)


def _detect_power(text: str) -> str:
    if not text:
        return ""
    match = _POWER_RE.search(text)
    if not match:
        return ""
    number = match.group(1)
    unit = match.group(2)
    return f"{number}{unit}"


# MLCC dielectric subtypes; order matters because NP0 should map ahead of C0G.
_DIELECTRIC_TOKENS: tuple[tuple[str, str], ...] = (
    ("NP0", "NP0"),
    ("C0G", "C0G"),
    ("X5R", "X5R"),
    ("X7R", "X7R"),
    ("X7S", "X7S"),
    ("Y5V", "Y5V"),
)


def _detect_dielectric(text: str) -> str:
    if not text:
        return ""
    upper = text.upper()
    for token, canonical in _DIELECTRIC_TOKENS:
        if re.search(rf"(?<![A-Z0-9]){token}(?![A-Z0-9])", upper):
            return canonical
    return ""


# Resistance: "10K", "4.7K", "2M2", "100R", "330Ohm", "0R22", "0.1Ohm",
# "10kOhm".  The token may be either a pure EIA form (e.g. ``10K``), or a
# numeric value followed by an Ohm suffix, optionally with a K/M/R modifier
# between the digits and the suffix (``10kOhm``, ``2.2MOhms``).
_RES_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"("
    r"\d+(?:\.\d+)?[KMR]\d*[KkMmRr]?"  # 10K, 2M2, 10K0, 4R7
    r"|\d+[KMRkmr](?=Ohms?\b|\s|$|\W)"  # 10K alone, 10kOhm
    r"|\d+(?:\.\d+)?[KMRkmr]?\s*(?:Ohm|Ohms)"  # 10kOhm, 330Ohm, 0.1Ohm
    r")"
    r"(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_resistance(text: str) -> tuple[Optional[float], str]:
    """Return (ohms, source_token) when a resistance is detected."""

    if not text:
        return None, ""
    for match in _RES_TOKEN_RE.finditer(text):
        token = match.group(1)
        normalised = re.sub(r"(?i)\s*ohms?", "", token)
        ohms = parse_res_to_ohms(normalised)
        if ohms is not None:
            return ohms, token
    return None, ""


_CAP_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?\s*(?:p|n|u|m)?F)(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_capacitance(text: str) -> tuple[Optional[float], str]:
    if not text:
        return None, ""
    for match in _CAP_TOKEN_RE.finditer(text):
        token = match.group(1)
        farads = parse_cap_to_farad(token)
        if farads is not None:
            return farads, token
    return None, ""


_IND_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?\s*(?:n|u|m)H)(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_inductance(text: str) -> tuple[Optional[float], str]:
    if not text:
        return None, ""
    for match in _IND_TOKEN_RE.finditer(text):
        token = match.group(1)
        henries = parse_ind_to_henry(token)
        if henries is not None:
            return henries, token
    return None, ""


# Wavelength: "620nm", "470 nm".
_WAVELENGTH_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d{3,4})\s*nm(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_wavelength(text: str) -> str:
    if not text:
        return ""
    match = _WAVELENGTH_RE.search(text)
    if not match:
        return ""
    return f"{match.group(1)}nm"


# Brightness: "120mcd", "1500 mcd".
_MCD_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*mcd(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_mcd(text: str) -> str:
    if not text:
        return ""
    match = _MCD_RE.search(text)
    if not match:
        return ""
    return f"{match.group(1)}mcd"


# Viewing angle: "120°" or "120 deg".
_ANGLE_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d{2,3})\s*(?:°|deg|degrees?)(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def _detect_angle(text: str) -> str:
    if not text:
        return ""
    match = _ANGLE_RE.search(text)
    if not match:
        return ""
    return f"{match.group(1)}°"


# ---------------------------------------------------------------------------
# Category derivation (string-only inputs)
# ---------------------------------------------------------------------------


_CATEGORY_HINT_TO_CANONICAL: dict[str, str] = {
    "capacitor": "CAP",
    "capacitors": "CAP",
    "ceramic capacitor": "CAP",
    "mlcc": "CAP",
    "resistor": "RES",
    "resistors": "RES",
    "inductor": "IND",
    "inductors": "IND",
    "ferrite bead": "IND",
    "ferrite": "IND",
    "led": "LED",
    "leds": "LED",
    "diode": "DIO",
    "diodes": "DIO",
    "transistor": "Q",
    "mosfet": "Q",
    "ic": "IC",
    "integrated circuit": "IC",
    "connector": "CON",
    "connectors": "CON",
    "header": "CON",
    "switch": "SWI",
    "fuse": "FUS",
    "crystal": "OSC",
    "oscillator": "OSC",
    "relay": "RLY",
}


_DESCRIPTION_KEYWORD_TO_CANONICAL: tuple[tuple[str, str], ...] = (
    ("MLCC", "CAP"),
    ("CAPACITOR", "CAP"),
    ("RESISTOR", "RES"),
    ("INDUCTOR", "IND"),
    ("FERRITE", "IND"),
    ("LED", "LED"),
    ("ZENER", "DIO"),
    ("DIODE", "DIO"),
    ("SCHOTTKY", "DIO"),
    ("MOSFET", "Q"),
    ("TRANSISTOR", "Q"),
    ("REGULATOR", "REG"),
    ("OSCILLATOR", "OSC"),
    ("CRYSTAL", "OSC"),
    ("CONNECTOR", "CON"),
    ("HEADER", "CON"),
    ("FUSE", "FUS"),
    ("SWITCH", "SWI"),
    ("RELAY", "RLY"),
)


def _normalize_category_hint(hint: str) -> str:
    if not hint:
        return ""
    lowered = hint.strip().lower()
    return _CATEGORY_HINT_TO_CANONICAL.get(lowered, "")


def _category_from_description(text: str) -> str:
    if not text:
        return ""
    upper = text.upper()
    for token, canonical in _DESCRIPTION_KEYWORD_TO_CANONICAL:
        if token in upper:
            return canonical
    return ""


def _category_from_mfgpn_or_spn(mfgpn: str, spn: str) -> str:
    upper = " ".join((mfgpn or "", spn or "")).upper()
    if not upper.strip():
        return ""
    if "CL10" in upper or "CC0" in upper or "CC1" in upper:
        return "CAP"
    if "RC0" in upper or "ERJ" in upper or "RMCF" in upper:
        return "RES"
    if "MLZ" in upper or "MLF" in upper:
        return "IND"
    return ""


def derive_category(
    *,
    category_hint: str = "",
    description: str = "",
    mfgpn: str = "",
    spn: str = "",
) -> str:
    """Return the canonical category code derived from available signals.

    Returns an empty string when no signal yields a confident category.  The
    derivation order is intentionally hint-first so users can override the
    parser by labelling their export.
    """

    canonical = _normalize_category_hint(category_hint)
    if canonical:
        return canonical
    canonical = _category_from_description(description)
    if canonical:
        return canonical
    return _category_from_mfgpn_or_spn(mfgpn, spn)


# ---------------------------------------------------------------------------
# Parser entry point
# ---------------------------------------------------------------------------


def parse_description(
    description: str,
    *,
    category_hint: str = "",
    package_hint: str = "",
    mfgpn: str = "",
    spn: str = "",
) -> ParsedDescription:
    """Parse *description* and identity hints into a :class:`ParsedDescription`.

    The parser is order-independent and tolerates fragmentary descriptions.
    Numeric typed fields populate alongside string representations of the
    same value when relevant, so canonical output can pick whichever form is
    most useful.
    """

    text = normalize_description_text(description)
    parsed = ParsedDescription()

    category = derive_category(
        category_hint=category_hint,
        description=text,
        mfgpn=mfgpn,
        spn=spn,
    )
    if category:
        parsed.category = category
        parsed.provenance["category"] = (
            category_hint.strip() or text or mfgpn or spn or ""
        )

    package = (package_hint or "").strip() or _detect_package(text)
    if package:
        parsed.package = package
        parsed.provenance["package"] = package

    tolerance = _detect_tolerance(text)
    if tolerance:
        parsed.tolerance = tolerance
        parsed.provenance["tolerance"] = tolerance

    voltage = _detect_voltage(text)
    if voltage:
        parsed.voltage = voltage
        parsed.provenance["voltage"] = voltage

    current = _detect_current(text)
    if current:
        parsed.current = current
        parsed.provenance["current"] = current

    power = _detect_power(text)
    if power:
        parsed.power = power
        parsed.provenance["power"] = power

    dielectric = _detect_dielectric(text)
    if dielectric:
        parsed.type = dielectric
        parsed.provenance["type"] = dielectric

    if parsed.category in {"CAP", ""}:
        capacitance, token = _detect_capacitance(text)
        if capacitance is not None:
            parsed.capacitance = capacitance
            parsed.value = farad_to_eia(capacitance)
            parsed.provenance["capacitance"] = token
            if not parsed.category:
                parsed.category = "CAP"

    if parsed.category in {"RES", ""}:
        resistance, token = _detect_resistance(text)
        if resistance is not None:
            parsed.resistance = resistance
            parsed.value = ohms_to_eia(resistance)
            parsed.provenance["resistance"] = token
            if not parsed.category:
                parsed.category = "RES"

    if parsed.category in {"IND", ""}:
        inductance, token = _detect_inductance(text)
        if inductance is not None:
            parsed.inductance = inductance
            parsed.value = henry_to_eia(inductance)
            parsed.provenance["inductance"] = token
            if not parsed.category:
                parsed.category = "IND"

    if parsed.category == "LED" or not parsed.category:
        wavelength = _detect_wavelength(text)
        if wavelength:
            parsed.wavelength = wavelength
            parsed.provenance["wavelength"] = wavelength
            if not parsed.category:
                parsed.category = "LED"
        mcd = _detect_mcd(text)
        if mcd:
            parsed.mcd = mcd
            parsed.provenance["mcd"] = mcd
        angle = _detect_angle(text)
        if angle:
            parsed.angle = angle
            parsed.provenance["angle"] = angle

    return parsed
