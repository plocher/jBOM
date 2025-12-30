# BDD Axioms and Patterns for jBOM

This document captures the established axioms and patterns that MUST be consistently applied across ALL BDD scenarios in the jBOM project.

## Core Axioms

### 1. Fabricator Configuration Dependencies
**Pattern**: Configuration dependencies belong in the ASSERTION, not the scenario description.

**✅ Correct Pattern** (from fabricator_formats.feature):
```gherkin
Then the BOM generates in the requested format with columns matching the [FABRICATOR] fabricator configuration
```

**✅ Apply to back_annotation**:
```gherkin
Then component R1 has LCSC property set to "C25804" matching the JLC fabricator configuration
Then component R1 has "Distributor Part Number" property set to "PWR-10K603" matching the PCBWay fabricator configuration
```

**❌ Avoid**: Embedding configuration details in scenario descriptions or Given clauses.

### 2. Concrete Test Vectors Over Abstract Concepts
**Axiom**: All scenarios MUST use specific, measurable test data instead of abstract placeholders.

**✅ Concrete**:
- Priority values: 0, 1, 5, 50, 100, 2147483647, 4294967295
- Specific part numbers: C25804, RC0603FR-0710K
- Real field names: LCSC, MPN, "Distributor Part Number"

**❌ Abstract**:
- "high priority parts"
- "component matches"
- "various values"

### 3. Internal Consistency Rule
**Axiom**: Table headers MUST exactly match assertion field names within each scenario.

**✅ Consistent**:
```gherkin
| LCSC   | MPN        |
| C25804 | RC0603FR-0 |

Then component has LCSC property set to "C25804"
```

**❌ Inconsistent**:
```gherkin
| Current_LCSC | Current_MPN |
| C25804       | RC0603FR-0  |

Then component has LCSC property set to "C25804"
```

### 4. Edge Case Testing Pattern
**Axiom**: Critical algorithms MUST include edge cases in test vectors.

**Priority Edge Cases**:
- Minimum valid: 0
- Common values: 1, 5, 50, 100
- System limits: 2147483647, 4294967295
- Malformed: "high", "", "#DIV/0!"

**UUID Edge Cases**:
- Valid UUIDs
- "invalid-uuid"
- Empty strings ""

### 5. Positive/Negative Test Assertion Pattern
**Axiom**: Scenarios testing selection logic MUST include both positive (what is selected) AND negative (what is excluded) assertions.

**✅ Complete Pattern**:
```gherkin
Then the BOM contains R1 matched to R001 with priority 0
And the BOM excludes R002 and R003 due to higher priority values
```

**❌ Incomplete**:
```gherkin
Then the BOM contains R1 matched to R001
```

### 6. Fixture-Based Approach with Edge Case Visibility
**Axiom**: Reusable test data SHOULD be organized in fixtures/ with clear subdirectories. HOWEVER, inline tables are acceptable when they provide critical visibility to specific edge cases being tested.

**Structure**:
```
features/fixtures/
├── schematics/
├── inventories/
└── pcbs/
```

**Acceptable Inline Table Use Cases**:
- **Edge case visibility**: When the scenario tests specific matching logic (e.g., 1.1K precision resistor matching 1K1 tolerance component)
- **Algorithmic demonstration**: When the table data directly illustrates the algorithm being tested
- **Priority edge cases**: When testing boundary conditions (0, max values, malformed data)
- **Field comparison**: When contrasting fabricator-specific field mappings

**Use Fixtures When**:
- Standard component sets ("BasicComponents", "ComponentProperties")
- Reusable inventory sets ("JLC_Basic", "LocalStock")
- Common test scenarios across multiple features

### 7. File Format vs Data Logic Separation
**Axiom**: BDD scenarios test file format SUPPORT at workflow level, leaving parsing specifics to unit tests.

**BDD Level**: "Excel inventory file", "Numbers inventory file"
**Unit Test Level**: Specific Excel parsing errors, cell format validation

### 8. Algorithmic Behavior Over Hardcoded Assumptions
**Axiom**: Scenarios MUST specify the algorithm, not hardcode specific outcomes.

**✅ Algorithmic**:
```gherkin
Then the BOM selects parts with lowest priority value regardless of actual numbers
```

**❌ Hardcoded**:
```gherkin
Then the BOM selects parts with priority 1 over parts with priority 2 and 3
```

### 9. Fabricator Filtering Logic
**Axiom**: Multi-source inventory filtering is based on Distributor column VALUES, not filenames.

**Correct Logic**:
- `--jlc` filters to parts where `Distributor == "JLC"`
- All inventory files are processed
- Non-matching distributor parts are filtered out (not ignored)

### 10. Dependency Visibility Principle
**Axiom**: All external dependencies MUST be explicit in the scenario.

**Hidden Dependencies** (❌):
- Implicit configuration files
- Assumed field mappings
- Unstated fabricator policies

**Explicit Dependencies** (✅):
- "with JLC fabricator configuration"
- "matching the PCBWay fabricator configuration"
- Visible test data in scenario tables

### 11. Explicit Field Specification for BOM Testing
**Axiom**: BOM scenarios MUST explicitly specify which fields are expected in the output to ensure assertions can be validated.

**Preferred Pattern - Use Fabricator Configurations**:
```gherkin
When I generate a BOM with --generic fabricator
Then the BOM contains R1 matched to R001 with priority 0
```

**Alternative Pattern - Explicit Fields** (use sparingly):
```gherkin
When I generate a BOM with fields "Value,Package,Priority"
Then the BOM excludes R002 due to higher priority
```

**Rationale**:
- **DRY Principle**: Leverage existing fabricator configurations instead of repeating field lists
- **Generic Configuration**: Use `--generic` with standard fields (Reference, Quantity, Description, Value, Package, Footprint, Manufacturer, Part Number)
- **Fabricator-Specific**: Use `--jlc`, `--pcbway`, etc. for fabricator-specific field sets
- **Custom Fields**: Only specify explicit fields when testing edge cases requiring specific field combinations

**Examples**:
```gherkin
# Standard testing - use fabricator configs
When I generate a BOM with --generic fabricator

# Priority testing - generic includes all needed fields
When I generate a JLC BOM with --jlc fabricator

# Edge case - only when specific field combination needed
When I generate a BOM with fields "Reference,Priority" for priority-only validation
```

### 12. Multi-Modal Testing Coverage
**Axiom**: All core functionality MUST be tested across three execution contexts: CLI, API, and Embedded-KiCad.

**Three Execution Contexts**:
1. **CLI**: Command-line interface (`jbom bom --jlc`)
2. **API**: Python API (`BackAnnotationAPI.update()`)
3. **Embedded-KiCad**: Plugin/integration within KiCad environment

**Automatic Multi-Modal Pattern** (Domain-Specific Steps):
```gherkin
Scenario: Back-annotation with JLC parts
  Given the "BasicComponents" schematic
  And the "JLC_Basic" inventory
  When I run back-annotation with --jlc fabricator
  Then component R1 has LCSC property set to "C25804"
```

**Step Definition Implementation**:
```python
@then('component R1 has LCSC property set to "{value}"')
def step_component_has_property(context, value):
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")
    # Then verify the specific behavior across CLI, API, Embedded-KiCad
```

**❌ ANTI-PATTERNS - Do NOT specify execution context in scenarios**:
```gherkin
# WRONG - Violates Axiom #12
Scenario: Generate BOM via API
  When I use the API to generate BOM...

Scenario: Search enhancement via CLI
  When I use the CLI to search...

Scenario: Back-annotation through plugin
  When I use the KiCad plugin to annotate...
```

**✅ CORRECT PATTERNS - Let domain-specific steps handle multi-modal testing**:
```gherkin
# CORRECT - Tests all execution contexts automatically
Scenario: Generate BOM with fabricator configuration
  When I generate BOM with --jlc fabricator...

Scenario: Search enhancement with caching
  When I generate search-enhanced inventory...

Scenario: Back-annotation with part updates
  When I run back-annotation with --jlc fabricator...
```

**Benefits**:
- **Automatic**: No need for Scenario Outlines or manual repetition
- **DRY**: Single scenario tests all three execution paths
- **Transparent**: Step definitions handle multi-modal execution invisibly
- **Complete Coverage**: Every assertion automatically validates all usage models

### 13. Generic Configuration as BDD Testing Foundation
**Axiom**: BDD tests SHOULD depend on and use the `--generic` fabricator configuration as the primary testing foundation. The generic configuration CAN and SHOULD be updated as necessary to support axiom-adherent features and scenarios.

**Principle**: The generic configuration serves as the **stable testing contract** between BDD scenarios and jBOM functionality.

**Guidelines**:
- **Primary Testing**: Use `--generic` for standard BDD testing unless fabricator-specific behavior is being tested
- **Configuration Evolution**: Update `generic.fab.yaml` when BDD scenarios require new fields or capabilities
- **Backward Compatibility**: Changes to generic config should be additive (new fields) rather than breaking (removing fields)
- **Documentation**: Generic config changes should be documented and justified in commit messages

**Rationale**:
- **Single Source of Truth**: Eliminates field list duplication across scenarios
- **Maintainable**: Changes to field requirements only need updates in one place
- **Extensible**: New testing needs can be supported by enhancing the generic configuration
- **Realistic**: Tests use actual jBOM configuration system rather than synthetic field lists

**Examples**:
```yaml
# generic.fab.yaml evolution for BDD support
bom_columns:
  "Reference": "reference"     # Core field
  "Value": "value"           # Component matching
  "Package": "package"       # Added for BDD edge case testing
  "Priority": "priority"     # Could be added for priority testing
```

**Anti-Pattern**: Creating synthetic field combinations that don't reflect real jBOM usage

**Three Execution Contexts**:
1. **CLI**: Command-line interface (`jbom bom --jlc`)
2. **API**: Python API (`BackAnnotationAPI.update()`)
3. **Embedded-KiCad**: Plugin/integration within KiCad environment

**Automatic Multi-Modal Pattern** (Domain-Specific Steps):
```gherkin
Scenario: Back-annotation with JLC parts
  Given the "BasicComponents" schematic
  And the "JLC_Basic" inventory
  When I run back-annotation with --jlc fabricator
  Then component R1 has LCSC property set to "C25804"
```

**Step Definition Implementation**:
```python
@then('component R1 has LCSC property set to "{value}"')
def step_component_has_property(context, value):
    # Auto-execute multi-modal validation
    context.execute_steps("When I validate behavior across all usage models")
    # Then verify the specific behavior across CLI, API, Embedded-KiCad
```

**Benefits**:
- **Automatic**: No need for Scenario Outlines or manual repetition
- **DRY**: Single scenario tests all three execution paths
- **Transparent**: Step definitions handle multi-modal execution invisibly
- **Complete Coverage**: Every assertion automatically validates all usage models

## Application Checklist

When reviewing/creating BDD scenarios, verify:

- [ ] Fabricator dependencies in assertions (Axiom #1)
- [ ] Concrete test vectors, no abstractions (Axiom #2)
- [ ] Internal consistency between tables and assertions (Axiom #3)
- [ ] Edge cases included for critical algorithms (Axiom #4)
- [ ] Both positive AND negative test assertions (Axiom #5)
- [ ] Fixtures OR edge case visibility inline tables (Axiom #6)
- [ ] File format testing at workflow level (Axiom #7)
- [ ] Algorithmic behavior specified (Axiom #8)
- [ ] Distributor filtering logic correct (Axiom #9)
- [ ] All dependencies visible (Axiom #10)
- [ ] Explicit field specification for BOM output (Axiom #11)
- [ ] Multi-modal coverage: NO explicit "via API", "via CLI", "through plugin" in scenarios (Axiom #12)
- [ ] Generic configuration as primary testing foundation (Axiom #13)

## Files Requiring Review

Apply these axioms to all remaining BDD feature files:
- `features/bom/*.feature` (remaining files)
- `features/annotate/*.feature` (remaining scenarios in back_annotation.feature)
- `features/pos/*.feature`
- Any other feature files

## Status

**Foundation Established**: All 13 core BDD axioms defined and documented

**BOM Features**: Fully compliant with all axioms
- component_matching.feature, fabricator_formats.feature, multi_source_inventory.feature, priority_selection.feature
- All leverage --generic or appropriate fabricator configurations
- DRY violations eliminated through generic.fab.yaml enhancement

**Back-Annotation Features**: Transformed to use fixture-based, domain-specific step approach
- back_annotation.feature fully refactored with automatic multi-modal testing

**Generic Configuration**: Enhanced to support BDD testing requirements
- Added Package field to generic.fab.yaml
- Established as stable testing foundation per Axiom #13

**Next**: Apply axioms to remaining feature areas (pos/, search/, inventory/, error_handling/)
