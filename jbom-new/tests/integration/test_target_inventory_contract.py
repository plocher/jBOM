"""Targeted inventory contract tests (data drift vs code regression).

These tests load a *real* inventory CSV (by default the repo example inventory)
then validate a small set of expectations that represent an implied contract:
- the inventory is loadable by InventoryReader
- specific known items exist (sentinel IPNs)
- known schematic-like components match those items

Failure mode differentiation:
- If a previously-expected match disappears BUT the expected item is still
  present in the inventory, treat it as a matcher regression.
- If the expected item is no longer present, treat it as data drift / contract
  change (inventory fixture changed).

Run control:
- These tests are marked as "contract" so they can be excluded from CI if
  desired.
- Override the inventory path with JBOM_TEST_INVENTORY_CSV.

Task: Phase 1 / Task 1.6.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from jbom.common.types import Component, InventoryItem
from jbom.services.inventory_reader import InventoryReader
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


def _repo_root() -> Path:
    # .../jBOM/jbom-new/tests/integration/test_target_inventory_contract.py
    # We want the *jBOM* repo root (sibling of jbom-new/), since that's where the
    # shared examples/ inventory lives.
    return Path(__file__).resolve().parents[3]


def _default_inventory_csv() -> Path:
    return _repo_root() / "examples" / "SPCoast-INVENTORY.csv"


def _target_inventory_csv() -> Path:
    if override := os.environ.get("JBOM_TEST_INVENTORY_CSV"):
        return Path(override).expanduser().resolve()
    return _default_inventory_csv()


@pytest.fixture(scope="session")
def target_inventory_csv() -> Path:
    return _target_inventory_csv()


@pytest.fixture(scope="session")
def target_inventory_items(target_inventory_csv: Path) -> list[InventoryItem]:
    if not target_inventory_csv.exists():
        pytest.skip(f"Missing targeted inventory CSV: {target_inventory_csv}")

    reader = InventoryReader(target_inventory_csv)
    items, _fields = reader.load()
    return items


@pytest.fixture()
def matcher() -> SophisticatedInventoryMatcher:
    return SophisticatedInventoryMatcher(MatchingOptions())


def _make_component(
    *,
    reference: str,
    lib_id: str,
    value: str,
    footprint: str,
    properties: dict[str, str] | None = None,
) -> Component:
    return Component(
        reference=reference,
        lib_id=lib_id,
        value=value,
        footprint=footprint,
        properties=properties or {},
    )


@dataclass(frozen=True)
class ExpectedMatch:
    name: str
    component: Component
    expected_ipn: str
    expected_package: str | None = None


def _inventory_contains_ipn(inventory: list[InventoryItem], ipn: str) -> bool:
    return any(i.ipn == ipn for i in inventory)


def _diagnose_primary_filter(
    *,
    matcher: SophisticatedInventoryMatcher,
    component: Component,
    item: InventoryItem,
) -> tuple[bool, str]:
    """Return (passes, reason) for primary filtering.

    This intentionally mirrors :meth:`SophisticatedInventoryMatcher._passes_primary_filters`.
    It exists purely to produce actionable test failure messages.
    """

    from jbom.common.component_classification import get_component_type
    from jbom.common.constants import ComponentType
    from jbom.common.package_matching import extract_package_from_footprint
    from jbom.common.value_parsing import (
        parse_cap_to_farad,
        parse_ind_to_henry,
        parse_res_to_ohms,
    )

    comp_type = get_component_type(component.lib_id, component.footprint)
    comp_pkg = extract_package_from_footprint(component.footprint)

    # 1) Type/category.
    if comp_type:
        cat = (item.category or "").upper()
        if comp_type not in cat:
            return (
                False,
                f"type/category mismatch (comp_type={comp_type!r}, item.category={item.category!r})",
            )

    # 2) Package.
    if comp_pkg:
        ipkg = (item.package or "").lower()
        if comp_pkg not in ipkg:
            return (
                False,
                f"package mismatch (comp_pkg={comp_pkg!r}, item.package={item.package!r})",
            )

    # 3) Value.
    comp_val_norm = matcher._normalize_value(component.value) if component.value else ""
    if comp_val_norm:
        if comp_type == ComponentType.RESISTOR:
            comp_num = parse_res_to_ohms(component.value)
            inv_num = parse_res_to_ohms(item.value)
            if comp_num is None or inv_num is None:
                return (
                    False,
                    f"resistance parse failed (comp_num={comp_num!r}, inv_num={inv_num!r})",
                )
            if abs(comp_num - inv_num) > 1e-12:
                return (
                    False,
                    f"resistance mismatch (comp_ohms={comp_num}, inv_ohms={inv_num})",
                )
        elif comp_type == ComponentType.CAPACITOR:
            comp_num = parse_cap_to_farad(component.value)
            inv_num = parse_cap_to_farad(item.value)
            if comp_num is None or inv_num is None:
                return (
                    False,
                    f"capacitance parse failed (comp_num={comp_num!r}, inv_num={inv_num!r})",
                )
            if abs(comp_num - inv_num) > 1e-18:
                return (
                    False,
                    f"capacitance mismatch (comp_f={comp_num}, inv_f={inv_num})",
                )
        elif comp_type == ComponentType.INDUCTOR:
            comp_num = parse_ind_to_henry(component.value)
            inv_num = parse_ind_to_henry(item.value)
            if comp_num is None or inv_num is None:
                return (
                    False,
                    f"inductance parse failed (comp_num={comp_num!r}, inv_num={inv_num!r})",
                )
            if abs(comp_num - inv_num) > 1e-18:
                return (
                    False,
                    f"inductance mismatch (comp_h={comp_num}, inv_h={inv_num})",
                )
        else:
            inv_val_norm = matcher._normalize_value(item.value) if item.value else ""
            if not inv_val_norm or inv_val_norm != comp_val_norm:
                return (
                    False,
                    f"normalized value mismatch (comp_val={comp_val_norm!r}, inv_val={inv_val_norm!r})",
                )

    return True, "passes"


def _assert_expected_match_or_classify_failure(
    *,
    matcher: SophisticatedInventoryMatcher,
    inventory: list[InventoryItem],
    expected: ExpectedMatch,
) -> None:
    """Assert that a component matches a particular IPN, classifying failures.

    The goal is to make failures immediately actionable:
    - If the expected IPN is present but no longer matched => code regression
    - If the expected IPN is missing => inventory drift / contract change
    """

    results = matcher.find_matches(expected.component, inventory)

    comp = expected.component
    comp_summary = (
        f"component(reference={comp.reference!r}, lib_id={comp.lib_id!r}, "
        f"value={comp.value!r}, footprint={comp.footprint!r})"
    )

    def _format_candidate(r: Any) -> str:
        item = r.inventory_item
        return (
            f"ipn={item.ipn!r}, category={item.category!r}, value={item.value!r}, "
            f"package={item.package!r}, priority={item.priority}, score={r.score}"
        )

    # If we have an expected package, validate the inventory still claims it for the
    # expected IPN. This is a contract check (drift), not a matcher check.
    if expected.expected_package is not None:
        for item in inventory:
            if (
                item.ipn == expected.expected_ipn
                and item.package != expected.expected_package
            ):
                raise AssertionError(
                    "CONTRACT FAILURE (data drift): expected inventory item changed.\n"
                    f"- expectation: {expected.name}\n"
                    f"- expected_ipn: {expected.expected_ipn!r}\n"
                    f"- expected_package: {expected.expected_package!r}\n"
                    f"- actual_package: {item.package!r}\n"
                    f"- {comp_summary}\n"
                    "Action: update the contract expectation or restore the inventory row."
                )

    # Happy path: expected IPN appears anywhere in the match set.
    if any(r.inventory_item.ipn == expected.expected_ipn for r in results):
        return

    expected_ipn_present = _inventory_contains_ipn(inventory, expected.expected_ipn)

    # Prepare a useful preview of what the matcher *is* choosing now.
    candidates_preview = (
        "\n".join(f"  - { _format_candidate(r) }" for r in results[:5])
        if results
        else "  (no matches)"
    )

    if expected_ipn_present:
        expected_item = next(i for i in inventory if i.ipn == expected.expected_ipn)
        passes, reason = _diagnose_primary_filter(
            matcher=matcher, component=expected.component, item=expected_item
        )
        expected_score = (
            matcher._calculate_match_score(expected.component, expected_item)
            if passes
            else None
        )

        raise AssertionError(
            "MATCH REGRESSION (code failure): expected IPN is present, but matcher no longer selects it.\n"
            f"- expectation: {expected.name}\n"
            f"- expected_ipn: {expected.expected_ipn!r} (present in inventory)\n"
            f"- expected_item: category={expected_item.category!r}, "
            f"value={expected_item.value!r}, package={expected_item.package!r}, "
            f"priority={expected_item.priority}\n"
            f"- primary_filter: {'PASS' if passes else 'FAIL'} ({reason})\n"
            f"- expected_score_if_included (diagnostic only): {expected_score!r}\n"
            f"- {comp_summary}\n"
            "- top_candidates (current matcher output):\n"
            f"{candidates_preview}\n"
            "Action: if primary_filter FAIL -> investigate filter logic/value parsing/"
            "package extraction/type detection. If primary_filter PASS -> investigate "
            "scoring/ordering differences that could remove or de-prioritize the expected IPN."
        )

    raise AssertionError(
        "CONTRACT FAILURE (data drift): expected IPN is missing from inventory.\n"
        f"- expectation: {expected.name}\n"
        f"- expected_ipn: {expected.expected_ipn!r} (NOT present in inventory)\n"
        f"- {comp_summary}\n"
        "Action: update the contract expectations (new sentinel) or restore the missing inventory row."
    )


@pytest.mark.contract
class TestTargetInventoryContract:
    def test_inventory_loads_and_contains_sentinel_items(
        self, target_inventory_csv: Path, target_inventory_items: list[InventoryItem]
    ) -> None:
        sentinel_ipns = {
            "RES_5%_100mW_0603_10k",
            "CAP_0.1uF_X7R_0603",
            "LED_Red _0603",
        }

        missing = {
            ipn
            for ipn in sentinel_ipns
            if not _inventory_contains_ipn(target_inventory_items, ipn)
        }
        if missing:
            raise AssertionError(
                "CONTRACT FAILURE (data drift): targeted inventory is missing sentinel items.\n"
                f"- inventory_csv: {str(target_inventory_csv)!r}\n"
                f"- missing_ipns: {sorted(missing)!r}\n"
                "Action: either restore these rows in the targeted inventory, or update "
                "the sentinel set to reflect the new inventory contract."
            )

    def test_known_components_match_expected_items_or_classify_drift(
        self,
        matcher: SophisticatedInventoryMatcher,
        target_inventory_items: list[InventoryItem],
    ) -> None:
        expectations = [
            ExpectedMatch(
                name="resistor 10k 0603",
                component=_make_component(
                    reference="R1",
                    lib_id="Device:R",
                    value="10k",
                    footprint="R_0603_1608Metric",
                    properties={"Tolerance": "5%"},
                ),
                expected_ipn="RES_5%_100mW_0603_10k",
                expected_package="0603",
            ),
            ExpectedMatch(
                name="capacitor 100nF 0603",
                component=_make_component(
                    reference="C1",
                    lib_id="Device:C",
                    value="100nF",
                    footprint="C_0603_1608Metric",
                ),
                # The contract says 100nF should match the existing 0.1uF X7R option.
                expected_ipn="CAP_0.1uF_X7R_0603",
                expected_package="0603",
            ),
            ExpectedMatch(
                name="LED red 0603",
                component=_make_component(
                    reference="D1",
                    lib_id="Device:LED",
                    value="Red",
                    footprint="LED_0603_1608Metric",
                ),
                expected_ipn="LED_Red _0603",
                expected_package="0603",
            ),
        ]

        for expected in expectations:
            _assert_expected_match_or_classify_failure(
                matcher=matcher,
                inventory=target_inventory_items,
                expected=expected,
            )

    def test_ordering_invariant_priority_asc_score_desc_for_known_resistor(
        self,
        matcher: SophisticatedInventoryMatcher,
        target_inventory_items: list[InventoryItem],
    ) -> None:
        component = _make_component(
            reference="R1",
            lib_id="Device:R",
            value="10k",
            footprint="R_0603_1608Metric",
            properties={"Tolerance": "5%"},
        )

        results = matcher.find_matches(component, target_inventory_items)
        if not results:
            raise AssertionError(
                "MATCH REGRESSION (code failure): expected at least one match for resistor 10k 0603"
            )

        # If the expected inventory items are present, assert the known ordering.
        expected_ipn = "RES_5%_100mW_0603_10k"
        if not _inventory_contains_ipn(target_inventory_items, expected_ipn):
            raise AssertionError(
                "CONTRACT FAILURE (data drift): expected resistor IPN no longer present: "
                f"{expected_ipn}"
            )

        # Phase 4 inventory schema collapses duplicates to one row per IPN, so we
        # only assert the *best* match is the expected IPN.
        top1 = results[0]
        assert top1.inventory_item.ipn == expected_ipn

        # Same priority should order by score desc.
        for a, b in zip(results, results[1:]):
            if a.inventory_item.priority == b.inventory_item.priority:
                assert a.score >= b.score
            else:
                assert a.inventory_item.priority <= b.inventory_item.priority
