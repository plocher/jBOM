"""
Functional tests for Federation Logic.
Covering: Multi-source loading, conflict resolution, and missing data handling.
"""
from jbom.loaders.inventory import InventoryLoader
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.common.types import Component
from .test_functional_base import FunctionalTestBase


class TestFunctionalFederation(FunctionalTestBase):
    def test_multi_source_conflict_resolution(self):
        """Test: Load same IPN from multiple sources, verify precedence."""
        # Source 1: JLC Export (Lower priority in our logic?)
        # Source 2: Local CSV (Higher priority user override)

        # Create Source 1
        src1 = self.output_dir / "jlc_export.csv"
        with open(src1, "w") as f:
            f.write("IPN,Category,Value,Package,Description,Priority\n")
            f.write("RES-10K,Resistor,10k,0603,JLC Default,2\n")  # Priority 2

        # Create Source 2
        src2 = self.output_dir / "local_override.csv"
        with open(src2, "w") as f:
            f.write("IPN,Category,Value,Package,Description,Priority\n")
            f.write(
                "RES-10K,Resistor,10k,0603,Local Override,1\n"
            )  # Priority 1 (Better)

        # Load both
        loader = InventoryLoader([src1, src2])
        items, _ = loader.load()

        # We expect 2 items with same IPN? Or should loader merge them?
        # Current logic: InventoryMatcher will see both.
        # Matcher should pick the one with better Priority (1).

        matcher = InventoryMatcher(None)
        matcher.set_inventory(items, [])

        # Mock component matching RES-10K
        comp = Component("R1", "Device:R", "10k", "Resistor_SMD:R_0603_1608Metric")

        matches = matcher.find_matches(comp)

        # Expect best match to be the Local Override (Priority 1)
        self.assertTrue(len(matches) >= 1)
        best_item = matches[0][0]
        self.assertEqual(best_item.description, "Local Override")
        self.assertEqual(best_item.priority, 1)

    def test_missing_data_handling(self):
        """Test: Inventory item missing 'Package' field."""
        # CSV missing package
        src = self.output_dir / "missing_pkg.csv"
        with open(src, "w") as f:
            f.write("IPN,Category,Value,Package\n")
            f.write("RES-10K,Resistor,10k,\n")  # Empty package

        loader = InventoryLoader(src)
        items, _ = loader.load()

        matcher = InventoryMatcher(None)
        matcher.set_inventory(items, [])

        # Component needs 0603
        comp = Component("R1", "Device:R", "10k", "Resistor_SMD:R_0603_1608Metric")

        # If package is missing in inventory, strict package matching should FAIL
        # unless we have a "wildcard" policy or "unknown package" policy.
        # Current logic: If comp_pkg is known (0603), and item package is empty/different, it fails.
        matches = matcher.find_matches(comp)

        # Should be NO match because inventory has no package to confirm it fits 0603
        self.assertEqual(len(matches), 0)
