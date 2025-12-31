# Development Notes

This directory contains internal development notes, TODOs, and design documents that are used during jBOM development but are not part of the main user documentation.

## Contents

### BDD and Testing Infrastructure
- **BDD_AXIOMS.md** - Comprehensive BDD axioms and best practices for test development
- **BEHAVE_SUBDIRECTORY_LOADING.md** - Technical solution for behave step definition loading from subdirectories

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

## Moving Forward

As features are completed, relevant documentation should be moved to the main `docs/` directory or integrated into user-facing documentation as appropriate.
