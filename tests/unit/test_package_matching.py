"""Unit tests for package matching utilities."""
import pytest
from jbom.common.package_matching import (
    PackageType,
    extract_package_from_footprint,
    footprint_matches_package,
)


class TestPackageType:
    """Test PackageType constants."""

    def test_smd_packages_contains_expected_packages(self):
        """SMD_PACKAGES should contain common SMD package types."""
        expected_packages = [
            "0402",
            "0603",
            "0805",
            "1206",  # Common imperial
            "1005",
            "1608",
            "2012",
            "3216",  # Common metric
            "sot-23",
            "sot-223",
            "soic",
            "qfp",
            "bga",  # Common IC packages
        ]
        for package in expected_packages:
            assert package in PackageType.SMD_PACKAGES, f"Missing package: {package}"

    def test_through_hole_packages_contains_expected_packages(self):
        """THROUGH_HOLE_PACKAGES should contain common through-hole package types."""
        expected_packages = [
            "dip",
            "through-hole",
            "axial",
            "radial",
            "to-220",
            "to-92",
        ]
        for package in expected_packages:
            assert (
                package in PackageType.THROUGH_HOLE_PACKAGES
            ), f"Missing package: {package}"

    def test_package_lists_are_lowercase(self):
        """All package names should be lowercase for consistent matching."""
        for package in PackageType.SMD_PACKAGES:
            assert package == package.lower(), f"Package '{package}' is not lowercase"

        for package in PackageType.THROUGH_HOLE_PACKAGES:
            assert package == package.lower(), f"Package '{package}' is not lowercase"


class TestExtractPackageFromFootprint:
    """Test extract_package_from_footprint function."""

    def test_extract_common_imperial_packages(self):
        """Should extract common imperial package sizes."""
        test_cases = [
            ("R_0402_1005Metric", "0402"),
            ("R_0603_1608Metric", "0603"),
            ("R_0805_2012Metric", "0805"),
            ("C_1206_3216Metric_Pad1.33x1.80mm_HandSolder", "1206"),
            ("L_1210_3225Metric", "1210"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_extract_common_metric_packages(self):
        """Should extract common metric package sizes."""
        test_cases = [
            ("R_1005_2512Metric", "1005"),
            ("C_1608_4032Metric", "1608"),
            ("R_2012_5032Metric", "2012"),
            ("C_3216_8032Metric", "3216"),
            ("L_3225_8032Metric", "3225"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_extract_sot_packages(self):
        """Should extract SOT package variants."""
        test_cases = [
            ("SOT-23", "sot-23"),
            ("SOT-23-3", "sot-23"),  # Should match longer pattern first
            ("SOT-23-5", "sot-23-5"),  # Should match exact variant
            ("SOT-23-6", "sot-23-6"),
            ("SOT-223", "sot-223"),
            ("SOT-89", "sot-89"),
            ("SOT-143", "sot-143"),
            ("SOT-323", "sot-323"),
            ("SOT-353", "sot-353"),
            ("SOT-363", "sot-363"),
            ("SC-70", "sc-70"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_extract_ic_packages(self):
        """Should extract common IC package types."""
        test_cases = [
            ("SOIC-8_3.9x4.9mm_P1.27mm", "soic"),
            ("SSOP-20_5.3x7.2mm_P0.65mm", "ssop"),
            ("TSSOP-16_4.4x5mm_P0.65mm", "tssop"),
            ("QFP-44_10x10mm_P0.8mm", "qfp"),
            ("QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm", "qfn"),
            ("DFN-8-1EP_2x2mm_P0.5mm_EP0.9x1.3mm", "dfn"),
            ("BGA-256_17x17mm_Layout16x16_P1.0mm", "bga"),
            ("WLCSP-25_2.097x2.493mm_P0.4mm", "wlcsp"),
            ("LGA-14_3x2.5mm_P0.5mm", "lga"),
            ("PLCC-44_16.58x16.58mm_P1.27mm", "plcc"),
            ("PQFP-100_14x14mm_P0.5mm", "pqfp"),
            ("TQFP-64_10x10mm_P0.5mm", "tqfp"),
            ("LQFP-48_7x7mm_P0.5mm", "lqfp"),
            ("MSOP-10_3x3mm_P0.5mm", "msop"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_extract_diode_packages(self):
        """Should extract diode package types."""
        test_cases = [
            ("D_SOD-123", "sod-123"),
            ("D_SOD-323_HandSoldering", "sod-323"),
            ("D_SOD-523", "sod-523"),
            ("D_SOD-923", "sod-923"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_extract_power_packages(self):
        """Should extract SMD power package types."""
        test_cases = [
            ("TO_SOT_Packages_SMD:DPAK", "dpak"),
            ("TO_SOT_Packages_SMD:D2PAK", "d2pak"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_case_insensitive_matching(self):
        """Should handle case variations in footprint names."""
        test_cases = [
            ("r_0603_1608metric", "0603"),
            ("C_0805_2012METRIC", "0805"),
            ("sot-23", "sot-23"),
            ("SOT-23", "sot-23"),
            ("SoT-23", "sot-23"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_longer_pattern_precedence(self):
        """Should match longer patterns before shorter ones."""
        # "sot-23-5" should be matched instead of just "sot" or "sot-23"
        result = extract_package_from_footprint("SOT-23-5")
        assert result == "sot-23-5"

        # "sot-23" should be matched instead of just "sot"
        result = extract_package_from_footprint("SOT-23")
        assert result == "sot-23"

    def test_empty_and_invalid_inputs(self):
        """Should handle empty and invalid inputs gracefully."""
        test_cases = [
            ("", ""),
            ("Unknown_Package", ""),
            ("DIP-8_W7.62mm", ""),  # Through-hole package not in SMD list
            ("Connector_PinHeader_2.54mm", ""),
            ("TestPoint_Bridge_Pad_D1.0mm", ""),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"

    def test_partial_matches_in_complex_names(self):
        """Should find packages even in complex footprint names."""
        test_cases = [
            ("C_0603_1608Metric_Pad1.08x0.95mm_HandSolder", "0603"),
            ("R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "0805"),
            ("Package_TO_SOT_SMD:SOT-23_HandSoldering", "sot-23"),
            ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "soic"),
        ]
        for footprint, expected in test_cases:
            result = extract_package_from_footprint(footprint)
            assert (
                result == expected
            ), f"For {footprint}, expected {expected}, got {result}"


class TestFootprintMatchesPackage:
    """Test footprint_matches_package function."""

    def test_direct_package_matches(self):
        """Should match when package appears in both footprint and inventory."""
        test_cases = [
            ("R_0603_1608Metric", "0603", True),
            ("C_0805_2012Metric", "0805", True),
            ("SOT-23", "sot-23", True),
            ("SOIC-8_3.9x4.9mm_P1.27mm", "soic", True),
            ("QFN-32-1EP_5x5mm_P0.5mm", "qfn", True),
            ("D_SOD-323_HandSoldering", "sod-323", True),
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"

    def test_case_insensitive_matching(self):
        """Should handle case variations in both inputs."""
        test_cases = [
            ("R_0603_1608Metric", "0603", True),
            ("r_0603_1608metric", "0603", True),
            ("R_0603_1608METRIC", "0603", True),
            ("SOT-23", "sot-23", True),
            ("sot-23", "SOT-23", True),
            ("SoT-23", "SoT-23", True),
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"

    def test_dash_variation_matching(self):
        """Should handle dash variations between footprint and inventory naming."""
        test_cases = [
            ("SOT-23", "sot23", True),  # Footprint has dash, inventory doesn't
            ("SOD-123", "sod123", True),  # Footprint has dash, inventory doesn't
            ("SOT-323", "sot323", True),  # Footprint has dash, inventory doesn't
            ("SC-70", "sc70", True),  # Footprint has dash, inventory doesn't
            # Note: reverse case (inventory has dash, footprint doesn't) would need
            # the extract function to find the dash-less version in the footprint
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"

    def test_non_matching_packages(self):
        """Should return False for non-matching packages."""
        test_cases = [
            ("R_0603_1608Metric", "0805", False),
            ("C_0805_2012Metric", "1206", False),
            ("SOT-23", "soic", False),
            ("SOIC-8_3.9x4.9mm_P1.27mm", "qfp", False),
            ("QFN-32-1EP_5x5mm_P0.5mm", "bga", False),
            ("Unknown_Package", "0603", False),
            ("R_0603_1608Metric", "unknown", False),
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"

    def test_empty_and_none_inputs(self):
        """Should handle empty and None inputs gracefully."""
        test_cases = [
            ("", "", False),
            ("R_0603_1608Metric", "", False),
            ("", "0603", False),
            (None, "0603", False),  # Will be handled by truthiness check
            ("R_0603_1608Metric", None, False),  # Will be handled by truthiness check
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"

    def test_complex_real_world_examples(self):
        """Should handle real-world KiCad footprint names correctly."""
        test_cases = [
            ("Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder", "0603", True),
            ("Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", "0805", True),
            ("Package_TO_SOT_SMD:SOT-23_HandSoldering", "sot23", True),
            ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "soic8", True),
            ("Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm", "qfn32", True),
            ("Diode_SMD:D_SOD-323_HandSoldering", "sod323", True),
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"

    def test_edge_case_substring_matching(self):
        """Should handle edge cases in substring matching."""
        # Make sure we don't get false positives from partial matches
        test_cases = [
            ("R_0603_1608Metric", "603", False),  # Partial number match should fail
            ("SOT-23", "ot-23", False),  # Partial string match should fail
            ("SOIC-8", "ic", False),  # Partial match should fail
        ]
        for footprint, package, expected in test_cases:
            result = footprint_matches_package(footprint, package)
            assert (
                result == expected
            ), f"For ({footprint}, {package}), expected {expected}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__])
