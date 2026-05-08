"""Unit tests for ProjectMetadata service."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from jbom.services.project_metadata import (
    ProjectMetadata,
    create_metadata,
    normalize_archive_stem,
)


class TestNormalizeArchiveStem:
    """Tests for normalize_archive_stem function."""

    def test_normalize_spaces_to_underscores(self) -> None:
        """Spaces should be converted to underscores."""
        assert normalize_archive_stem("My Project") == "My_Project"

    def test_normalize_removes_special_characters(self) -> None:
        """Special characters should be removed."""
        assert normalize_archive_stem("Project@#$%") == "Project"

    def test_normalize_preserves_alphanumerics_hyphens_underscores(self) -> None:
        """Should keep alphanumerics, hyphens, and underscores."""
        assert normalize_archive_stem("My-Project_123") == "My-Project_123"

    def test_normalize_collapses_multiple_underscores(self) -> None:
        """Multiple consecutive underscores should collapse to one."""
        assert normalize_archive_stem("Project___Name") == "Project_Name"

    def test_normalize_preserves_single_hyphens(self) -> None:
        """Single hyphens should be preserved."""
        assert normalize_archive_stem("My-Project") == "My-Project"

    def test_normalize_handles_mixed_spaces_and_specials(self) -> None:
        """Mixed spacing and special chars should normalize cleanly."""
        # Dots are removed; spaces become underscores; @ is removed
        assert normalize_archive_stem("Project! Name@2.0") == "Project_Name20"

    def test_normalize_empty_string_returns_default(self) -> None:
        """Empty input should return 'archive' as default."""
        assert normalize_archive_stem("") == "archive"

    def test_normalize_only_special_chars_returns_default(self) -> None:
        """String with only special chars should return 'archive'."""
        assert normalize_archive_stem("@#$%") == "archive"

    def test_normalize_strips_leading_trailing_underscores(self) -> None:
        """Leading/trailing underscores should be removed."""
        assert normalize_archive_stem("_project_") == "project"

    def test_normalize_real_world_example(self) -> None:
        """Real-world project name should normalize correctly."""
        assert normalize_archive_stem("cpNode-Xiao-68x90") == "cpNode-Xiao-68x90"


class TestCreateMetadata:
    """Tests for create_metadata factory function."""

    def test_create_metadata_requires_project_file(self) -> None:
        """Should raise FileNotFoundError if project file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            nonexistent = tmpdir_path / "nonexistent.kicad_pro"

            with pytest.raises(FileNotFoundError):
                create_metadata(nonexistent)

    def test_create_metadata_with_only_project_file(self) -> None:
        """Should work with only project file (minimal case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_file = tmpdir_path / "test_project.kicad_pro"
            project_file.write_text("(kicad_pro (version 20211014))")

            metadata = create_metadata(project_file)

            assert metadata.project_name == "test_project"
            assert metadata.pcb_metadata is None
            assert metadata.schematic_metadata is None
            assert metadata.release_timestamp is not None

    def test_create_metadata_falls_back_to_project_basename(self) -> None:
        """Should use project file basename when title blocks are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_file = tmpdir_path / "MyProject.kicad_pro"
            project_file.write_text("(kicad_pro (version 20211014))")

            metadata = create_metadata(project_file)

            assert metadata.project_name == "MyProject"

    def test_create_metadata_pcb_file_not_found_is_silent(self) -> None:
        """Should silently skip missing PCB file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_file = tmpdir_path / "test.kicad_pro"
            project_file.write_text("(kicad_pro (version 20211014))")
            nonexistent_pcb = tmpdir_path / "nonexistent.kicad_pcb"

            metadata = create_metadata(project_file, pcb_file=nonexistent_pcb)

            assert metadata.pcb_metadata is None

    def test_create_metadata_schematic_file_not_found_is_silent(self) -> None:
        """Should silently skip missing schematic file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_file = tmpdir_path / "test.kicad_pro"
            project_file.write_text("(kicad_pro (version 20211014))")
            nonexistent_sch = tmpdir_path / "nonexistent.kicad_sch"

            metadata = create_metadata(project_file, schematic_file=nonexistent_sch)

            assert metadata.schematic_metadata is None

    def test_create_metadata_is_immutable(self) -> None:
        """ProjectMetadata should be frozen (immutable)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_file = tmpdir_path / "test.kicad_pro"
            project_file.write_text("(kicad_pro (version 20211014))")

            metadata = create_metadata(project_file)

            with pytest.raises(AttributeError):
                metadata.project_name = "changed"

    def test_create_metadata_timestamp_is_recent(self) -> None:
        """release_timestamp should be very recent."""
        from datetime import datetime, timedelta

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            project_file = tmpdir_path / "test.kicad_pro"
            project_file.write_text("(kicad_pro (version 20211014))")

            before = datetime.now()
            metadata = create_metadata(project_file)
            after = datetime.now()

            # Timestamp should be between before and after (within 1 second)
            assert before <= metadata.release_timestamp <= after + timedelta(seconds=1)


class TestProjectMetadataDataclass:
    """Tests for ProjectMetadata dataclass itself."""

    def test_project_metadata_is_frozen(self) -> None:
        """ProjectMetadata should be frozen."""
        from jbom.common.types import TitleBlockMetadata
        from datetime import datetime

        metadata = ProjectMetadata(
            project_name="test",
            pcb_metadata=TitleBlockMetadata(title="PCB Title", revision="1.0"),
            schematic_metadata=None,
            release_timestamp=datetime.now(),
        )

        with pytest.raises(AttributeError):
            metadata.project_name = "changed"

    def test_project_metadata_provenance_tracking(self) -> None:
        """ProjectMetadata should preserve separate provenance for PCB and schematic."""
        from jbom.common.types import TitleBlockMetadata
        from datetime import datetime

        pcb_md = TitleBlockMetadata(title="PCB Title", revision="2.0")
        sch_md = TitleBlockMetadata(title="Schematic Title", revision="3.0")

        metadata = ProjectMetadata(
            project_name="test",
            pcb_metadata=pcb_md,
            schematic_metadata=sch_md,
            release_timestamp=datetime.now(),
        )

        # Both should be available for downstream decision-making
        assert metadata.pcb_metadata.revision == "2.0"
        assert metadata.schematic_metadata.revision == "3.0"
