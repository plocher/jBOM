# BDD Axioms and Patterns for jBOM

This document captures the established axioms and patterns that MUST be consistently applied across ALL BDD scenarios in the jBOM project.

## Axiom Organization

The 18 axioms are organized by priority:
- **Foundational Axioms (1-6)**: Essential principles for all scenarios
- **Quality Axioms (7-12)**: Ensuring robustness and reliability
- **Advanced Patterns (13-18)**: Optimizing maintainability and reusability

---

## Foundational Axioms (1-6)
*Essential principles that must be applied to ALL scenarios*

### Axiom #1: Behavior Over Implementation
**Principle**: BDD scenarios must describe business behavior and outcomes, not technical implementation details.

**✅ Behavior-Focused**:
```gherkin
When I generate a BOM with --jlc fabricator
Then the BOM contains components with JLC-specific fields
```

**❌ Implementation-Focused**:
```gherkin
When I click the "Generate BOM" button and parse CSV output
Then a file is written to /tmp/output.csv
```

### Axiom #2: Concrete Test Vectors
**Principle**: All scenarios MUST use specific, measurable test data instead of abstract placeholders.

**✅ Concrete**: Priority values: 0, 1, 5, 50, 100, 2147483647; Part numbers: C25804, RC0603FR-0710K
**❌ Abstract**: "high priority parts", "component matches", "various values"

### Axiom #3: Explicit Dependencies
**Principle**: All external dependencies MUST be explicit in the scenario - no hidden assumptions.

**✅ Explicit**: "with JLC fabricator configuration", visible test data in tables
**❌ Hidden**: Implicit configuration files, assumed field mappings

### Axiom #4: Multi-Modal Testing
**Principle**: All core functionality MUST be tested across CLI, API, and Plugin execution contexts automatically.

**✅ Automatic Multi-Modal**:
```gherkin
When I generate a BOM with --jlc fabricator
# Tests CLI, API, and Plugin automatically in step definition
```

**❌ Explicit Context** (Violates DRY):
```gherkin
Scenario: Generate BOM via API
Scenario: Generate BOM via CLI
Scenario: Generate BOM via Plugin
```

### Axiom #5: Internal Consistency
**Principle**: Table headers MUST exactly match assertion field names within each scenario.

**✅ Consistent**:
```gherkin
| LCSC   | MPN        |
| C25804 | RC0603FR-0 |

Then component has LCSC property set to "C25804"
```

### Axiom #6: Positive and Negative Assertions
**Principle**: Scenarios testing selection logic MUST include both what IS selected AND what is EXCLUDED.

**✅ Complete**:
```gherkin
Then the BOM contains R1 matched to R001 with priority 0
And the BOM excludes R002 and R003 due to higher priority values
```

---

## Quality Axioms (7-12)
*Ensuring robustness and reliability*

### Axiom #7: Edge Case Coverage
**Principle**: Critical algorithms MUST include boundary conditions and edge cases.

**Examples**: Priority values (0, 1, 2147483647), Invalid data ("high", "", "#DIV/0!"), System limits

### Axiom #8: Configuration Dependencies in Assertions
**Principle**: Configuration dependencies belong in the ASSERTION, not the scenario description.

**✅ Correct**:
```gherkin
Then component R1 has LCSC property set to "C25804" matching the JLC fabricator configuration
```

### Axiom #9: Algorithmic Behavior Over Hardcoded Assumptions
**Principle**: Scenarios MUST specify the algorithm, not hardcode specific outcomes.

**✅ Algorithmic**: "the BOM selects parts with lowest priority value"
**❌ Hardcoded**: "the BOM selects parts with priority 1 over priority 2"

### Axiom #10: Fabricator Filtering Logic
**Principle**: Multi-source inventory filtering is based on Distributor column VALUES, not filenames.

### Axiom #11: Generic Configuration as Testing Foundation
**Principle**: Use `--generic` fabricator configuration as the primary BDD testing foundation.

### Axiom #12: File Format vs Data Logic Separation
**Principle**: BDD scenarios test file format SUPPORT at workflow level, leaving parsing specifics to unit tests.

---

## Advanced Patterns (13-18)
*Optimizing maintainability and reusability*

### Axiom #13: Step Definition Organization
**Principle**: Step definitions MUST be organized logically by domain, kept reusable, and separate business logic from implementation details.

**Structure**:
```
features/steps/
├── bom/shared.py          # BOM domain steps
├── inventory/shared.py    # Inventory domain steps
├── pos/shared.py          # POS domain steps
└── shared.py              # Cross-domain shared steps
```

### Axiom #14: Step Parameterization
**Principle**: Step definitions MUST use parameterization to eliminate hardcoded values.

**✅ Parameterized**:
```python
@when('I generate a BOM with --{fabricator:w} fabricator')
def step_generate_bom_with_fabricator(context, fabricator):
    # Works with --generic, --jlc, --pcbway, etc.
```

**❌ Hardcoded**:
```python
@when('I generate a BOM with JLC fabricator')
def step_generate_bom_jlc_only(context):
    # Only works for JLC
```

### Axiom #15: Fixture-Based Approach with Edge Case Visibility
**Principle**: Use fixtures for common test data, BUT allow inline tables when they provide critical visibility to edge cases being tested.

**Use Fixtures**: Standard component sets, reusable inventory
**Use Inline Tables**: Edge case visibility, algorithmic demonstrations

### Axiom #16: Explicit Field Specification
**Principle**: BOM scenarios MUST explicitly specify which fields are expected in output.

**Preferred**: Use fabricator configurations (`--generic`, `--jlc`)
**Alternative**: Explicit fields only for edge cases

### Axiom #17: Complete Precondition Specification ⭐ NEW
**Principle**: All test preconditions must be explicitly stated in Given steps with no implicit assumptions about system state.

**✅ Explicit Preconditions**:
```gherkin
Given the schematic contains a 1K 0603 resistor
And the generic inventory contains a 1k1 0603 resistor
And the inventory does not contain a 1k 0603 resistor
When I generate a BOM with --generic fabricator
Then the BOM contains a matched resistor with inventory value "1K1"
```

**❌ Implicit Assumptions**:
```gherkin
Given the schematic contains a 1K 0603 resistor
# Missing: what's available in inventory?
When I generate a BOM with --generic fabricator
Then the BOM contains a matched resistor with inventory value "1K1"
# How do we know 1K1 should be the match?
```

**Key Requirements**:
- Each scenario must be self-contained and reproducible
- Negative preconditions must explicitly state what is missing
- No assumptions about system state
- Test data setup should establish complete context

### Axiom #18: Dynamic Test Data Builder Pattern ⭐ NEW
**Principle**: Balance explicit preconditions (Axiom #17) with DRY principle using Background + dynamic extensions.

**Three-Tier Strategy**:

1. **Background (Feature-wide Foundation)**:
```gherkin
Background: Base Test Data Foundation
  Given a clean test environment
  And a base inventory with standard components:
    | IPN   | Category | Value | Package |
    | R001  | RES      | 10K   | 0603    |
    | R002  | RES      | 1K1   | 0603    |
```

2. **Dynamic Extensions (Scenario-specific)**:
```gherkin
Given the schematic is extended with component:
  | Reference | Value | Package |
  | R1        | 1K    | 0603    |
And the inventory excludes exact match for "1K 0603 resistor"
```

3. **Named Fixtures (Complex scenarios)**:
```gherkin
Given the "HierarchicalDesign" schematic
And the "MultiSupplierInventory" inventory
```

**Benefits**:
- ✅ Maintains explicit preconditions (Axiom #17)
- ✅ Reduces duplication through base data + extensions
- ✅ Enables complex scenarios with manageable syntax
- ✅ Supports both static fixtures and dynamic mocking

---

## Application Checklist

When reviewing/creating BDD scenarios, verify:

### Foundational (Required for ALL scenarios):
- [ ] Describes behavior, not implementation (Axiom #1)
- [ ] Uses concrete test vectors (Axiom #2)
- [ ] All dependencies explicit (Axiom #3)
- [ ] Multi-modal testing automatic (Axiom #4)
- [ ] Table headers match assertions (Axiom #5)
- [ ] Includes positive AND negative assertions (Axiom #6)

### Quality (Essential for robustness):
- [ ] Edge cases covered (Axiom #7)
- [ ] Configuration dependencies in assertions (Axiom #8)
- [ ] Algorithmic behavior specified (Axiom #9)
- [ ] Correct fabricator filtering logic (Axiom #10)
- [ ] Uses generic configuration foundation (Axiom #11)
- [ ] File format testing at workflow level (Axiom #12)

### Advanced (Optimizing maintainability):
- [ ] Steps organized by domain (Axiom #13)
- [ ] Steps properly parameterized (Axiom #14)
- [ ] Fixtures used appropriately (Axiom #15)
- [ ] Explicit field specification (Axiom #16)
- [ ] Complete preconditions specified (Axiom #17)
- [ ] Dynamic test data builder used (Axiom #18)

---

## Implementation Status

### Completed Domains:
✅ **Back-annotation**: Complete (0 undefined steps)
✅ **BOM**: Complete (0 undefined steps)
✅ **Inventory**: Complete (0 undefined steps)

### Remaining Work:
🚧 **Error Handling**: ~27 step definitions needed
🚧 **POS Component Placement**: ~40 step definitions needed
🚧 **Search**: Integrated with inventory domain

### Architecture Established:
- Automatic multi-modal testing across CLI, API, Plugin
- Advanced parameterization with `{fabricator:w}` patterns
- Domain-specific organization following Axiom #13
- AmbiguousStep conflict resolution
- Dynamic test data builder pattern (Axiom #18)

**Definition of Done**: Solid foundation of TDD and BDD development patterns achieved for 3 of 6 major jBOM domains, with proven architecture for remaining domains.
