"""Plugin CLI registration system.

Allows plugins to register their CLI commands without coupling to main.py.
Each plugin can define its argument parser and handler independently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
import argparse


@dataclass
class PluginCommand:
    """Represents a plugin's CLI command registration."""

    name: str  # Command name (e.g., 'pos')
    help: str  # Help text for command
    handler: Callable[[argparse.Namespace], int]  # Function to handle parsed args
    configure_parser: Callable[
        [argparse.ArgumentParser], None
    ]  # Function to add arguments


class PluginCLIRegistry:
    """Registry for plugin CLI commands."""

    def __init__(self):
        self._commands: Dict[str, PluginCommand] = {}

    def register(
        self,
        name: str,
        help: str,
        handler: Callable[[argparse.Namespace], int],
        configure_parser: Callable[[argparse.ArgumentParser], None],
    ) -> None:
        """Register a plugin command.

        Args:
            name: Command name
            help: Help text
            handler: Function that takes parsed args and returns exit code
            configure_parser: Function that adds arguments to parser
        """
        if name in self._commands:
            raise ValueError(f"Command '{name}' already registered")

        self._commands[name] = PluginCommand(
            name=name, help=help, handler=handler, configure_parser=configure_parser
        )

    def get_command(self, name: str) -> Optional[PluginCommand]:
        """Get a registered command by name."""
        return self._commands.get(name)

    def list_commands(self) -> List[str]:
        """List all registered command names."""
        return list(self._commands.keys())

    def configure_subparsers(self, subparsers: argparse._SubParsersAction) -> None:
        """Configure argparse subparsers with all registered commands."""
        for cmd in self._commands.values():
            parser = subparsers.add_parser(cmd.name, help=cmd.help)
            cmd.configure_parser(parser)


# Global registry instance
_plugin_cli_registry = PluginCLIRegistry()


def register_command(
    name: str,
    help: str,
    handler: Callable[[argparse.Namespace], int],
    configure_parser: Callable[[argparse.ArgumentParser], None],
) -> None:
    """Register a plugin CLI command."""
    _plugin_cli_registry.register(name, help, handler, configure_parser)


def get_registry() -> PluginCLIRegistry:
    """Get the global plugin CLI registry."""
    return _plugin_cli_registry
