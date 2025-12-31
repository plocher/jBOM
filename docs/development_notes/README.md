# Development Notes

This directory contains internal development notes, TODOs, and design documents that are used during jBOM development but are not part of the main user documentation.

## Contents

### BDD and Testing Infrastructure
- **BDD_AXIOMS.md** - Comprehensive BDD axioms and best practices for test development
- **BEHAVE_SUBDIRECTORY_LOADING.md** - Technical solution for behave step definition loading from subdirectories
- **BDD Step Loading Pattern** - Systematic approach for organizing behave step definitions in subdirectories without import conflicts

### Development TODOs and Planning
- **development_tasks.md** - Master task list and BDD implementation roadmap (was TODO)

### Requirements Documentation

#### Completed Requirements (`completed/`)
- **inventory_management_requirements.md** - Inventory system requirements (✅ Completed - Steps 1-3.5)
- **federated_inventory_requirements.md** - Multi-source inventory support (✅ Completed)

#### Active Requirements (`active/`)
- **back_annotation_requirements.md** - Back-annotation to KiCad schematics (Step 4)
- **fabrication_platform_requirements.md** - Complete fabrication automation platform
- **fabricator_integration_requirements.md** - Multi-fabricator support (Step 6)
- **component_rotation_correction_requirements.md** - Pick-and-place rotation corrections per fabricator
- **comprehensive_fault_testing_requirements.md** - Edge case and fault tolerance testing strategy

### Testing and Validation
- **sample_detailed_validation_report.txt** - Sample validation report format
- **PROJECT_INPUT_RESOLUTION_TESTS.feature** - Development test scenarios for project input resolution

## Organization

These files are organized here to keep the project root directory clean while maintaining easy access for developers. Most of these documents are working notes and planning materials that support the development process but are not needed by end users.

### Structure
- **`completed/`** - Historical requirements documents for features that have been fully implemented
- **`active/`** - Current requirements and planning documents for features under development
- **Root level** - Development infrastructure, TODOs, and cross-cutting concerns

## BDD Step Loading Design Pattern

### Overview

jBOM uses a systematic approach to organize behave step definitions in domain-specific subdirectories while avoiding import conflicts. This pattern was developed to solve step loading issues and maintain clean organization.

### Pattern Implementation

**Directory Structure:**
```
features/
├── steps/
│   ├── __init__.py         # Empty - lets behave discover subdirectories
│   ├── shared.py          # Cross-domain shared steps
│   ├── annotate/
│   │   ├── __init__.py    # Domain package initialization
│   │   └── back_annotation.py
│   ├── bom/
│   │   ├── __init__.py    # Domain package initialization
│   │   ├── component_matching.py
│   │   ├── fabricator_formats.py
│   │   └── shared.py      # Domain-specific shared steps
│   └── [other domains...]
```

**Key Principles:**
1. **Empty main `__init__.py`** - Avoids import conflicts with behave's execution model
2. **Natural discovery** - Behave automatically finds `.py` files in subdirectories with `__init__.py`
3. **Domain separation** - Each domain (bom, pos, inventory, etc.) has its own subdirectory
4. **Shared step hierarchy** - Cross-domain steps in root, domain-specific shared steps in subdirectories

### Technical Solution Details

**Problem Solved:** Behave executes step files using `exec()` without providing `__name__` in globals, making relative imports fail with `KeyError: "'__name__' not in globals"`.

**Solution:** Let behave handle step discovery naturally instead of complex import logic.

**Reference:** Based on [QC Analytics systematic approach](https://qc-analytics.com/2019/10/importing-behave-python-steps-from-subdirectories/) adapted for behave's execution constraints.

### Implementation Files

- **`features/steps/STEP_LOADING_SOLUTION.md`** - Complete technical documentation
- **`features/steps/__init__.py`** - Empty file enabling natural discovery
- **Domain `__init__.py` files** - Simple imports for subdirectory step files

### Adding New Step Domains

1. Create subdirectory under `features/steps/`
2. Add empty `__init__.py` file
3. Add step definition `.py` files
4. Use `behave --dry-run` to validate discovery

## Moving Forward

As features are completed, relevant documentation should be moved to the main `docs/` directory or integrated into user-facing documentation as appropriate.
