"""ProjectFileResolver service for converting user inputs to file paths.

Stateful service that converts various user inputs (directories, base names,
explicit files) to proper file paths using ProjectContext for intelligent resolution.
Maintains backward compatibility while providing project-centric enhancements.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

from jbom.services.project_context import ProjectContext
from jbom.common.options import GeneratorOptions

__all__ = ["ProjectFileResolver", "ResolvedInput"]


@dataclass
class ResolvedInput:
    """Data structure representing resolved user input."""

    input_type: str  # "explicit_file", "directory", "base_name"
    resolved_path: Path  # The actual file path to use
    project_context: Optional[ProjectContext] = None

    @property
    def is_schematic(self) -> bool:
        """Check if resolved path is a schematic file."""
        return self.resolved_path.suffix == ".kicad_sch"

    @property
    def is_pcb(self) -> bool:
        """Check if resolved path is a PCB file."""
        return self.resolved_path.suffix == ".kicad_pcb"

    def get_matching_pcb(self) -> Optional[Path]:
        """Get matching PCB file for schematic."""
        if not self.is_schematic or not self.project_context:
            return None
        return self.project_context.find_matching_pcb_for_schematic(self.resolved_path)

    def get_matching_schematic(self) -> Optional[Path]:
        """Get matching schematic file for PCB."""
        if not self.is_pcb or not self.project_context:
            return None
        return self.project_context.find_matching_schematic_for_pcb(self.resolved_path)

    def get_hierarchical_files(self) -> List[Path]:
        """Get all hierarchical schematic files."""
        if not self.is_schematic or not self.project_context:
            return [self.resolved_path]
        return self.project_context.get_hierarchical_schematic_files()

    def get_suggestions(self) -> Dict[str, str]:
        """Get helpful suggestions based on current context."""
        suggestions = {}

        if not self.project_context:
            return suggestions

        # Suggest missing files
        missing_files = self.project_context.suggest_missing_files()
        for key, path in missing_files.items():
            file_type = key.replace("suggested_", "")
            suggestions[file_type] = f"Consider creating {path.name}"

        return suggestions


class ProjectFileResolver:
    """Service for resolving user inputs to proper file paths.

    Stateful service with constructor-configured behavior.
    Converts directories, base names, and explicit files to resolved paths
    using ProjectContext for intelligent project-aware resolution.
    """

    def __init__(
        self,
        prefer_pcb: bool = False,
        target_file_type: Optional[str] = None,
        options: Optional[GeneratorOptions] = None,
    ):
        """Initialize ProjectFileResolver service.

        Args:
            prefer_pcb: If True, prefer PCB files when multiple types available
            target_file_type: Target file type ('schematic', 'pcb', 'project') for cross-command intelligence
            options: Optional GeneratorOptions for verbose output etc.
        """
        self.prefer_pcb = prefer_pcb
        self.target_file_type = target_file_type
        self.options = options or GeneratorOptions()

    def resolve_input(self, user_input: Union[str, Path]) -> ResolvedInput:
        """Resolve user input to actual file path.

        Args:
            user_input: User input (directory, base name, or explicit file)

        Returns:
            ResolvedInput with resolved path and context

        Raises:
            FileNotFoundError: If specified file doesn't exist
            ValueError: If directory contains no KiCad files
        """
        input_path = Path(user_input).expanduser()

        # Handle current directory
        if str(user_input) == ".":
            return self._resolve_directory(Path.cwd())

        # Handle explicit file paths (backward compatibility)
        if input_path.is_file():
            return self._resolve_explicit_file(input_path.resolve())

        # Handle directory paths
        if input_path.is_dir():
            return self._resolve_directory(input_path.resolve())

        # Handle explicit file paths that don't exist
        if input_path.suffix in (".kicad_sch", ".kicad_pcb", ".kicad_pro", ".pro"):
            if not input_path.exists():
                # Normalize error messages to match Gherkin expectations
                if input_path.suffix == ".kicad_sch":
                    raise FileNotFoundError("No schematic file found")
                if input_path.suffix == ".kicad_pcb":
                    raise FileNotFoundError("No PCB file found")
                if input_path.suffix in (".kicad_pro", ".pro"):
                    raise FileNotFoundError("Project file not found")
                raise FileNotFoundError(f"File not found: {input_path}")
            return self._resolve_explicit_file(input_path.resolve())

        # Handle base name resolution (try current directory)
        return self._resolve_base_name(str(user_input), Path.cwd())

    def _resolve_explicit_file(self, file_path: Path) -> ResolvedInput:
        """Resolve explicit file path with project context if available."""
        if not file_path.exists():
            # Normalize error messages to match Gherkin expectations
            if file_path.suffix == ".kicad_sch":
                raise FileNotFoundError("No schematic file found")
            if file_path.suffix == ".kicad_pcb":
                raise FileNotFoundError("No PCB file found")
            if file_path.suffix in (".kicad_pro", ".pro"):
                raise FileNotFoundError("Project file not found")
            raise FileNotFoundError(f"File not found: {file_path}")

        # Try to create project context from parent directory
        project_context = None
        try:
            project_context = ProjectContext(file_path.parent, self.options)
        except ValueError:
            # No project context available, that's okay for explicit files
            pass

        return ResolvedInput(
            input_type="explicit_file",
            resolved_path=file_path,
            project_context=project_context,
        )

    def _resolve_directory(self, dir_path: Path) -> ResolvedInput:
        """Resolve directory input to appropriate file."""
        # Create project context to discover files
        try:
            project_context = ProjectContext(dir_path, self.options)
        except ValueError as e:
            # Re-raise with more specific error message
            raise ValueError(str(e))

        # Determine which file to return based on target file type and preferences
        resolved_path = self._select_target_file(project_context, dir_path)

        # Emit discovery messages expected by UX tests
        try:
            import sys as _sys

            base_name = project_context.project_base_name
            if project_context.project_file:
                print(f"found project {base_name}", file=_sys.stderr)
            if project_context.schematic_file:
                print(
                    f"found schematic {project_context.schematic_file.name}",
                    file=_sys.stderr,
                )
            if project_context.pcb_file:
                print(f"found pcb {project_context.pcb_file.name}", file=_sys.stderr)
        except Exception:
            pass

        return ResolvedInput(
            input_type="directory",
            resolved_path=resolved_path,
            project_context=project_context,
        )

    def _resolve_base_name(self, base_name: str, search_dir: Path) -> ResolvedInput:
        """Resolve base name to file in search directory."""
        # Try to find files with matching base name
        possible_schematic = search_dir / f"{base_name}.kicad_sch"
        possible_pcb = search_dir / f"{base_name}.kicad_pcb"

        # Check what exists
        schematic_exists = possible_schematic.exists()
        pcb_exists = possible_pcb.exists()

        if not schematic_exists and not pcb_exists:
            raise FileNotFoundError(
                f"No files found for base name '{base_name}' in {search_dir}. "
                f"Expected {base_name}.kicad_sch or {base_name}.kicad_pcb"
            )

        # Create project context
        try:
            project_context = ProjectContext(search_dir, self.options)
        except ValueError:
            project_context = None

        # Determine which file to return
        if self.prefer_pcb and pcb_exists:
            resolved_path = possible_pcb
        elif schematic_exists:
            resolved_path = possible_schematic
        else:
            resolved_path = possible_pcb

        return ResolvedInput(
            input_type="base_name",
            resolved_path=resolved_path,
            project_context=project_context,
        )

    def _select_target_file(
        self, project_context: ProjectContext, search_path: Path
    ) -> Path:
        """Select the appropriate file based on target file type and cross-command intelligence."""
        # If target file type is specified, try to find that type first
        if self.target_file_type == "schematic":
            if project_context.schematic_file:
                return project_context.schematic_file
            else:
                # Normalize error string to match test expectations
                raise ValueError("No schematic file found")

        elif self.target_file_type == "pcb":
            if project_context.pcb_file:
                return project_context.pcb_file
            else:
                # Normalize error string to match test expectations
                raise ValueError("No PCB file found")

        elif self.target_file_type == "project":
            if project_context.project_file:
                return project_context.project_file
            else:
                raise ValueError(
                    f"No project file found in {search_path}. "
                    f"Expected .kicad_pro file."
                )

        # Default behavior - prefer based on prefer_pcb flag
        if self.prefer_pcb and project_context.pcb_file:
            return project_context.pcb_file
        elif project_context.schematic_file:
            return project_context.schematic_file
        elif project_context.pcb_file:
            return project_context.pcb_file
        else:
            # Normalize combined-missing error to emphasize schematic/pcb absence
            raise ValueError("No schematic file found")

    def resolve_for_wrong_file_type(
        self, resolved_input: ResolvedInput, target_type: str
    ) -> ResolvedInput:
        """Handle cases where user provided wrong file type for command.

        Args:
            resolved_input: Originally resolved input
            target_type: Target file type needed ('schematic', 'pcb')

        Returns:
            New ResolvedInput with correct file type

        Raises:
            ValueError: If target file type cannot be found
        """
        if not resolved_input.project_context:
            raise ValueError(
                f"Cannot resolve {target_type} file - no project context available. "
                f"Try running command from project directory."
            )

        context = resolved_input.project_context

        if target_type == "schematic":
            if context.schematic_file:
                return ResolvedInput(
                    input_type="cross_resolved",
                    resolved_path=context.schematic_file,
                    project_context=context,
                )
            else:
                raise ValueError(
                    f"No schematic file found for project {context.project_base_name}. "
                    f"Expected {context.get_expected_schematic_path().name}"
                )

        elif target_type == "pcb":
            if context.pcb_file:
                return ResolvedInput(
                    input_type="cross_resolved",
                    resolved_path=context.pcb_file,
                    project_context=context,
                )
            else:
                raise ValueError(
                    f"No PCB file found for project {context.project_base_name}. "
                    f"Expected {context.get_expected_pcb_path().name}"
                )

        else:
            raise ValueError(f"Unsupported target file type: {target_type}")
