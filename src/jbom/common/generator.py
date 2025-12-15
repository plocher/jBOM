"""Base generator classes for unified BOM and placement generation.

Provides abstract base classes and interfaces for all output generators.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = [
    "FieldProvider",
    "Generator",
    "GeneratorOptions",
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
class GeneratorOptions:
    """Base options for all generators."""

    verbose: bool = False
    debug: bool = False
    fields: Optional[List[str]] = None


class Generator(FieldProvider):
    """Abstract base class for all output generators (BOM, placement, etc).

    Provides common interface for:
    - Field discovery and selection
    - Entry generation
    - CSV output writing

    Subclasses must implement:
    - generate(): Create output entries
    - write_csv(): Write entries to CSV
    - get_available_fields(): List available output fields
    - default_preset(): Return default field preset name
    """

    def __init__(self, options: GeneratorOptions):
        """Initialize generator with options.

        Args:
            options: Generator configuration options
        """
        self.options = options

    @abstractmethod
    def generate(self) -> List[Any]:
        """Generate output entries.

        Returns:
            List of entry objects (type depends on generator)
        """
        pass

    @abstractmethod
    def write_csv(self, output_path: Path, fields: List[str]) -> None:
        """Write output entries to CSV file.

        Args:
            output_path: Path to output CSV file
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
