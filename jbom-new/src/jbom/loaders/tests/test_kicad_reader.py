"""Unit tests for KiCadReaderService."""

import tempfile
import pytest
from pathlib import Path

from jbom.loaders.kicad_reader import (
    DefaultKiCadReaderService,
    KiCadParseError,
    create_kicad_reader_service,
)
from jbom.loaders.pcb_model import BoardModel


class TestKiCadReaderService:
    """Test cases for KiCadReaderService interface and implementation."""

    def test_factory_creates_default_service(self):
        """Test that factory function creates DefaultKiCadReaderService."""
        service = create_kicad_reader_service()
        assert isinstance(service, DefaultKiCadReaderService)
        assert service.mode == "auto"

    def test_factory_accepts_mode_parameter(self):
        """Test that factory function accepts mode parameter."""
        service = create_kicad_reader_service(mode="sexp")
        assert service.mode == "sexp"


class TestDefaultKiCadReaderService:
    """Test cases for DefaultKiCadReaderService implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = DefaultKiCadReaderService()

    def test_validate_pcb_file_nonexistent(self):
        """Test validation fails for nonexistent file."""
        nonexistent_path = Path("/nonexistent/file.kicad_pcb")
        assert not self.service.validate_pcb_file(nonexistent_path)

    def test_validate_pcb_file_wrong_extension(self):
        """Test validation fails for wrong file extension."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
            tmp_path = Path(tmp.name)
            assert not self.service.validate_pcb_file(tmp_path)

    def test_validate_pcb_file_invalid_content(self):
        """Test validation fails for invalid PCB content."""
        with tempfile.NamedTemporaryFile(
            suffix=".kicad_pcb", mode="w", delete=False
        ) as tmp:
            tmp.write("invalid pcb content")
            tmp_path = Path(tmp.name)

        try:
            assert not self.service.validate_pcb_file(tmp_path)
        finally:
            tmp_path.unlink()

    def test_validate_pcb_file_valid_content(self):
        """Test validation succeeds for valid PCB content."""
        with tempfile.NamedTemporaryFile(
            suffix=".kicad_pcb", mode="w", delete=False
        ) as tmp:
            tmp.write("(kicad_pcb (version 20221018)")
            tmp_path = Path(tmp.name)

        try:
            assert self.service.validate_pcb_file(tmp_path)
        finally:
            tmp_path.unlink()

    def test_read_pcb_file_invalid_file(self):
        """Test that reading invalid file raises KiCadParseError."""
        nonexistent_path = Path("/nonexistent/file.kicad_pcb")

        with pytest.raises(KiCadParseError) as exc_info:
            self.service.read_pcb_file(nonexistent_path)

        assert "Invalid or missing PCB file" in str(exc_info.value)
        assert exc_info.value.pcb_path == nonexistent_path

    def test_read_pcb_file_simple_board(self):
        """Test reading a simple PCB with one component."""
        pcb_content = """(kicad_pcb (version 20221018) (generator pcbnew)
  (general
    (title "Test Board")
  )
  (footprint "Resistor_SMD:R_0603_1608Metric" (layer "F.Cu")
    (at 25.4 25.4 0)
    (fp_text reference "R1" (at 0 0) (layer "F.SilkS"))
    (fp_text value "1K" (at 0 0) (layer "F.Fab"))
    (property "Reference" "R1")
    (property "Value" "1K")
    (property "Footprint" "Resistor_SMD:R_0603_1608Metric")
    (property "Datasheet" "~")
    (attr smd)
  )
)"""

        with tempfile.NamedTemporaryFile(
            suffix=".kicad_pcb", mode="w", delete=False
        ) as tmp:
            tmp.write(pcb_content)
            tmp_path = Path(tmp.name)

        try:
            board = self.service.read_pcb_file(tmp_path)

            assert isinstance(board, BoardModel)
            assert board.path == tmp_path
            assert board.title == "Test Board"
            assert len(board.footprints) == 1

            component = board.footprints[0]
            assert component.reference == "R1"
            assert component.footprint_name == "Resistor_SMD:R_0603_1608Metric"
            assert component.center_x_mm == 25.4
            assert component.center_y_mm == 25.4
            assert component.rotation_deg == 0.0
            assert component.side == "TOP"
            assert component.package_token == "0603"
            assert component.attributes["Value"] == "1K"
            assert component.attributes["Datasheet"] == "~"
            assert component.attributes["mount_type"] == "smd"

        finally:
            tmp_path.unlink()

    def test_read_pcb_file_multiple_components(self):
        """Test reading PCB with multiple components on different layers."""
        pcb_content = """(kicad_pcb (version 20221018) (generator pcbnew)
  (general
    (title "Multi-Component Board")
  )
  (footprint "Resistor_SMD:R_0603_1608Metric" (layer "F.Cu")
    (at 25.4 25.4 90)
    (fp_text reference "R1" (at 0 0))
    (fp_text value "1K" (at 0 0))
    (property "Reference" "R1")
    (property "Value" "1K")
    (attr smd)
  )
  (footprint "Capacitor_SMD:C_0603_1608Metric" (layer "B.Cu")
    (at 50.8 25.4 180)
    (fp_text reference "C1" (at 0 0))
    (fp_text value "0.1uF" (at 0 0))
    (property "Reference" "C1")
    (property "Value" "0.1uF")
    (attr smd)
  )
  (footprint "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm" (layer "F.Cu")
    (at 76.2 25.4 0)
    (fp_text reference "U1" (at 0 0))
    (fp_text value "NE555" (at 0 0))
    (property "Reference" "U1")
    (property "Value" "NE555")
    (property "Manufacturer" "Texas Instruments")
    (attr smd)
  )
)"""

        with tempfile.NamedTemporaryFile(
            suffix=".kicad_pcb", mode="w", delete=False
        ) as tmp:
            tmp.write(pcb_content)
            tmp_path = Path(tmp.name)

        try:
            board = self.service.read_pcb_file(tmp_path)

            assert len(board.footprints) == 3

            # Check R1 (top side, rotated)
            r1 = next(c for c in board.footprints if c.reference == "R1")
            assert r1.side == "TOP"
            assert r1.rotation_deg == 90.0
            assert r1.package_token == "0603"
            assert r1.attributes["Value"] == "1K"

            # Check C1 (bottom side, rotated)
            c1 = next(c for c in board.footprints if c.reference == "C1")
            assert c1.side == "BOTTOM"
            assert c1.rotation_deg == 180.0
            assert c1.center_x_mm == 50.8
            assert c1.attributes["Value"] == "0.1uF"

            # Check U1 (top side, has manufacturer attribute)
            u1 = next(c for c in board.footprints if c.reference == "U1")
            assert u1.side == "TOP"
            assert u1.package_token == "SOIC"
            assert u1.attributes["Value"] == "NE555"
            assert u1.attributes["Manufacturer"] == "Texas Instruments"

        finally:
            tmp_path.unlink()

    def test_extract_package_token_various_footprints(self):
        """Test package token extraction for various footprint names."""
        test_cases = [
            ("Resistor_SMD:R_0603_1608Metric", "0603"),
            ("Capacitor_SMD:C_0805_2012Metric", "0805"),
            ("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "SOIC"),
            ("Package_QFP:TQFP-32_7x7mm_P0.8mm", "QFP"),
            ("BGA:FBGA-78_7.5x11mm_Layout2x3x13_P0.8mm", "BGA"),
            ("Unknown:CustomFootprint", "CustomFootprint"),
            ("", ""),
        ]

        for footprint_name, expected_package in test_cases:
            actual_package = self.service._extract_package_token(footprint_name)
            assert (
                actual_package == expected_package
            ), f"Failed for {footprint_name}: expected {expected_package}, got {actual_package}"

    def test_extract_board_metadata_missing_title(self):
        """Test board metadata extraction when title is missing."""
        pcb_content = """(kicad_pcb (version 20221018)
  (general)
)"""

        with tempfile.NamedTemporaryFile(
            suffix=".kicad_pcb", mode="w", delete=False
        ) as tmp:
            tmp.write(pcb_content)
            tmp_path = Path(tmp.name)

        try:
            board = self.service.read_pcb_file(tmp_path)
            assert board.title == ""
            assert board.kicad_version is None
        finally:
            tmp_path.unlink()


class TestKiCadParseError:
    """Test cases for KiCadParseError exception."""

    def test_error_with_path(self):
        """Test error creation with path."""
        test_path = Path("/test/file.kicad_pcb")
        error = KiCadParseError("Test error", test_path)

        assert str(error) == "Test error"
        assert error.pcb_path == test_path

    def test_error_without_path(self):
        """Test error creation without path."""
        error = KiCadParseError("Test error")

        assert str(error) == "Test error"
        assert error.pcb_path is None
