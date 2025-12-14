# Changelog

All notable changes to jBOM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-12-14

### Added
- Case-insensitive field name handling throughout the system
- `normalize_field_name()` function for canonical snake_case normalization
- `field_to_header()` function for human-readable Title Case output
- Man page documentation files:
  - `README.man1.md` - CLI reference with options, fields, examples, troubleshooting
  - `README.man3.md` - Python library API reference for programmatic use
  - `README.man4.md` - KiCad Eeschema plugin setup and integration guide
  - `README.man5.md` - Inventory file format specification with field definitions
- `README.tests.md` - Comprehensive test suite documentation
- `SEE ALSO` sections with markdown links in all README files
- Python packaging infrastructure:
  - Modern `pyproject.toml` with comprehensive metadata
  - `setup.py` for legacy compatibility
  - `MANIFEST.in` for non-Python files
  - `src/jbom/` package structure following Python best practices
  - Console script entry point for `jbom` command

### Changed
- Enhanced tolerance substitution scoring:
  - Exact tolerance matches always preferred
  - Next-tighter tolerances preferred over tightest available
  - Scoring penalty for over-specification (gap > 1% gets reduced bonus)
- Updated all field processing to use normalized snake_case internally
- CSV output headers now in human-readable Title Case
- Test suite expanded from 46 to 98 tests across 27 test classes
- Project naming standardized to "jBOM" throughout documentation
- Version number updated to 1.0.1 in all files

### Fixed
- Field name matching now handles all formats: snake_case, Title Case, CamelCase, UPPERCASE, spaces, hyphens
- Tolerance substitution now correctly implements preference ordering
- I:/C: prefix disambiguation system fully functional

### Removed
- Redundant Usage Documentation section from README.md
- Duplicate information consolidated into SEE ALSO sections

## [1.0.0] - 2025-12-13

### Added
- Initial stable release of jBOM
- KiCad schematic parsing via S-expression format
- Hierarchical schematic support for multi-sheet designs
- Intelligent component matching using category, package, and numeric value matching
- Multiple inventory formats: CSV, Excel (.xlsx/.xls), Apple Numbers (.numbers)
- Advanced matching algorithms:
  - Type-specific value parsing (resistors, capacitors, inductors)
  - Tolerance-aware substitution
  - Priority-based ranking
  - EIA-style value formatting
- Debug mode with detailed matching information
- SMD filtering capability for Surface Mount Device selection
- Custom field system with I:/C: prefix disambiguation
- Comprehensive test suite (46 tests across 14 test classes)
- Multiple integration options:
  - KiCad Eeschema plugin via `kicad_jbom_plugin.py`
  - Command-line interface with comprehensive options
  - Python library for programmatic use
- Extensive documentation:
  - `README.md` - User-facing overview and quick start
  - `README.developer.md` - Technical architecture and extension points
  - Full docstrings and inline comments throughout

[1.0.1]: https://github.com/SPCoast/jBOM/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/SPCoast/jBOM/releases/tag/v1.0.0
