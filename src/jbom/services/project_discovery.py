"""ProjectDiscovery service for finding KiCad project files.

Stateful service that discovers KiCad project files (.kicad_pro, .pro),
schematic files (.kicad_sch), and PCB files (.kicad_pcb) in directories.
Follows domain service architecture with constructor-configured behavior.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jbom.common.options import GeneratorOptions

__all__ = ["ProjectDiscovery", "ProjectFiles"]


@dataclass
class ProjectFiles:
    """Data structure holding discovered project files."""

    project_file: Optional[Path] = None
    schematic_file: Optional[Path] = None
    pcb_file: Optional[Path] = None


class ProjectDiscovery:
    """Service for discovering KiCad project files in directories.

    Stateful service with constructor-configured search behavior.
    Handles autosave files, directory name matching, and multiple project scenarios.
    """

    def __init__(
        self, strict_mode: bool = False, options: Optional[GeneratorOptions] = None
    ):
        """Initialize ProjectDiscovery service.

        Args:
            strict_mode: If True, raise exception when multiple project files found.
                        If False, pick the first one alphabetically.
            options: Optional GeneratorOptions for verbose output etc.
        """
        self.strict_mode = strict_mode
        self.options = options or GeneratorOptions()

    def find_project_file(self, search_dir: Path) -> Optional[Path]:
        """Find the best KiCad project file in a directory.

        Args:
            search_dir: Directory to search in

        Returns:
            Path to .kicad_pro or .pro file, or None if not found

        Raises:
            ValueError: If strict_mode=True and multiple projects found
        """
        if not search_dir.is_dir():
            return None

        # Find project files (prefer .kicad_pro over legacy .pro)
        kicad_pro_files = list(search_dir.glob("*.kicad_pro"))
        pro_files = list(search_dir.glob("*.pro"))

        # Check for multiple projects in strict mode
        total_projects = len(kicad_pro_files) + len(pro_files)
        if self.strict_mode and total_projects > 1:
            raise ValueError(
                f"Multiple project files found in {search_dir}. "
                f"Found {len(kicad_pro_files)} .kicad_pro and {len(pro_files)} .pro files. "
                f"Please specify a specific project file."
            )

        # Prefer .kicad_pro files
        if kicad_pro_files:
            # If legacy also present, emit UX note selecting modern file
            try:
                import sys as _sys

                if pro_files:
                    print(
                        f"using modern project file {sorted(kicad_pro_files)[0].name}",
                        file=_sys.stderr,
                    )
            except Exception:
                pass
            return self._select_best_file(kicad_pro_files, search_dir.name)

        # Fall back to legacy .pro files
        if pro_files:
            try:
                import sys as _sys

                print(
                    f"using legacy project file {sorted(pro_files)[0].name}",
                    file=_sys.stderr,
                )
            except Exception:
                pass
            return self._select_best_file(pro_files, search_dir.name)

        return None

    def find_schematic_file(self, search_dir: Path) -> Optional[Path]:
        """Find the best schematic file in a directory.

        Args:
            search_dir: Directory to search in

        Returns:
            Path to .kicad_sch file, or None if not found
        """
        if not search_dir.is_dir():
            return None

        schematic_files = list(search_dir.glob("*.kicad_sch"))
        if not schematic_files:
            return None

        return self._select_best_file_with_autosave(
            schematic_files, search_dir.name, "schematic"
        )

    def find_pcb_file(self, search_dir: Path) -> Optional[Path]:
        """Find the best PCB file in a directory.

        Args:
            search_dir: Directory to search in

        Returns:
            Path to .kicad_pcb file, or None if not found
        """
        if not search_dir.is_dir():
            return None

        pcb_files = list(search_dir.glob("*.kicad_pcb"))
        if not pcb_files:
            return None

        return self._select_best_file_with_autosave(pcb_files, search_dir.name, "PCB")

    def discover_project_files(self, search_dir: Path) -> ProjectFiles:
        """Discover all project files in a directory.

        Args:
            search_dir: Directory to search in

        Returns:
            ProjectFiles object with discovered file paths
        """
        return ProjectFiles(
            project_file=self.find_project_file(search_dir),
            schematic_file=self.find_schematic_file(search_dir),
            pcb_file=self.find_pcb_file(search_dir),
        )

    def _select_best_file(self, files: list[Path], dir_name: str) -> Path:
        """Select best file from list, preferring directory name matches.

        Args:
            files: List of file paths
            dir_name: Directory name to match against

        Returns:
            Best file path
        """
        # Prefer files matching directory name
        matching = [f for f in files if f.stem == dir_name]
        if matching:
            return matching[0]

        # Return first file alphabetically
        return sorted(files)[0]

    def _select_best_file_with_autosave(
        self, files: list[Path], dir_name: str, file_type: str
    ) -> Path:
        """Select best file handling autosave files with warnings.

        Args:
            files: List of file paths
            dir_name: Directory name to match against
            file_type: Type of file for warning messages

        Returns:
            Best file path
        """
        # Separate autosave and normal files
        normal_files = [f for f in files if not f.name.startswith("_autosave-")]
        autosave_files = [f for f in files if f.name.startswith("_autosave-")]

        # Prefer normal files that match directory name
        matching_normal = [f for f in normal_files if f.stem == dir_name]
        if matching_normal:
            return matching_normal[0]

        # Use any normal file
        if normal_files:
            return sorted(normal_files)[0]

        # Fall back to autosave files with warning
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

        # Should not reach here given our input filtering
        return files[0]
