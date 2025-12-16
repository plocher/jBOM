"""Base generator classes for unified BOM and placement generation.

Provides abstract base classes and interfaces for all output generators.
Implements Template Method pattern for consistent generation flow.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

__all__ = [
    "FieldProvider",
    "Generator",
    "GeneratorOptions",
    "DiagnosticEvent",
    "Diagnostics",
]


class FieldProvider(ABC):
    """Interface for objects that provide available output fields."""

    @abstractmethod
    def get_available_fields(self) -> Dict[str, str]:
        """Return dictionary of field_name -> description for all available fields.

        Returns:
            Dict mapping normalized field names to human-readable descriptions
        """
        pass


@dataclass
class DiagnosticEvent:
    level: str  # info | warning | error
    code: str
    message: str
    context: Optional[Dict[str, Any]] = None
    exception: Optional[str] = None


class Diagnostics:
    """Collects non-fatal diagnostics during generation.

    Use this to record parse fallbacks, data coercions, missing fields, etc.
    Keeps generators pure while still exposing rich debug context to callers.
    """

    def __init__(self) -> None:
        self.events: List[DiagnosticEvent] = []

    def info(self, code: str, message: str, **context: Any) -> None:
        self.events.append(DiagnosticEvent("info", code, message, context or None))

    def warn(self, code: str, message: str, **context: Any) -> None:
        self.events.append(DiagnosticEvent("warning", code, message, context or None))

    def error(
        self,
        code: str,
        message: str,
        exc: Optional[BaseException] = None,
        **context: Any,
    ) -> None:
        exc_str = f"{type(exc).__name__}: {exc}" if exc else None
        self.events.append(
            DiagnosticEvent("error", code, message, context or None, exception=exc_str)
        )

    def as_dicts(self) -> List[Dict[str, Any]]:
        return [
            {
                "level": e.level,
                "code": e.code,
                "message": e.message,
                **({"context": e.context} if e.context else {}),
                **({"exception": e.exception} if e.exception else {}),
            }
            for e in self.events
        ]


@dataclass
class GeneratorOptions:
    """Base options for all generators."""

    verbose: bool = False
    debug: bool = False
    fields: Optional[List[str]] = None


class Generator(FieldProvider):
    """Abstract base class for all output generators (BOM, placement, etc).

    Implements Template Method pattern:
    1. discover_input() - Find the correct input file(s)
    2. load_input() - Parse input file(s) into data structures
    3. process() - Transform input data into output entries
    4. write_output() - Write entries to file/stdout/console

    The run() method orchestrates these steps with common logic for:
    - File discovery (directory vs explicit file)
    - Output routing (file vs stdout vs console)
    - Error handling
    - Result dictionary structure

    Subclasses must implement:
    - discover_input(): Find input file given directory
    - load_input(): Load and parse input file
    - process(): Generate output entries from loaded data
    - write_csv(): Write entries to CSV
    - get_available_fields(): List available output fields
    - default_preset(): Return default field preset name
    """

    def __init__(self, options: Optional[GeneratorOptions] = None):
        """Initialize generator with options.

        Args:
            options: Generator configuration options
        """
        self.options = options or GeneratorOptions()
        # Diagnostics collector available to subclasses as self.diag
        self.diagnostics = Diagnostics()
        # Convenience alias
        self.diag = self.diagnostics

    @abstractmethod
    def discover_input(self, input_path: Path) -> Path:
        """Discover the actual input file from a directory.

        Args:
            input_path: Directory to search

        Returns:
            Path to the discovered input file

        Raises:
            FileNotFoundError: If no suitable file found
        """
        pass

    @abstractmethod
    def load_input(self, input_path: Path) -> Any:
        """Load and parse input file(s).

        Args:
            input_path: Path to input file

        Returns:
            Loaded data structure (type depends on generator)
        """
        pass

    @abstractmethod
    def process(self, data: Any) -> tuple[List[Any], Dict[str, Any]]:
        """Process loaded data into output entries.

        Args:
            data: Loaded data from load_input()

        Returns:
            Tuple of (entries, metadata_dict)
            - entries: List of output entry objects
            - metadata: Additional information for result dict
        """
        pass

    @abstractmethod
    def write_csv(
        self, entries: List[Any], output_path: Path, fields: List[str]
    ) -> None:
        """Write output entries to CSV file.

        Args:
            entries: List of entry objects to write
            output_path: Path to output CSV file (or "-" for stdout)
            fields: List of field names to include in output
        """
        pass

    @abstractmethod
    def default_preset(self) -> str:
        """Return the default field preset name for this generator.

        Returns:
            Preset name string (e.g., 'standard', 'kicad_pos')
        """
        pass

    def run(
        self,
        input: Union[str, Path],
        output: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Template method: orchestrate the complete generation flow.

        This method implements the common flow for all generators:
        1. Convert inputs to Path objects
        2. Auto-discover input file if directory given
        3. Validate input file exists
        4. Load input data
        5. Process data into entries
        6. Write output if specified
        7. Return result dictionary

        Args:
            input: Path to input directory or file
            output: Optional output path (file, "-" for stdout, "console" for formatted)
            **kwargs: Additional generator-specific arguments

        Returns:
            Dictionary containing:
            - data: Loaded input data
            - entries: Generated output entries
            - metadata: Generator-specific information

        Raises:
            FileNotFoundError: If input file not found
        """
        # 1. Convert to Path
        input_path = Path(input)
        output_path = Path(output) if output else None

        # 2. Auto-discover if directory
        if input_path.is_dir():
            input_path = self.discover_input(input_path)

        # 3. Validate existence
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # 4. Load input
        data = self.load_input(input_path)

        # 5. Process
        entries, metadata = self.process(data)

        # 6. Write output if specified
        if output_path:
            output_str = str(output_path).lower()
            if output_str not in ("console",):  # console handled by caller
                fields = self.options.fields or self._get_default_fields()
                self.write_csv(entries, output_path, fields)

        # 7. Return result (include diagnostics)
        return {
            "data": data,
            "entries": entries,
            **metadata,  # Merge generator-specific metadata
            "diagnostics": self.diagnostics.as_dicts(),
        }

    def _get_default_fields(self) -> List[str]:
        """Get default field list for this generator.

        Can be overridden by subclasses for custom behavior.

        Returns:
            List of default field names
        """
        # This is a simple default - subclasses can override
        available = self.get_available_fields()
        return list(available.keys())
