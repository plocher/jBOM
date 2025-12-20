# Source Code Guidelines

## Core Application Structure
- `src/jbom/jbom.py` - Main application (~2700 lines)
- `src/jbom/__version__.py` - Version information (auto-updated by semantic-release)
- `src/jbom/cli/` - Command-line interface modules
- `src/jbom/pcb/` - PCB position file handling

## Architecture Patterns
- **Parsing Phase:** S-expression → `Component` objects
- **Matching Phase:** Components → `InventoryItem` matching with scoring
- **Output Phase:** Generate `BOMEntry` objects → CSV/format output

## Code Organization Rules
- Type hints required on all functions
- Docstrings required for public methods
- Use dataclasses for structured data (`Component`, `InventoryItem`, `BOMEntry`)
- Validation at data intake points
- Single responsibility principle for functions
- Coding practices to adhere to:
    - See release-management/WARP.md
- Agent behavior expectations
    - When uncertain about alternate paths or solutions, ask for guidance


## Component Matching Logic
**Tolerance Substitution:** Tighter tolerances can substitute looser (1% can replace 5%)
**Priority System:** Lower numbers = higher priority (1 = preferred)
**Field Normalization:** Always use `normalize_field_name()` for consistent handling
**Debug Mode:** Use Notes column for detailed matching information

## Key Extension Points
- `ComponentType` enum for new component categories
- `CATEGORY_FIELDS` dict for category-specific field mappings
- `_get_component_type()` for detection logic
- `_match_properties()` for scoring algorithms
