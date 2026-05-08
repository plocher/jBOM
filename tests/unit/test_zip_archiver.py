"""Unit tests for ZipArchiver service."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from jbom.services.zip_archiver import ZipArchiver


class TestZipArchiver:
    """Tests for ZipArchiver service."""

    def test_archive_single_file(self) -> None:
        """ZipArchiver should create archive with single file stored at its basename only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a test file
            test_file = tmpdir_path / "test.txt"
            test_file.write_text("Hello, World!")

            # Archive it
            archive_path = tmpdir_path / "output.zip"
            archiver = ZipArchiver()
            archiver.archive([test_file], archive_path)

            # Verify archive exists and contains the file at its basename — no absolute path
            assert archive_path.exists()
            with zipfile.ZipFile(archive_path, "r") as z:
                names = z.namelist()
                assert names == ["test.txt"], f"Expected ['test.txt'], got {names}"
                assert not any(
                    name.startswith("/") for name in names
                ), f"Archive contains absolute paths: {names}"

    def test_archive_multiple_files(self) -> None:
        """ZipArchiver should archive multiple files with basenames only (no absolute paths)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            file1 = tmpdir_path / "file1.txt"
            file1.write_text("Content 1")
            file2 = tmpdir_path / "file2.txt"
            file2.write_text("Content 2")

            # Archive both
            archive_path = tmpdir_path / "output.zip"
            archiver = ZipArchiver()
            archiver.archive([file1, file2], archive_path)

            # Verify both stored as basenames with no absolute path components
            with zipfile.ZipFile(archive_path, "r") as z:
                names = sorted(z.namelist())
                assert names == ["file1.txt", "file2.txt"], f"Unexpected names: {names}"
                assert not any(name.startswith("/") for name in names)

    def test_archive_directory_structure(self) -> None:
        """ZipArchiver should store directory contents relative to the source dir root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create directory structure
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            file_in_subdir = subdir / "nested.txt"
            file_in_subdir.write_text("Nested content")

            # Archive the directory
            archive_path = tmpdir_path / "output.zip"
            archiver = ZipArchiver()
            archiver.archive([subdir], archive_path)

            # Files inside a directory are stored relative to that directory's root —
            # no parent path components from outside the source dir
            with zipfile.ZipFile(archive_path, "r") as z:
                names = z.namelist()
                assert names == ["nested.txt"], f"Expected ['nested.txt'], got {names}"
                assert not any(name.startswith("/") for name in names)
                assert not any(
                    "subdir" in name for name in names
                ), f"Directory name leaked into archive paths: {names}"

    def test_archive_creates_parent_directories(self) -> None:
        """ZipArchiver should create parent directories of archive path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a test file
            test_file = tmpdir_path / "test.txt"
            test_file.write_text("Test")

            # Archive to nested path that doesn't exist yet
            archive_path = tmpdir_path / "deep" / "nested" / "path" / "output.zip"
            archiver = ZipArchiver()
            archiver.archive([test_file], archive_path)

            # Verify archive was created (parent dirs were created)
            assert archive_path.exists()
            with zipfile.ZipFile(archive_path, "r") as z:
                assert len(z.namelist()) == 1

    def test_archive_raises_on_empty_paths(self) -> None:
        """ZipArchiver should raise ValueError on empty source_paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            archive_path = tmpdir_path / "output.zip"

            archiver = ZipArchiver()
            with pytest.raises(ValueError, match="source_paths cannot be empty"):
                archiver.archive([], archive_path)

    def test_archive_raises_on_missing_source(self) -> None:
        """ZipArchiver should raise FileNotFoundError if source doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            nonexistent = tmpdir_path / "does_not_exist.txt"
            archive_path = tmpdir_path / "output.zip"

            archiver = ZipArchiver()
            with pytest.raises(FileNotFoundError):
                archiver.archive([nonexistent], archive_path)

    def test_archive_raises_on_empty_directory(self) -> None:
        """ZipArchiver should raise ValueError if directory is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create an empty directory
            empty_dir = tmpdir_path / "empty"
            empty_dir.mkdir()

            archive_path = tmpdir_path / "output.zip"
            archiver = ZipArchiver()

            with pytest.raises(ValueError, match="No files found"):
                archiver.archive([empty_dir], archive_path)

    def test_archive_mixed_files_and_directories(self) -> None:
        """ZipArchiver stores files at basename and directory contents relative to dir root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a file
            file1 = tmpdir_path / "root.txt"
            file1.write_text("Root file")

            # Create a directory with a file
            subdir = tmpdir_path / "subdir"
            subdir.mkdir()
            file2 = subdir / "nested.txt"
            file2.write_text("Nested file")

            # Archive both
            archive_path = tmpdir_path / "output.zip"
            archiver = ZipArchiver()
            archiver.archive([file1, subdir], archive_path)

            # root.txt stored as "root.txt"; nested.txt stored as "nested.txt" (relative to subdir)
            with zipfile.ZipFile(archive_path, "r") as z:
                names = sorted(z.namelist())
                assert names == ["nested.txt", "root.txt"], f"Unexpected names: {names}"
                assert not any(name.startswith("/") for name in names)

    def test_archive_content_integrity(self) -> None:
        """ZipArchiver should preserve file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a file with specific content
            test_file = tmpdir_path / "content.txt"
            content = "This is test content with special chars: äöü\n"
            test_file.write_text(content, encoding="utf-8")

            # Archive it
            archive_path = tmpdir_path / "output.zip"
            archiver = ZipArchiver()
            archiver.archive([test_file], archive_path)

            # Verify content is preserved
            with zipfile.ZipFile(archive_path, "r") as z:
                for name in z.namelist():
                    if "content.txt" in name:
                        extracted_content = z.read(name).decode("utf-8")
                        assert extracted_content == content
