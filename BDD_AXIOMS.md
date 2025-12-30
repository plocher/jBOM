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

### 6. Fixture-Based Approach
**Axiom**: Reusable test data SHOULD be organized in fixtures/ with clear subdirectories.

**Structure**:
```
features/fixtures/
├── schematics/
├── inventories/
└── pcbs/
```

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

### 11. Multi-Modal Testing Coverage
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
- [ ] Reusable data organized in fixtures (Axiom #6)
- [ ] File format testing at workflow level (Axiom #7)
- [ ] Algorithmic behavior specified (Axiom #8)
- [ ] Distributor filtering logic correct (Axiom #9)
- [ ] All dependencies visible (Axiom #10)
- [ ] Multi-modal coverage: CLI, API, Embedded-KiCad (Axiom #11)

## Files Requiring Review

Apply these axioms to all remaining BDD feature files:
- `features/bom/*.feature` (remaining files)
- `features/annotate/*.feature` (remaining scenarios in back_annotation.feature)
- `features/pos/*.feature`
- Any other feature files

## Status

**Completed**: multi_source_inventory.feature, component_matching.feature, priority_selection.feature, fabricator_formats.feature, partial back_annotation.feature

**Next**: Complete back_annotation.feature alignment, then systematic review of all remaining scenarios.
