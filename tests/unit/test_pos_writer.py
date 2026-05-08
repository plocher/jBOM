"""Unit tests for POSWriter service."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from jbom.application.pos_workflow import POSGenerationPayload
from jbom.services.pos_writer import POSWriter


class TestPOSWriterBasics:
    """Basic POSWriter functionality tests."""

    def test_write_creates_file(self) -> None:
        """POSWriter.write should create output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(
                    {
                        "reference": "R1",
                        "x_mm": 10.0,
                        "y_mm": 20.0,
                        "rotation": 0.0,
                        "side": "top",
                    },
                ),
                selected_fields=("reference", "x", "y", "rotation", "side"),
                headers=("Reference", "X", "Y", "Rotation", "Side"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)
            assert output_path.exists()

    def test_write_with_headers(self) -> None:
        """POSWriter.write should output correct headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference", "x", "y"),
                headers=("Reference", "X", "Y"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                headers = next(reader)
                assert headers == ["Reference", "X", "Y"]

    def test_write_with_single_entry(self) -> None:
        """POSWriter.write should output row content correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(
                    {
                        "reference": "R1",
                        "x_mm": 10.0,
                        "y_mm": 20.0,
                        "rotation": 0.0,
                        "side": "top",
                    },
                ),
                selected_fields=("reference", "x", "y", "rotation", "side"),
                headers=("Reference", "X", "Y", "Rotation", "Side"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                assert len(rows) == 1
                assert rows[0][0] == "R1"

    def test_write_with_multiple_entries(self) -> None:
        """POSWriter.write should handle multiple entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(
                    {
                        "reference": "R1",
                        "x_mm": 10.0,
                        "y_mm": 20.0,
                        "rotation": 0.0,
                        "side": "top",
                    },
                    {
                        "reference": "C1",
                        "x_mm": 15.0,
                        "y_mm": 25.0,
                        "rotation": 90.0,
                        "side": "top",
                    },
                ),
                selected_fields=("reference", "x", "y", "rotation", "side"),
                headers=("Reference", "X", "Y", "Rotation", "Side"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                assert len(rows) == 2

    def test_write_with_empty_entries(self) -> None:
        """POSWriter.write should handle empty POS (header-only output)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference", "x", "y"),
                headers=("Reference", "X", "Y"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
                assert len(rows) == 1  # Header only
                assert rows[0] == ["Reference", "X", "Y"]

    def test_write_uses_quote_all(self) -> None:
        """POSWriter.write should use csv.QUOTE_ALL for quoting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(
                    {
                        "reference": "R1",
                        "x_mm": 0.0603,  # Leading zeros should be preserved
                        "y_mm": 20.0,
                        "rotation": 0.0,
                        "side": "top",
                    },
                ),
                selected_fields=("reference", "x"),
                headers=("Reference", "X"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)

            # Read raw file content to check quoting
            with open(output_path, "r") as f:
                content = f.read()
                # QUOTE_ALL should quote all fields
                assert '"' in content


class TestPOSWriterOverwritePolicy:
    """POSWriter overwrite guard tests."""

    def test_raises_on_existing_file_without_force(self) -> None:
        """POSWriter.write should raise FileExistsError when force=False and file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            output_path.write_text("existing content")

            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference",),
                headers=("Reference",),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            with pytest.raises(FileExistsError):
                POSWriter.write(payload, output_path, force=False)

    def test_overwrites_existing_file_with_force(self) -> None:
        """POSWriter.write should overwrite existing file when force=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            output_path.write_text("old content")

            payload = POSGenerationPayload(
                pos_data=(
                    {
                        "reference": "R1",
                        "x_mm": 10.0,
                        "y_mm": 20.0,
                        "rotation": 0.0,
                        "side": "top",
                    },
                ),
                selected_fields=("reference", "x"),
                headers=("Reference", "X"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path, force=True)

            # Verify old content is overwritten
            content = output_path.read_text()
            assert "old content" not in content
            assert "Reference" in content
            assert "R1" in content

    def test_force_false_by_default(self) -> None:
        """POSWriter.write should default force=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            output_path.write_text("existing")

            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference",),
                headers=("Reference",),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            # Should raise without explicit force=True
            with pytest.raises(FileExistsError):
                POSWriter.write(payload, output_path)


class TestPOSWriterIntegration:
    """Integration tests with actual field resolution."""

    def test_write_resolves_field_values(self) -> None:
        """POSWriter.write should resolve field values using field resolver."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(
                    {
                        "reference": "R1",
                        "x_mm": 10.0,
                        "y_mm": 20.0,
                        "rotation": 0.0,
                        "side": "top",
                        "package": "0603",
                    },
                ),
                selected_fields=("reference", "package"),
                headers=("Reference", "Package"),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            POSWriter.write(payload, output_path)

            with open(output_path, "r") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                row = next(reader)
                assert row[0] == "R1"
                assert row[1] == "0603"

    def test_write_with_path_object(self) -> None:
        """POSWriter.write should accept both Path and str paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "placement.csv"
            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference",),
                headers=("Reference",),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            # Pass Path object
            POSWriter.write(payload, output_path)
            assert output_path.exists()

    def test_write_with_string_path(self) -> None:
        """POSWriter.write should accept string paths and convert to Path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path_str = str(Path(tmpdir) / "placement.csv")
            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference",),
                headers=("Reference",),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            # Pass string path
            POSWriter.write(payload, output_path_str)  # type: ignore[arg-type]
            assert Path(output_path_str).exists()

    def test_write_creates_parent_directory_when_needed(self) -> None:
        """POSWriter.write should handle nested paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "placement.csv"
            # Parent directory does not exist yet

            payload = POSGenerationPayload(
                pos_data=(),
                selected_fields=("reference",),
                headers=("Reference",),
                fabricator="generic",
                fabricator_config=None,
                default_output_path=Path("cpl.csv"),
            )

            # This should fail because POSWriter does not create parents
            with pytest.raises(FileNotFoundError):
                POSWriter.write(payload, output_path)
