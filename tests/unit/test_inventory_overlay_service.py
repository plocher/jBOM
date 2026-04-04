"""Unit tests for InventoryOverlayService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from jbom.common.component_utils import derive_package_from_footprint
from jbom.config.defaults import FieldSynonymConfig, InventorySchemaConfig
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.inventory_overlay_service import InventoryOverlayService


class _StubInventoryMatcher:
    """Test double for InventoryMatcher used by overlay service tests."""

    def __init__(self, result: BOMData):
        self.result = result
        self.calls: list[tuple[Path, str, str | None]] = []

    def enhance_bom_with_inventory(
        self,
        bom_data: BOMData,
        inventory_file: Path,
        *,
        fabricator_id: str = "generic",
        project_name: str | None = None,
        include_inventory_dnp: bool = False,
    ) -> BOMData:
        self.calls.append(
            (inventory_file, fabricator_id, project_name, include_inventory_dnp)
        )
        return self.result


def test_overlay_without_inventory_adds_i_package_fallback() -> None:
    service = InventoryOverlayService()
    bom_data = BOMData(
        project_name="Demo",
        entries=[
            BOMEntry(
                references=["D1"],
                value="LED",
                footprint="SignalMast-ColorLight-SingleHead:0603-LED",
                quantity=1,
                attributes={},
            )
        ],
    )

    result = service.overlay_bom_data(
        bom_data,
        inventory_file=None,
        fabricator_id="jlc",
        project_name="Demo",
    )

    assert result.bom_data.entries[0].attributes["i:package"] == "0603-LED"
    assert result.bom_data.metadata["inventory_overlay_mode"] == "project_fallback_only"


def test_overlay_with_inventory_projects_i_namespace_fields() -> None:
    matched_entry = BOMEntry(
        references=["R1"],
        value="10k",
        footprint="Resistor_SMD:R_0603_1608Metric",
        quantity=1,
        attributes={
            "inventory_matched": True,
            "manufacturer": "Yageo",
            "manufacturer_part": "RC0603",
            "package": "0603",
            "smd": True,
        },
    )
    matcher_result = BOMData(project_name="Demo", entries=[matched_entry], metadata={})
    matcher = _StubInventoryMatcher(matcher_result)
    service = InventoryOverlayService(inventory_matcher=matcher)

    result = service.overlay_bom_data(
        BOMData(project_name="Demo", entries=[]),
        inventory_file=Path("/tmp/inventory.csv"),
        fabricator_id="jlc",
        project_name="Demo",
    )

    assert matcher.calls == [(Path("/tmp/inventory.csv"), "jlc", "Demo", False)]
    attributes = result.bom_data.entries[0].attributes
    assert attributes["i:manufacturer"] == "Yageo"
    assert attributes["i:manufacturer_part"] == "RC0603"
    assert attributes["i:package"] == "0603"
    assert attributes["i:smd"] == "Yes"
    assert result.bom_data.metadata["inventory_overlay_mode"] == "inventory_applied"


def test_overlay_without_inventory_match_does_not_project_non_package_fields() -> None:
    unmatched = BOMEntry(
        references=["R2"],
        value="1k",
        footprint="Resistor_SMD:R_0603_1608Metric",
        quantity=1,
        attributes={"manufacturer": "Yageo"},
    )
    service = InventoryOverlayService()

    result = service.overlay_bom_data(
        BOMData(project_name="Demo", entries=[unmatched]),
        inventory_file=None,
        fabricator_id="generic",
        project_name="Demo",
    )

    attributes = result.bom_data.entries[0].attributes
    assert "i:manufacturer" not in attributes
    assert attributes["i:package"] == derive_package_from_footprint(
        "Resistor_SMD:R_0603_1608Metric"
    )


def test_namespace_fields_are_loaded_from_defaults_inventory_schema() -> None:
    class _StubDefaults:
        def get_inventory_schema(self) -> InventorySchemaConfig:
            return InventorySchemaConfig(
                canonical_fields=("inventory_ipn", "manufacturer_part"),
                field_synonyms={
                    "inventory_ipn": FieldSynonymConfig(
                        display_name="IPN",
                        synonyms=("ipn",),
                    )
                },
                enrichment_bindings={
                    "inventory_ipn": "ipn",
                    "manufacturer_part": "mfgpn",
                },
            )

    with patch(
        "jbom.services.inventory_overlay_service.get_defaults",
        return_value=_StubDefaults(),
    ):
        service = InventoryOverlayService()

    assert service.namespace_fields == ("inventory_ipn", "manufacturer_part")
