"""Base classes and utilities for CLI commands.

Provides common patterns for BOM and POS command implementations.
"""
from __future__ import annotations
import argparse
from abc import ABC, abstractmethod
import sys
from pathlib import Path

from jbom.common.config import get_config

__all__ = [
    "Command",
    "OutputMode",
]


class OutputMode:
    """Output destination modes"""

    FILE = "file"
    CONSOLE = "console"
    STDOUT = "stdout"


class Command(ABC):
    """Base class for CLI subcommands (bom, pos)"""

    def __init__(self):
        self.parser: argparse.ArgumentParser | None = None

    @abstractmethod
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure command-specific arguments.

        Args:
            parser: Subparser for this command
        """
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the command.

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass

    def handle_errors(self, args: argparse.Namespace) -> int:
        """Execute command with standard error handling.

        Args:
            args: Parsed arguments

        Returns:
            Exit code
        """
        try:
            return self.execute(args)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except (ValueError, KeyError, ImportError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
            return 1

    @staticmethod
    def determine_output_mode(output_arg: str | None) -> tuple[OutputMode, Path | None]:
        """Determine output mode from argument.

        Args:
            output_arg: Output argument from command line

        Returns:
            Tuple of (output_mode, output_path)
        """
        if not output_arg:
            return (OutputMode.FILE, None)

        output_str = output_arg.lower()
        if output_str == "console":
            return (OutputMode.CONSOLE, None)
        elif output_str in ("-", "stdout"):
            return (OutputMode.STDOUT, Path("-"))
        else:
            return (OutputMode.FILE, Path(output_arg))

    @staticmethod
    def add_common_output_args(parser: argparse.ArgumentParser) -> None:
        """Add standard output-related arguments.

        Args:
            parser: Parser to add arguments to
        """
        parser.add_argument(
            "-o",
            "--output",
            metavar="PATH",
            help="""Output destination:
  filename.csv  - Write to file
  -             - CSV to stdout (pipeline-friendly)
  stdout        - CSV to stdout (pipeline-friendly)
  console       - Formatted table to console (human-readable)
  (default: auto-generated filename in input directory)""",
        )

    @staticmethod
    def add_fabricator_field_args(
        parser: argparse.ArgumentParser, field_help: str
    ) -> None:
        """Add --fields and dynamic fabricator flag arguments.

        Args:
            parser: Parser to add arguments to
            field_help: Help text for --fields argument
        """
        parser.add_argument(
            "-f",
            "--fields",
            metavar="FIELDS",
            help=field_help,
        )

        # Dynamically add fabricator flags from configuration
        try:
            config = get_config()
            for fabricator in config.fabricators:
                for flag in fabricator.cli_flags:
                    # Remove leading '--' to get the argument name
                    flag_name = flag.lstrip("-")
                    parser.add_argument(
                        flag,
                        action="store_true",
                        help=f"Use {fabricator.name} preset: {fabricator.description or 'optimized for ' + fabricator.name}",
                        dest=f"fabricator_{flag_name}",  # Store as fabricator_jlc, fabricator_pcbway, etc.
                    )
        except Exception:
            # If config loading fails, just continue without fabricator flags
            # This ensures jBOM still works even if configuration is broken
            pass
