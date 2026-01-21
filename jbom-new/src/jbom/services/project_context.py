"""ProjectContext service for managing project state and file relationships.

Stateful service that maintains KiCad project context including file paths,
hierarchical relationships, and cross-file intelligence.
Follows domain service architecture with constructor-configured behavior.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from jbom.services.project_discovery import ProjectDiscovery
from jbom.common.options import GeneratorOptions

__all__ = ["ProjectContext"]


class ProjectContext:
    """Service for managing KiCad project context and file relationships.

    Stateful service that discovers and maintains project file relationships,
    hierarchical schematic processing, and cross-file intelligence.
    """

    def __init__(
        self, project_directory: Path, options: Optional[GeneratorOptions] = None
    ):
        """Initialize ProjectContext service.

        Args:
            project_directory: Directory containing KiCad project files
            options: Optional GeneratorOptions for verbose output etc.

        Raises:
            ValueError: If no project files found in directory
        """
        self.project_directory = project_directory
        self.options = options or GeneratorOptions()

        # Discover project files using ProjectDiscovery service
        discovery = ProjectDiscovery(strict_mode=False, options=self.options)
        self.project_files = discovery.discover_project_files(project_directory)

        # Validate that we found at least some project files
        if (
            not self.project_files.project_file
            and not self.project_files.schematic_file
            and not self.project_files.pcb_file
        ):
            raise ValueError(
                f"No project files found in {project_directory}. "
                f"Expected at least one of: .kicad_pro, .kicad_sch, or .kicad_pcb files."
            )

    @property
    def project_file(self) -> Optional[Path]:
        """Get the project file path."""
        return self.project_files.project_file

    @property
    def schematic_file(self) -> Optional[Path]:
        """Get the schematic file path."""
        return self.project_files.schematic_file

    @property
    def pcb_file(self) -> Optional[Path]:
        """Get the PCB file path."""
        return self.project_files.pcb_file

    @property
    def project_base_name(self) -> str:
        """Get the base name for the project (without extension)."""
        # Use project file name if available
        if self.project_file:
            return self.project_file.stem
        # Use schematic file name if available
        elif self.schematic_file:
            return self.schematic_file.stem
        # Use PCB file name if available
        elif self.pcb_file:
            return self.pcb_file.stem
        # Fall back to directory name
        else:
            return self.project_directory.name

    def get_expected_schematic_path(self) -> Path:
        """Get expected path for schematic file based on project base name."""
        return self.project_directory / f"{self.project_base_name}.kicad_sch"

    def get_expected_pcb_path(self) -> Path:
        """Get expected path for PCB file based on project base name."""
        return self.project_directory / f"{self.project_base_name}.kicad_pcb"

    def get_expected_project_path(self) -> Path:
        """Get expected path for project file based on project base name."""
        return self.project_directory / f"{self.project_base_name}.kicad_pro"

    def get_hierarchical_schematic_files(self) -> List[Path]:
        """Get all schematic files in hierarchical design.

        Returns:
            List of Path objects for all schematic files (main + sheets)
        """
        if not self.schematic_file:
            return []

        files = []
        processed = set()

        # Process main schematic and any hierarchical sheets
        self._process_hierarchical_schematic(self.schematic_file, files, processed)

        return files

    def find_matching_pcb_for_schematic(self, schematic_path: Path) -> Optional[Path]:
        """Find matching PCB file for a schematic file.

        Args:
            schematic_path: Path to schematic file

        Returns:
            Path to matching PCB file, or None if not found
        """
        # Try exact base name match
        expected_pcb = schematic_path.with_suffix(".kicad_pcb")
        if expected_pcb.exists():
            return expected_pcb

        # If schematic is in project context, try project base name
        if self.pcb_file and schematic_path.parent == self.project_directory:
            return self.pcb_file

        return None

    def find_matching_schematic_for_pcb(self, pcb_path: Path) -> Optional[Path]:
        """Find matching schematic file for a PCB file.

        Args:
            pcb_path: Path to PCB file

        Returns:
            Path to matching schematic file, or None if not found
        """
        # Try exact base name match
        expected_sch = pcb_path.with_suffix(".kicad_sch")
        if expected_sch.exists():
            return expected_sch

        # If PCB is in project context, try project schematic
        if self.schematic_file and pcb_path.parent == self.project_directory:
            return self.schematic_file

        return None

    def get_project_metadata(self) -> Dict[str, Any]:
        """Get project metadata.

        Returns:
            Dictionary with project metadata
        """
        metadata = {
            "project_base_name": self.project_base_name,
            "project_directory": str(self.project_directory),
            "has_project_file": self.project_file is not None,
            "has_schematic_file": self.schematic_file is not None,
            "has_pcb_file": self.pcb_file is not None,
        }

        if self.project_file:
            metadata["project_file"] = str(self.project_file)

        if self.schematic_file:
            metadata["schematic_file"] = str(self.schematic_file)
            hierarchical_files = self.get_hierarchical_schematic_files()
            metadata["is_hierarchical"] = len(hierarchical_files) > 1
            metadata["hierarchical_files"] = [str(f) for f in hierarchical_files]

        if self.pcb_file:
            metadata["pcb_file"] = str(self.pcb_file)

        return metadata

    def suggest_missing_files(self) -> Dict[str, Path]:
        """Suggest paths for missing related files.

        Returns:
            Dictionary with suggested file paths
        """
        suggestions = {}

        # Suggest PCB if missing
        if not self.pcb_file:
            suggestions["suggested_pcb"] = self.get_expected_pcb_path()

        # Suggest schematic if missing
        if not self.schematic_file:
            suggestions["suggested_schematic"] = self.get_expected_schematic_path()

        # Suggest project file if missing
        if not self.project_file:
            suggestions["suggested_project"] = self.get_expected_project_path()

        return suggestions

    def _process_hierarchical_schematic(
        self, schematic_path: Path, files: List[Path], processed: set[Path]
    ) -> None:
        """Recursively process hierarchical schematic files.

        Args:
            schematic_path: Path to schematic file to process
            files: List to accumulate found files
            processed: Set of already processed files to avoid cycles
        """
        if schematic_path in processed or not schematic_path.exists():
            return

        processed.add(schematic_path)
        files.append(schematic_path)

        # Extract referenced sheet files
        sheet_files = self._extract_sheet_files(schematic_path)

        # Process each referenced sheet
        for sheet_file in sheet_files:
            sheet_path = self.project_directory / sheet_file
            if not sheet_path.exists():
                try:
                    import sys as _sys

                    print(f"missing sheet {sheet_file}", file=_sys.stderr)
                except Exception:
                    pass
                # Continue without the missing sheet
                continue
            self._process_hierarchical_schematic(sheet_path, files, processed)

    def _extract_sheet_files(self, schematic_path: Path) -> List[str]:
        """Extract referenced sheet file names from a schematic.

        Args:
            schematic_path: Path to schematic file

        Returns:
            List of referenced sheet file names
        """
        try:
            content = schematic_path.read_text(encoding="utf-8")

            # Look for (property "Sheetfile" "filename.kicad_sch") patterns
            sheet_pattern = r'\(property\s+"Sheetfile"\s+"([^"]+\.kicad_sch)"'
            matches = re.findall(sheet_pattern, content)

            return matches

        except Exception as e:
            if self.options.verbose:
                print(
                    f"Warning: Could not parse hierarchical references from {schematic_path}: {e}"
                )
            return []
