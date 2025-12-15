"""Numeric value parsing and formatting helpers.

Phase P0: lifted from InventoryMatcher, kept API-compatible via wrappers.
"""
from __future__ import annotations
import re
from typing import Optional

__all__ = [
    "parse_res_to_ohms",
    "ohms_to_eia",
    "parse_cap_to_farad",
    "farad_to_eia",
    "cap_unit_multiplier",
    "parse_ind_to_henry",
    "henry_to_eia",
    "ind_unit_multiplier",
]

_OHM_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([kKmMrR]?)\s*\+?\s*$")

# ---- Resistors ----


def parse_res_to_ohms(s: str) -> Optional[float]:
    if not s:
        return None
    t = s.strip()
    t = t.replace("Ω", "").replace("ω", "").replace("ohm", "").replace("OHM", "")
    t = t.replace(" ", "")
    t = t.upper()
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
    m = _OHM_RE.match(t)
    if not m:
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


def ohms_to_eia(ohms: float, *, force_trailing_zero: bool = False) -> str:
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
    val = ohms
    s = f"{val:.2g}"
    if "." in s:
        left, right = s.split(".")
        return f"{left}R{right}"
    return f"0R{s}"


# ---- Capacitors ----


def cap_unit_multiplier(unit: str) -> float:
    u = unit.lower()
    return {
        "f": 1.0,
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "": 1.0,
    }.get(u, 1.0)


def parse_cap_to_farad(s: str) -> Optional[float]:
    if not s:
        return None
    t = (s or "").strip().lower().replace("μ", "u")
    t = t.replace(" ", "")
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([fpnum]?)(f)?$", t)
    if not m:
        m2 = re.match(r"^([0-9]+)([fpnum])0$", t)
        if m2:
            base = float(m2.group(1))
            unit = m2.group(2)
            return base * cap_unit_multiplier(unit)
        return None
    val = float(m.group(1))
    unit = m.group(2) or ""
    return val * cap_unit_multiplier(unit)


def farad_to_eia(farad: float) -> str:
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


# ---- Inductors ----


def ind_unit_multiplier(unit: str) -> float:
    u = unit.lower()
    return {
        "": 1.0,
        "m": 1e-3,
        "u": 1e-6,
        "n": 1e-9,
    }.get(u, 1.0)


def parse_ind_to_henry(s: str) -> Optional[float]:
    if not s:
        return None
    t = (s or "").strip().lower().replace("μ", "u")
    t = t.replace(" ", "")
    t = t.replace("h", "")
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([num]?)$", t)
    if not m:
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


def henry_to_eia(henry: float) -> str:
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
