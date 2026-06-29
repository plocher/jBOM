"""Unit tests for SchematicReader service."""

import pytest
from pathlib import Path
from unittest.mock import patch

from sexpdata import Symbol

from jbom.services.schematic_reader import SchematicReader
from jbom.common.types import Component, TitleBlockMetadata


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

    def test_should_include_component_is_permissive(self):
        """SchematicReader should not enforce BOM/parts filtering policy."""

        reader = SchematicReader()

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

        # Filtering policies (DNP, in_bom, virtual symbols) are applied later by
        # jbom.common.component_filters based on CLI flags.
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
        assert reader._should_include_component(not_in_bom) is True

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
        assert reader._should_include_component(dnp_component) is True

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
        assert reader._should_include_component(hash_component) is True


# ---------------------------------------------------------------------------
# Title-block metadata: COMMENT 1..9 parsing (#332)
# ---------------------------------------------------------------------------


def _sch_sexp_with_title_block(title_block_items: list[object]) -> list[object]:
    """Build a minimal ``(kicad_sch ... (title_block ...))`` tree for tests."""
    return [
        Symbol("kicad_sch"),
        [Symbol("version"), "20240108"],
        [Symbol("title_block"), *title_block_items],
    ]


def _comment(index: int, text: str) -> list[object]:
    return [Symbol("comment"), index, text]


class TestSchematicTitleBlockComments:
    """SchematicReader._extract_title_block_metadata parses comment N=1..9."""

    def test_scalar_fields_still_extracted(self) -> None:
        reader = SchematicReader()
        sexp = _sch_sexp_with_title_block(
            [
                [Symbol("title"), "MySch"],
                [Symbol("rev"), "A"],
                [Symbol("date"), "2026-05-09"],
                [Symbol("company"), "Acme"],
            ]
        )
        metadata = reader._extract_title_block_metadata(sexp)
        assert isinstance(metadata, TitleBlockMetadata)
        assert metadata.title == "MySch"
        assert metadata.revision == "A"
        assert metadata.date == "2026-05-09"
        assert metadata.company == "Acme"
        assert dict(metadata.comments) == {}

    def test_populates_all_nine_comments(self) -> None:
        reader = SchematicReader()
        sexp = _sch_sexp_with_title_block(
            [_comment(n, f"sch-comment-{n}") for n in range(1, 10)]
        )
        metadata = reader._extract_title_block_metadata(sexp)
        for n in range(1, 10):
            assert metadata.comments[n] == f"sch-comment-{n}"

    def test_missing_comments_absent_from_map(self) -> None:
        reader = SchematicReader()
        sexp = _sch_sexp_with_title_block([[Symbol("title"), "MySch"]])
        metadata = reader._extract_title_block_metadata(sexp)
        assert dict(metadata.comments) == {}

    def test_empty_comment_value_preserved(self) -> None:
        reader = SchematicReader()
        sexp = _sch_sexp_with_title_block([_comment(2, "")])
        metadata = reader._extract_title_block_metadata(sexp)
        assert 2 in metadata.comments
        assert metadata.comments[2] == ""

    def test_mixed_presence_preserved(self) -> None:
        reader = SchematicReader()
        sexp = _sch_sexp_with_title_block(
            [
                _comment(1, "designer"),
                _comment(9, "released"),
            ]
        )
        metadata = reader._extract_title_block_metadata(sexp)
        assert metadata.comments == {1: "designer", 9: "released"}


class TestReaderIndependence:
    """The schematic and PCB readers do not merge or reconcile values.

    Divergent SCH/PCB title-block content must be reported as-is by each
    reader; reconciliation policy is a consumer concern (KiCad itself
    permits independent edits once the schematic→PCB sync has happened).
    """

    def test_sch_and_pcb_readers_report_independent_comments(self) -> None:
        from jbom.services.pcb_reader import DefaultKiCadReaderService

        sch_reader = SchematicReader()
        pcb_reader = DefaultKiCadReaderService()

        sch_sexp = _sch_sexp_with_title_block(
            [
                [Symbol("title"), "sch-title"],
                [Symbol("rev"), "A"],
                _comment(1, "sch-designer"),
                _comment(9, "sch-status"),
            ]
        )
        pcb_sexp = [
            Symbol("kicad_pcb"),
            [Symbol("version"), "20240108"],
            [
                Symbol("title_block"),
                [Symbol("title"), "pcb-title"],
                [Symbol("rev"), "A1"],
                _comment(1, "pcb-designer"),
                _comment(9, "pcb-status"),
            ],
        ]

        sch_meta = sch_reader._extract_title_block_metadata(sch_sexp)
        pcb_meta = pcb_reader._extract_title_block_metadata(pcb_sexp)

        # Each reader reports its own file's values; divergent scalars and
        # comments are *not* merged across files.
        assert sch_meta.title == "sch-title"
        assert pcb_meta.title == "pcb-title"
        assert sch_meta.revision == "A"
        assert pcb_meta.revision == "A1"
        assert sch_meta.comments[1] == "sch-designer"
        assert pcb_meta.comments[1] == "pcb-designer"
        assert sch_meta.comments[9] == "sch-status"
        assert pcb_meta.comments[9] == "pcb-status"
