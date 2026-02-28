"""ProjectDiscovery service for finding KiCad v6+ project files.

jBOM v7 targets KiCad 6+ projects, which always include exactly one
`*.kicad_pro` project file in the project directory.

This service discovers the project file (`*.kicad_pro`), schematic file
(`*.kicad_sch`), and PCB file (`*.kicad_pcb`) in directories.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from jbom.common.options import GeneratorOptions

__all__ = ["ProjectDiscovery", "ProjectFiles"]


@dataclass
class ProjectFiles:
    """Data structure holding discovered project files."""

    project_file: Path
    schematic_file: Path | None = None
    pcb_file: Path | None = None


class ProjectDiscovery:
    """Service for discovering KiCad v6+ project files in directories."""

    def __init__(self, options: GeneratorOptions | None = None):
        self.options = options or GeneratorOptions()

    def find_project_file(self, search_dir: Path) -> Path:
        """Find the single KiCad v6+ project file in a directory.

        KiCad projects must contain exactly one `*.kicad_pro` file.

        Raises:
            ValueError: If zero or multiple `*.kicad_pro` files are found.
        """
        if not search_dir.is_dir():
            raise ValueError(f"Project directory does not exist: {search_dir}")

        kicad_pro_files = sorted(search_dir.glob("*.kicad_pro"))
        if not kicad_pro_files:
            # Preserve the "No project files found" substring for existing error mapping/tests.
            raise ValueError(
                f"No project files found (expected exactly one *.kicad_pro in {search_dir})"
            )

        if len(kicad_pro_files) > 1:
            raise ValueError(
                f"Multiple project files found in {search_dir} "
                f"({len(kicad_pro_files)} *.kicad_pro files)"
            )

        return kicad_pro_files[0]

    def find_schematic_file(self, search_dir: Path) -> Path | None:
        """Find the best schematic file in a directory."""
        if not search_dir.is_dir():
            return None

        schematic_files = list(search_dir.glob("*.kicad_sch"))
        if not schematic_files:
            return None

        return self._select_best_file_with_autosave(
            schematic_files, search_dir.name, "schematic"
        )

    def find_pcb_file(self, search_dir: Path) -> Path | None:
        """Find the best PCB file in a directory."""
        if not search_dir.is_dir():
            return None

        pcb_files = list(search_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return None

        return self._select_best_file_with_autosave(pcb_files, search_dir.name, "PCB")

    def discover_project_files(self, search_dir: Path) -> ProjectFiles:
        """Discover all project files in a directory."""
        return ProjectFiles(
            project_file=self.find_project_file(search_dir),
            schematic_file=self.find_schematic_file(search_dir),
            pcb_file=self.find_pcb_file(search_dir),
        )

    def _select_best_file(self, files: list[Path], dir_name: str) -> Path:
        """Select best file from list, preferring directory name matches."""
        matching = [f for f in files if f.stem == dir_name]
        if matching:
            return matching[0]

        return sorted(files)[0]

    def _select_best_file_with_autosave(
        self, files: list[Path], dir_name: str, file_type: str
    ) -> Path:
        """Select best file handling autosave files with warnings."""
        normal_files = [f for f in files if not f.name.startswith("_autosave-")]
        autosave_files = [f for f in files if f.name.startswith("_autosave-")]

        matching_normal = [f for f in normal_files if f.stem == dir_name]
        if matching_normal:
            return matching_normal[0]

        if normal_files:
            return sorted(normal_files)[0]

        if autosave_files:
            print(
                f"WARNING: Only autosave {file_type} files found in {files[0].parent}. "
                f"Using autosave file (may be incomplete).",
                file=sys.stderr,
            )
            matching_autosave = [
                f for f in autosave_files if f.stem == f"_autosave-{dir_name}"
            ]
            if matching_autosave:
                return matching_autosave[0]
            return sorted(autosave_files)[0]

        return files[0]
