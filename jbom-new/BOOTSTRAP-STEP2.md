# Bootstrap Progress - Step 2

## Goal
Add first real workflow (POS generation) to prove the plugin system works

## Why POS First?
- Simpler than BOM (no inventory matching)
- Validates plugin architecture
- Proves service + workflow pattern
- Tests file I/O

## Features to Implement

### 1. Define Success Criteria (Gherkin Scenarios)
Review and finalize scenarios in `features/simple_pos.feature`:
- [ ] Scenario: Generate POS from PCB file
- [ ] Scenario: Generate POS to stdout
- [ ] Scenario: Handle missing PCB file

### 2. Create Plugin Structure
Implement `plugins/pos/` with:
- [ ] plugin.json metadata
- [ ] services/ subdirectory with KiCad reader, POS generator, formatter
- [ ] workflows/ subdirectory with generate_pos workflow
- [ ] Unit tests in plugins/pos/tests/
- [ ] Integration with pytest discovery

### 3. Implement Services
- [ ] KiCadReaderService: read PCB files
- [ ] POSGeneratorService: extract placement data
- [ ] OutputFormatterService: format as CSV

### 4. Implement Workflow
- [ ] generate_pos workflow composes services
- [ ] Registered in workflow registry
- [ ] Callable from CLI

### 5. CLI Integration
- [ ] Add `pos` command to CLI
- [ ] Wire workflow to command handler
- [ ] Handle file I/O and error cases

### 6. Test Infrastructure
- [ ] Create step definitions for POS scenarios
- [ ] Update behave to discover plugin tests
- [ ] Configure pytest for plugin unit tests
- [ ] Verify all tests pass

## Success Criteria
- [ ] `jbom pos <project>` generates placement file
- [ ] Plugin structure: services/ and workflows/ subdirectories
- [ ] Service registry populated at startup
- [ ] Workflow can call services
- [ ] Output written to file or console
- [ ] All Gherkin scenarios pass
- [ ] Plugin unit tests pass with pytest

## Plugin Structure with Tests
```
src/jbom/plugins/
└── pos/
    ├── __init__.py
    ├── plugin.json              # Metadata
    ├── services/
    │   ├── __init__.py
    │   ├── kicad_reader.py      # Read PCB files
    │   ├── pos_generator.py     # Generate placement data
    │   └── output_formatter.py  # Format as CSV
    ├── workflows/
    │   ├── __init__.py
    │   └── generate_pos.py      # Compose services into workflow
    ├── features/                # Plugin BDD tests
    │   └── pos_generation.feature
    └── tests/                   # Plugin unit tests
        ├── __init__.py
        ├── test_kicad_reader.py
        ├── test_pos_generator.py
        └── test_output_formatter.py
```

## Test Discovery Configuration

### Behave (Functional Tests)
Plugin features use core step definitions:
- Core tests: `jbom-new/features/` directory
- Plugin tests: `jbom-new/src/jbom/plugins/*/features/` directories
- Step definitions: `jbom-new/features/steps/` (shared by all)
- Subdirectory loading: See `docs/development_notes/BEHAVE_SUBDIRECTORY_LOADING.md`
- Run from jbom-new/: `behave` (all) or `behave src/jbom/plugins/pos/features/` (specific plugin)

### Pytest (Unit Tests)
Need to configure in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = [
    "jbom-new/tests",           # Core unit tests
    "jbom-new/src/jbom/plugins",  # Plugin unit tests
]
pythonpath = ["jbom-new/src"]
```

Run with:
- `pytest jbom-new/` - all tests
- `pytest jbom-new/src/jbom/plugins/pos/tests/` - just POS plugin

## Service API Pattern
Services provide methods that workflows compose:
```python
class KiCadReaderService:
    def read_pcb(self, pcb_file: Path) -> PCBData: ...

class POSGeneratorService:
    def generate_pos(self, pcb_data: PCBData) -> POSData: ...

class OutputFormatterService:
    def format_csv(self, pos_data: POSData) -> str: ...
```

## Not in Step 2
- BOM generation (Step 3)
- Configuration system (Step 3)
- Multiple output formats (Step 3)
- Inventory integration (Step 3+)
