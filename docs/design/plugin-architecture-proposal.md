# Plugin Architecture Proposal for jBOM Subcommands

## Current State Analysis

### Strengths
- Command pattern already in use (base `Command` class)
- Good separation of concerns between CLI and API layers
- Common utilities extracted (`add_project_argument`, `add_common_output_args`)
- Consistent error handling via `handle_errors()`

### Pain Points
1. **Hardcoded Registration**: Commands are manually imported and registered in `main.py`
2. **No Extension Mechanism**: Can't add new commands without modifying core code
3. **Discovery Limitations**: No way to discover available commands programmatically
4. **Tight Coupling**: Main knows about all command implementations

## Proposed Plugin Architecture

### Goals
1. **Discoverable**: Commands auto-register via entry points or directory scanning
2. **Extensible**: Third-party packages can add new commands
3. **Backward Compatible**: Existing commands work without changes
4. **Testable**: Easy to test commands in isolation
5. **Type-Safe**: Maintain Python type hints throughout

### Architecture Overview

```
jbom/
├── cli/
│   ├── __init__.py
│   ├── main.py                    # Simplified, uses plugin loader
│   ├── plugin_loader.py           # NEW: Plugin discovery & loading
│   ├── commands/                  # NEW: Command plugins directory
│   │   ├── __init__.py           # Command base & registry
│   │   ├── base.py               # Moved from commands.py
│   │   ├── builtin/              # Built-in commands
│   │   │   ├── __init__.py
│   │   │   ├── bom.py           # Renamed from bom_command.py
│   │   │   ├── pos.py
│   │   │   ├── inventory.py
│   │   │   ├── annotate.py
│   │   │   └── search.py
│   │   └── external/             # Optional: For third-party plugins
│   ├── formatting.py              # Keep as shared utility
│   └── common.py                  # Keep as shared utility
```

### Key Components

#### 1. Plugin Metadata (Command Descriptor)

```python
# jbom/cli/commands/base.py

from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CommandMetadata:
    """Metadata describing a command plugin."""
    name: str                          # CLI command name (e.g., "bom")
    aliases: List[str] = None          # Alternative names (e.g., ["bill-of-materials"])
    help_text: str = ""                # Short help for command list
    category: str = "general"          # For grouping (e.g., "core", "analysis", "export")
    hidden: bool = False               # Hide from help unless --all flag
    requires_project: bool = True      # Does command need a KiCad project?
    requires_inventory: bool = False   # Does command need inventory file?
    min_version: str = "1.0.0"        # Minimum jBOM version required

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class Command(ABC):
    """Base class for all command plugins."""

    # Subclasses can override this class variable
    metadata: CommandMetadata = None

    def __init_subclass__(cls, **kwargs):
        """Auto-register command subclasses."""
        super().__init_subclass__(**kwargs)
        if cls.metadata is not None:
            CommandRegistry.register(cls)

    @abstractmethod
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure command-specific arguments."""
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the command."""
        pass

    # ... existing methods (handle_errors, determine_output_mode, etc.)
```

#### 2. Command Registry

```python
# jbom/cli/commands/__init__.py

from typing import Dict, Type, List
import importlib
import pkgutil

class CommandRegistry:
    """Central registry for command plugins."""

    _commands: Dict[str, Type[Command]] = {}
    _aliases: Dict[str, str] = {}  # alias -> canonical name

    @classmethod
    def register(cls, command_class: Type[Command]) -> None:
        """Register a command plugin."""
        if not command_class.metadata:
            raise ValueError(f"Command {command_class.__name__} missing metadata")

        meta = command_class.metadata
        cls._commands[meta.name] = command_class

        # Register aliases
        for alias in meta.aliases:
            cls._aliases[alias] = meta.name

    @classmethod
    def get(cls, name: str) -> Type[Command]:
        """Get command by name or alias."""
        # Resolve alias if needed
        canonical_name = cls._aliases.get(name, name)
        return cls._commands.get(canonical_name)

    @classmethod
    def list_commands(cls, category: str = None, include_hidden: bool = False) -> List[str]:
        """List available command names."""
        commands = []
        for name, cmd_class in cls._commands.items():
            meta = cmd_class.metadata
            if not include_hidden and meta.hidden:
                continue
            if category and meta.category != category:
                continue
            commands.append(name)
        return sorted(commands)

    @classmethod
    def get_by_category(cls) -> Dict[str, List[str]]:
        """Group commands by category."""
        categories = {}
        for name, cmd_class in cls._commands.items():
            cat = cmd_class.metadata.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(name)
        return {k: sorted(v) for k, v in sorted(categories.items())}


def discover_commands(package_path: str = None):
    """Discover and import all command modules."""
    if package_path is None:
        package_path = "jbom.cli.commands.builtin"

    package = importlib.import_module(package_path)

    # Import all modules in the package
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if not ispkg:  # Only import module files, not packages
            importlib.import_module(f"{package_path}.{modname}")
```

#### 3. Entry Point Support (for third-party plugins)

```python
# jbom/cli/plugin_loader.py

from importlib.metadata import entry_points
import logging

logger = logging.getLogger(__name__)


def load_entry_point_plugins():
    """Load command plugins from entry points."""
    try:
        # Python 3.10+
        eps = entry_points(group='jbom.commands')
    except TypeError:
        # Python 3.9 fallback
        eps = entry_points().get('jbom.commands', [])

    for ep in eps:
        try:
            ep.load()
            logger.debug(f"Loaded plugin: {ep.name}")
        except Exception as e:
            logger.warning(f"Failed to load plugin {ep.name}: {e}")
```

#### 4. Updated main.py

```python
# jbom/cli/main.py (simplified)

from jbom.cli.commands import CommandRegistry, discover_commands
from jbom.cli.plugin_loader import load_entry_point_plugins


def main(argv: List[str] | None = None) -> int:
    """Main CLI entry point with plugin support."""

    # Discover built-in commands
    discover_commands("jbom.cli.commands.builtin")

    # Load third-party plugins from entry points
    load_entry_point_plugins()

    # Create main parser
    parser = argparse.ArgumentParser(
        prog="jbom",
        description="KiCad Bill of Materials and Placement File Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-V", "--version", action="version",
                       version=f"%(prog)s {_get_version()}")

    # Create subparsers
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    # Register all discovered commands
    for cmd_name in CommandRegistry.list_commands():
        cmd_class = CommandRegistry.get(cmd_name)
        cmd_instance = cmd_class()

        cmd_parser = subparsers.add_parser(
            cmd_name,
            help=cmd_class.metadata.help_text or cmd_class.__doc__,
            aliases=cmd_class.metadata.aliases,
        )
        cmd_instance.setup_parser(cmd_parser)
        cmd_parser.set_defaults(command_instance=cmd_instance)

    # Parse and execute
    args = parser.parse_args(argv)
    return args.command_instance.handle_errors(args)
```

#### 5. Example Command Plugin

```python
# jbom/cli/commands/builtin/bom.py

from jbom.cli.commands.base import Command, CommandMetadata

class BOMCommand(Command):
    """Generate Bill of Materials from KiCad schematic"""

    metadata = CommandMetadata(
        name="bom",
        aliases=["bill-of-materials"],
        help_text="Generate Bill of Materials (BOM) from KiCad schematic",
        category="core",
        requires_project=True,
        requires_inventory=True,
    )

    def setup_parser(self, parser):
        self.add_project_argument(parser)
        parser.add_argument("-i", "--inventory", required=True, ...)
        # ... rest of setup

    def execute(self, args):
        # ... existing implementation
```

### Third-Party Plugin Example

A third-party plugin package structure:

```
jbom-plugin-gerber/
├── pyproject.toml
├── README.md
└── jbom_gerber/
    ├── __init__.py
    └── command.py

# pyproject.toml
[project.entry-points."jbom.commands"]
gerber = "jbom_gerber.command:GerberCommand"
```

```python
# jbom_gerber/command.py

from jbom.cli.commands.base import Command, CommandMetadata

class GerberCommand(Command):
    """Generate Gerber fabrication files"""

    metadata = CommandMetadata(
        name="gerber",
        help_text="Generate Gerber files for PCB fabrication",
        category="export",
        requires_project=True,
        min_version="4.0.0",
    )

    def setup_parser(self, parser):
        self.add_project_argument(parser)
        parser.add_argument("--layers", choices=["all", "top", "bottom"])
        # ...

    def execute(self, args):
        # Plugin implementation
        pass
```

## Migration Path

### Phase 1: Internal Refactoring (No API Changes)
1. Create new directory structure
2. Move command files to `commands/builtin/`
3. Implement `CommandRegistry` and `discover_commands()`
4. Update `main.py` to use registry
5. **No changes to command implementations needed**

### Phase 2: Add Plugin Support
1. Implement `plugin_loader.py` with entry point support
2. Add plugin documentation
3. Create example third-party plugin

### Phase 3: Enhanced Features (Optional)
1. Command versioning and compatibility checks
2. Command dependencies (e.g., `gerber` depends on `bom`)
3. Plugin configuration via `pyproject.toml` or `.jbom/plugins.yaml`
4. Plugin lifecycle hooks (e.g., `on_load`, `on_unload`)

## Benefits

### For Core Development
- **Reduced Main Complexity**: No hardcoded command imports
- **Better Testing**: Commands can be tested in complete isolation
- **Cleaner Structure**: Related code grouped together
- **Easier Maintenance**: Add/remove commands without touching main

### For Users
- **Extensibility**: Users can create custom commands for their workflow
- **Discoverability**: `jbom --help` shows all available commands, including plugins
- **No Core Modifications**: Custom commands don't require forking jBOM

### For Third-Party Developers
- **Standard Interface**: Well-defined API via `Command` base class
- **Easy Distribution**: Package as standard Python package with entry points
- **Version Safety**: Minimum version checks prevent breakage

## Example Use Cases

### Custom Workflow Command
```python
# User creates ~/.local/share/jbom/plugins/internal.py

class InternalWorkflowCommand(Command):
    """Generate files for internal approval process"""
    metadata = CommandMetadata(
        name="internal-review",
        category="custom",
    )

    def execute(self, args):
        # Generate BOM, POS, and PDF schematic in one command
        # Upload to internal review system
        pass
```

### Analysis Command
```python
class CostAnalysisCommand(Command):
    """Analyze BOM costs across multiple suppliers"""
    metadata = CommandMetadata(
        name="cost-analysis",
        category="analysis",
        requires_inventory=True,
    )
```

### Integration Command
```python
class JiraIntegrationCommand(Command):
    """Create Jira tickets for missing parts"""
    metadata = CommandMetadata(
        name="jira-parts",
        category="integration",
    )
```

## Backward Compatibility

All existing commands continue to work unchanged:
- Existing API (`generate_bom()`, `generate_pos()`) unaffected
- Command-line interface identical
- No breaking changes to user workflows

## Implementation Estimate

- **Phase 1 (Internal Refactoring)**: 2-3 days
  - Low risk, high value
  - Improves maintainability immediately

- **Phase 2 (Plugin Support)**: 1-2 days
  - Enables third-party extensions
  - Requires documentation

- **Phase 3 (Enhanced Features)**: Ongoing
  - Implement as needed based on user feedback

## Recommendation

**Start with Phase 1** as it provides immediate benefits with minimal risk:
1. Cleaner codebase
2. Better command organization
3. No user-facing changes
4. Foundation for future plugin support

Once Phase 1 is stable, add Phase 2 to enable the ecosystem to grow.
