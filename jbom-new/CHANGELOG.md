# Changelog

All notable changes to jBOM will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Multi-source inventory management**: Support multiple `--inventory` flags with priority-based selection
- **Component matching system**: Sophisticated component identification with scoring algorithm
  - Exact IPN matching (100 points)
  - Type+Value+Package matching (85 points)
  - Type+Value matching (60 points)
  - Configurable property-based matching
- **Inventory filtering**: `--filter-matches` flag to exclude already-matched components
- **File safety features**:
  - Overwrite protection requiring `--force` flag
  - Timestamped automatic backups when overwriting
- **Enhanced BOM command**: Inventory integration with `--inventory` flag
- **UX consistency**: All commands default to human-readable console tables
- **Comprehensive documentation**: USER_GUIDE.md and DEVELOPER_GUIDE.md

### Changed
- **Breaking**: All commands now default to console output instead of requiring `-o` for output
- **Breaking**: File overwrite now requires explicit `--force` flag for safety
- **Enhanced**: BOM generation can now reference multiple inventory sources
- **Enhanced**: Inventory command can filter out matched components for incremental updates

### Developer Changes
- Added `ComponentInventoryMatcher` service with sophisticated matching logic
- Implemented file backup service with timestamped backups
- Applied DRY principles to Gherkin test scenarios with Background patterns
- Added comprehensive test coverage (48+ scenarios across 5 feature files)
- Documented architectural patterns and extension points

## Workflow Examples

### Basic inventory management:
```bash
# Generate project inventory
jbom inventory project.kicad_sch -o components.csv

# Generate BOM with inventory enhancement
jbom bom project.kicad_sch --inventory stock.csv -o enhanced_bom.csv
```

### Multi-source inventory:
```bash
# Use multiple inventory sources (priority fields determine best matches)
jbom bom project.kicad_sch \
  --inventory primary_stock.csv \
  --inventory supplier_catalog.csv \
  -o comprehensive_bom.csv
```

### Incremental updates:
```bash
# Find components NOT in existing inventory
jbom inventory project.kicad_sch \
  --inventory existing.csv \
  --filter-matches \
  -o additions_needed.csv
```

See [USER_GUIDE.md](docs/USER_GUIDE.md) for complete workflow documentation.
