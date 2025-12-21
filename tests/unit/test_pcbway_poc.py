"""
Functional tests for PCBWay fabricator workflow.
Demonstrates the "Detour" federated inventory flow where:
1. Schematic contains generic parts.
2. Inventory contains Distributor SKU, MFGPN, and Manufacturer info.
3. jBOM generates a BOM with PCBWay-specific columns.
"""
from jbom.common.types import Component
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.generators.bom import BOMGenerator
from jbom.common.generator import GeneratorOptions
from tests.functional.test_functional_base import FunctionalTestBase


class TestPCBWayPOC(FunctionalTestBase):
    def test_pcbway_bom_generation(self):
        """Verify PCBWay BOM generation with distributor part numbers."""

        # 1. Setup Input: Generic Schematic Components
        components = [
            Component(
                reference="R1",
                lib_id="Device:R",
                value="10k",
                footprint="Resistor_SMD:R_0603_1608Metric",
                in_bom=True,
            ),
            Component(
                reference="C1",
                lib_id="Device:C",
                value="100nF",
                footprint="Capacitor_SMD:C_0603_1608Metric",
                in_bom=True,
            ),
        ]

        # 2. Setup Input: Mock Inventory CSV with Distributor Data
        inventory_csv = self.output_dir / "distributor_inventory.csv"
        with open(inventory_csv, "w") as f:
            f.write(
                "IPN,Category,Value,Package,Manufacturer,MFGPN,Distributor,Distributor Part Number,Priority\n"
                # R1 match: 10k 0603, specific Yageo part, DigiKey SKU
                "RES-10K-0603,Resistor,10k,0603,Yageo,RC0603JR-0710KL,DigiKey,311-10KGRCT-ND,1\n"
                # C1 match: 100nF 0603, Samsung part, Mouser SKU
                "CAP-100N-0603,Capacitor,100nF,0603,Samsung,CL10B104KB8NNNC,Mouser,187-CL10B104KB8NNNC,1\n"
            )

        # 3. Execution: Load Inventory and Match
        from jbom.loaders.inventory import InventoryLoader

        loader = InventoryLoader(inventory_csv)
        inventory_items, fields = loader.load()

        matcher = InventoryMatcher(None)
        matcher.set_inventory(inventory_items, fields)

        # 4. Execution: Generate BOM for PCBWay
        options = GeneratorOptions(verbose=False, fields=None)  # Default for fabricator
        options.fabricator = "pcbway"

        generator = BOMGenerator(matcher, options)
        generator.components = (
            components  # Manually inject components to bypass file loading
        )

        bom_entries, _ = generator.process(components)

        # 5. Output Verification
        output_bom = self.output_dir / "pcbway_bom.csv"
        generator.write_csv(bom_entries, output_bom, generator._get_default_fields())

        # Check Results
        rows = self.assert_csv_valid(output_bom)
        headers = rows[0]

        # 5.1 Verify PCBWay Headers
        expected_headers = [
            "Designator",
            "Quantity",
            "Value",
            "Comment",
            "Package",
            "Distributor Part Number",
        ]
        self.assertEqual(headers, expected_headers)

        # 5.2 Verify Row Content
        # R1 Row
        r1_row = next(r for r in rows if r[0] == "R1")
        # Check available columns based on indices:
        # 0:Designator, 1:Quantity, 2:Value, 3:Comment, 4:Package, 5:Distributor Part Number
        self.assertEqual(r1_row[5], "311-10KGRCT-ND")  # Distributor SKU from inventory

        # C1 Row
        c1_row = next(r for r in rows if r[0] == "C1")
        self.assertEqual(
            c1_row[5], "187-CL10B104KB8NNNC"
        )  # Distributor SKU from inventory
