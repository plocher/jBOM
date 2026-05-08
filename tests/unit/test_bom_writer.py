"""Unit tests for BOMWriter service."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from jbom.application.bom_workflow import BOMGenerationPayload
from jbom.services.bom_generator import BOMData, BOMEntry
from jbom.services.bom_writer import BOMWriter


class TestBOMWriterBasics:
    """Basic BOMWriter functionality tests."""

    def test_write_creates_file(self) -> None:
        """BOMWriter.write should create output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[
                        BOMEntry(
                            references=["R1"],
                            value="10k",
                            footprint="R_0603",
                            quantity=1,
                            attributes={},
                        )
                    ],
                    metadata={},
                ),
                selected_fields=("reference", "quantity", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)
            assert output_path.exists()

    def test_write_with_headers(self) -> None:
        """BOMWriter.write should output correct headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference", "quantity", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                headers = next(reader)
                # Headers from FabricatorProjectionService are title-cased
                assert headers == ["Reference", "Quantity", "Value"]

    def test_write_with_single_entry(self) -> None:
        """BOMWriter.write should output row content correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[
                        BOMEntry(
                            references=["R1"],
                            value="10k",
                            footprint="R_0603",
                            quantity=1,
                            attributes={},
                        )
                    ],
                    metadata={},
                ),
                selected_fields=("reference", "quantity", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0][0] == "R1"
                assert rows[0][1] == "1"
                assert rows[0][2] == "10k"

    def test_write_with_multiple_entries(self) -> None:
        """BOMWriter.write should handle multiple entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[
                        BOMEntry(
                            references=["R1", "R2"],
                            value="10k",
                            footprint="R_0603",
                            quantity=2,
                            attributes={},
                        ),
                        BOMEntry(
                            references=["C1"],
                            value="100nF",
                            footprint="C_0603",
                            quantity=1,
                            attributes={},
                        ),
                    ],
                    metadata={},
                ),
                selected_fields=("reference", "quantity", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                assert len(rows) == 2

    def test_write_with_empty_entries(self) -> None:
        """BOMWriter.write should handle empty BOM (header-only output)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference", "quantity", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows) == 1  # Header only
                # Headers from FabricatorProjectionService are title-cased
                assert rows[0] == ["Reference", "Quantity", "Value"]

    def test_write_uses_quote_all(self) -> None:
        """BOMWriter.write should use csv.QUOTE_ALL for quoting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[
                        BOMEntry(
                            references=["R1"],
                            value="0603",  # Leading zeros should be preserved
                            footprint="R_0603",
                            quantity=1,
                            attributes={},
                        )
                    ],
                    metadata={},
                ),
                selected_fields=("reference", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)

            # Read raw file content to check quoting
            with open(output_path, "r") as f:
                content = f.read()
                # QUOTE_ALL should quote all fields
                assert '"0603"' in content


class TestBOMWriterOverwritePolicy:
    """BOMWriter overwrite guard tests."""

    def test_raises_on_existing_file_without_force(self) -> None:
        """BOMWriter.write should raise FileExistsError when force=False and file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            output_path.write_text("existing content")

            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference",),
                default_output_path=Path("test.bom.csv"),
            )

            with pytest.raises(FileExistsError):
                BOMWriter.write(payload, output_path, force=False)

    def test_overwrites_existing_file_with_force(self) -> None:
        """BOMWriter.write should overwrite existing file when force=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            output_path.write_text("old content")

            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[
                        BOMEntry(
                            references=["R1"],
                            value="10k",
                            footprint="R_0603",
                            quantity=1,
                            attributes={},
                        )
                    ],
                    metadata={},
                ),
                selected_fields=("reference", "value"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path, force=True)

            # Verify old content is overwritten
            content = output_path.read_text()
            assert "old content" not in content
            # Headers from FabricatorProjectionService are title-cased
            assert "Reference" in content
            assert "R1" in content

    def test_force_false_by_default(self) -> None:
        """BOMWriter.write should default force=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            output_path.write_text("existing")

            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference",),
                default_output_path=Path("test.bom.csv"),
            )

            # Should raise without explicit force=True
            with pytest.raises(FileExistsError):
                BOMWriter.write(payload, output_path)


class TestBOMWriterIntegration:
    """Integration tests with actual field resolution."""

    def test_write_resolves_field_values(self) -> None:
        """BOMWriter.write should resolve field values using field resolver."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[
                        BOMEntry(
                            references=["R1"],
                            value="10k",
                            footprint="R_0603",
                            quantity=1,
                            attributes={
                                "package": "0603",
                                "s:footprint": "R_0603",
                                "p:footprint": "R_0603_Custom",
                            },
                        )
                    ],
                    metadata={},
                ),
                selected_fields=("reference", "quantity", "package"),
                default_output_path=Path("test.bom.csv"),
            )

            BOMWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                row = next(reader)
                assert row[0] == "R1"
                assert row[1] == "1"
                assert row[2] == "0603"

    def test_write_with_path_object(self) -> None:
        """BOMWriter.write should accept both Path and str paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference",),
                default_output_path=Path("test.bom.csv"),
            )

            # Pass Path object
            BOMWriter.write(payload, output_path)
            assert output_path.exists()

    def test_write_with_string_path(self) -> None:
        """BOMWriter.write should accept string paths and convert to Path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path_str = str(Path(tmpdir) / "test.csv")
            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference",),
                default_output_path=Path("test.bom.csv"),
            )

            # Pass string path
            BOMWriter.write(payload, output_path_str)  # type: ignore[arg-type]
            assert Path(output_path_str).exists()

    def test_write_creates_parent_directory_when_needed(self) -> None:
        """BOMWriter.write should handle nested paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "test.csv"
            # Parent directory does not exist yet

            payload = BOMGenerationPayload(
                bom_data=BOMData(
                    project_name="test",
                    entries=[],
                    metadata={},
                ),
                selected_fields=("reference",),
                default_output_path=Path("test.bom.csv"),
            )

            # This should fail because BOMWriter does not create parents
            with pytest.raises(FileNotFoundError):
                BOMWriter.write(payload, output_path)
