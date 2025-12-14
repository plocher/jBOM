# Changelog

All notable changes to jBOM are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-12-14

### Added
- Pre-commit hook configuration for automated secret detection and code quality
- Comprehensive pre-commit hooks guide: `PRE_COMMIT_SETUP.md`
- Quick reference guide for pre-commit operations: `PRE_COMMIT_QUICK_REFERENCE.md`
- Security incident report documentation: `SECURITY_INCIDENT_REPORT.md`
- GitHub secrets and CI/CD configuration guide: `GITHUB_SECRETS_SETUP.md`

### Changed
- Reorganized documentation for clarity:
  - All user-facing and developer documentation moved to `docs/` folder (included in PyPI)
  - Release management and security documentation moved to `release-management/` folder (excluded from PyPI)
  - `README.man*` files consolidated in `docs/` for consistency
- Simplified MANIFEST.in using `recursive-include docs *` pattern
- Updated cross-references throughout documentation to reflect new structure
- WARP.md now includes updated directory structure

### Improved
- Repository root is now cleaner with only `README.md` at the top level
- Better separation of concerns: user docs vs release/security management
- PyPI package is leaner by excluding release management documentation
- All documentation now properly indexed in `docs/` folder

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

[1.0.2]: https://github.com/SPCoast/jBOM/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/SPCoast/jBOM/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/SPCoast/jBOM/releases/tag/v1.0.0
