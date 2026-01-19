"""Unit tests for SchematicReader service."""

import pytest
from pathlib import Path
from unittest.mock import patch

from jbom.services.readers.schematic_reader import SchematicReader
from jbom.common.types import Component


class TestSchematicReader:
    """Test the SchematicReader service in isolation."""

    def test_init_with_default_options(self):
        """Test initialization with default options."""
        reader = SchematicReader()
        assert reader.options is not None
        assert hasattr(reader.options, "verbose")

    def test_init_with_custom_options(self):
        """Test initialization with custom options."""
        from jbom.common.options import GeneratorOptions

        options = GeneratorOptions(verbose=True)
        reader = SchematicReader(options)
        assert reader.options.verbose is True

    def test_load_components_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        reader = SchematicReader()
        non_existent_file = Path("/tmp/nonexistent.kicad_sch")

        with pytest.raises(FileNotFoundError, match="Schematic file not found"):
            reader.load_components(non_existent_file)

    def test_load_components_wrong_extension(self):
        """Test that ValueError is raised for wrong file extension."""
        reader = SchematicReader()

        # Mock file existence but wrong extension
        with patch("pathlib.Path.exists", return_value=True):
            wrong_file = Path("/tmp/test.txt")
            with pytest.raises(ValueError, match="Expected .kicad_sch file"):
                reader.load_components(wrong_file)

    @patch("jbom.services.readers.schematic_reader.load_kicad_file")
    @patch("jbom.services.readers.schematic_reader.walk_nodes")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.suffix", new_callable=lambda: ".kicad_sch")
    def test_load_components_success(
        self, mock_suffix, mock_exists, mock_walk, mock_load
    ):
        """Test successful component loading."""
        # Mock the S-expression parsing
        mock_load.return_value = []
        mock_walk.return_value = [
            # Mock symbol node
            [
                "symbol",
                ["lib_id", "Device:R"],
                ["property", "Reference", "R1"],
                ["property", "Value", "10K"],
                ["instances", "test"],
                ["in_bom", "yes"],
            ]
        ]

        reader = SchematicReader()
        schematic_file = Path("/tmp/test.kicad_sch")

        with patch.object(reader, "_parse_symbol") as mock_parse:
            mock_component = Component(
                reference="R1",
                lib_id="Device:R",
                value="10K",
                footprint="",
                uuid="",
                properties={},
                in_bom=True,
                exclude_from_sim=False,
                dnp=False,
            )
            mock_parse.return_value = mock_component

            components = reader.load_components(schematic_file)

            assert len(components) == 1
            assert components[0].reference == "R1"
            assert components[0].value == "10K"

    def test_should_include_component_filters(self):
        """Test component filtering logic."""
        reader = SchematicReader()

        # Component included
        good_component = Component(
            reference="R1",
            lib_id="Device:R",
            value="10K",
            footprint="",
            uuid="",
            properties={},
            in_bom=True,
            exclude_from_sim=False,
            dnp=False,
        )
        assert reader._should_include_component(good_component) is True

        # Component excluded - not in BOM
        not_in_bom = Component(
            reference="R1",
            lib_id="Device:R",
            value="10K",
            footprint="",
            uuid="",
            properties={},
            in_bom=False,
            exclude_from_sim=False,
            dnp=False,
        )
        assert reader._should_include_component(not_in_bom) is False

        # Component excluded - DNP
        dnp_component = Component(
            reference="R1",
            lib_id="Device:R",
            value="10K",
            footprint="",
            uuid="",
            properties={},
            in_bom=True,
            exclude_from_sim=False,
            dnp=True,
        )
        assert reader._should_include_component(dnp_component) is False

        # Component excluded - reference starts with #
        hash_component = Component(
            reference="#PWR01",
            lib_id="power:GND",
            value="",
            footprint="",
            uuid="",
            properties={},
            in_bom=True,
            exclude_from_sim=False,
            dnp=False,
        )
        assert reader._should_include_component(hash_component) is False
