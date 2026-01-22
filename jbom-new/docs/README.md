# Documentation

This directory contains project-wide documentation that doesn't belong to specific code modules.

## Architecture Documentation

### Design Principles
The jBOM architecture follows these key principles established during the Service/Workflow/Command decomposition:

1. **Service-Command Pattern**: Services contain business logic, CLI provides thin command wrappers
2. **Pure Functions**: Services are stateful classes, Common contains stateless utilities
3. **Single Responsibility**: Each service has one clear business purpose
4. **Testability**: Services can be unit tested in isolation, BDD tests validate user workflows

### Service vs Common Axiom
**Key Decision Rule**: Use `__init__` method presence as the differentiator:

- **Services** (in `src/services/`): Have state and behavior
  - Contains `__init__` method with instance variables
  - Examples: `BOMGenerator`, `SchematicReader`, `InventoryMatcher`

- **Common** (in `src/common/`): Stateless utilities and data structures
  - Pure functions, data classes, constants
  - No `__init__` methods (except for data classes)
  - Examples: `ComponentData`, file utilities, formatters

## Project Documentation

### [USER_GUIDE.md](USER_GUIDE.md)
Comprehensive user workflows and examples for BOM generation, inventory management, and component placement.

### [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
Architecture, design patterns, and implementation guide for contributors and maintainers.

## Historical Context

This documentation reflects the simplified architecture achieved after migrating from a complex plugin-based system. The previous architecture required:

- Plugin registries and discovery mechanisms
- Complex workflow abstractions
- Multi-layer indirection for simple operations
- Over 7,000 lines of infrastructure code

The current architecture eliminates this complexity while maintaining all functionality and enabling future GUI/Web/KiCad plugin interfaces.

## Development Documentation Structure

Documentation is distributed throughout the codebase following these patterns:

### Module-Level Documentation
Each significant directory contains a `README.md` with:
- **Purpose**: What this module does
- **Architecture**: How it fits in the overall system
- **Patterns**: Common patterns and conventions
- **Usage**: How to work with the module
- **Examples**: Real code references (not duplicated code)

### API Documentation
Services and functions include docstrings following Python conventions:
```python
def process_components(self, components: List[ComponentData]) -> BOMData:
    """Process components into BOM data structure.

    Args:
        components: List of component data from schematic

    Returns:
        Structured BOM data ready for output formatting

    Raises:
        BOMProcessingError: When component data is invalid
    """
```

### Test Documentation
Tests serve as living documentation:
- **Gherkin tests** document user-facing behavior
- **Unit tests** document service contracts and edge cases

## Documentation Maintenance

### Keeping Documentation Current
- Reference actual code rather than duplicating it
- Update documentation when making architectural changes
- Use examples from the working codebase
- Keep high-level concepts in central docs, implementation details near code

### Documentation Review
When adding features or making changes:
1. Update relevant module README files
2. Add/update docstrings for public APIs
3. Create BDD tests for user-facing changes
4. Update CHANGELOG.md for significant changes

## Future Evolution

As jBOM grows, maintain these documentation principles:
- **Discoverability**: New developers can understand the system quickly
- **Maintainability**: Documentation stays in sync with code
- **Completeness**: All architectural decisions are captured
- **Usability**: Examples and patterns are easy to follow

The Service-Command architecture provides a stable foundation that can support additional interfaces (GUI, Web, KiCad plugins) without requiring architectural changes or documentation restructuring.
