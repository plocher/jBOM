"""Command plugin infrastructure.

Provides command registry and auto-discovery for CLI subcommands.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import importlib
import pkgutil

if TYPE_CHECKING:
    from typing import Dict, Type, List
    from jbom.cli.commands.base import Command

__all__ = [
    "CommandRegistry",
    "discover_commands",
]


class CommandRegistry:
    """Central registry for command plugins with auto-registration."""

    _commands: Dict[str, Type[Command]] = {}

    @classmethod
    def register(cls, command_class: Type[Command]) -> None:
        """Register a command plugin.

        Args:
            command_class: Command class to register

        Raises:
            ValueError: If command has no metadata
        """
        if not command_class.metadata:
            raise ValueError(f"Command {command_class.__name__} missing metadata")

        cls._commands[command_class.metadata.name] = command_class

    @classmethod
    def get(cls, name: str) -> Type[Command] | None:
        """Get command class by name.

        Args:
            name: Command name

        Returns:
            Command class or None if not found
        """
        return cls._commands.get(name)

    @classmethod
    def list_commands(cls) -> List[str]:
        """List all registered command names.

        Returns:
            Sorted list of command names
        """
        return sorted(cls._commands.keys())

    @classmethod
    def get_all(cls) -> Dict[str, Type[Command]]:
        """Get all registered commands.

        Returns:
            Dictionary mapping command names to command classes
        """
        return cls._commands.copy()


def discover_commands(package_path: str = "jbom.cli.commands.builtin") -> None:
    """Discover and import all command modules in a package.

    This triggers the auto-registration mechanism via Command.__init_subclass__().

    Args:
        package_path: Dotted path to package containing command modules
    """
    try:
        package = importlib.import_module(package_path)
    except ImportError:
        # Package doesn't exist, skip discovery
        return

    # Import all modules in the package
    # This triggers class definitions and auto-registration
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if not ispkg:  # Only import module files, not packages
            try:
                importlib.import_module(f"{package_path}.{modname}")
            except ImportError as e:
                # Skip modules that fail to import
                # This allows partial plugin sets to work
                import logging

                logging.debug(f"Failed to import {package_path}.{modname}: {e}")
