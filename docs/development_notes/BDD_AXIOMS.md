# BDD Axioms and Patterns for jBOM

This document captures the established axioms and patterns that MUST be consistently applied across ALL BDD scenarios in the jBOM project.

## Axiom Organization

The 24 axioms are organized by priority:
- **Foundational Axioms (1-7)**: Essential principles for all scenarios
- **Quality Axioms (8-13)**: Ensuring robustness and reliability
- **Advanced Patterns (14-20)**: Optimizing maintainability and reusability
- **Precision Patterns (21-24)**: Eliminating ambiguity and value judgments

---

## Foundational Axioms (1-7)
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
And the BOM excludes R002 and R003
```

### Axiom #7: Gherkin Colon Consistency ⭐ NEW
**Principle**: Step definitions MUST consistently follow Gherkin colon conventions for table/docstring data.

**Standard Gherkin Convention**:
- **Steps with table/docstring data → USE colon (`:`)**
- **Simple statement steps → NO colon**

**✅ Correct Usage**:
```gherkin
Given the "TestBoard" schematic contains components:
  | Reference | Value | Footprint   |
  | R1        | 10K   | R_0603_1608 |
And a KiCad project named "ComponentTest"
```

**❌ Inconsistent Usage**:
```gherkin
Given a schematic with components
  | Reference | Value | Footprint   |
  | R1        | 10K   | R_0603_1608 |
# Missing colon before table data

Given a KiCad project named "ComponentTest":
# Unnecessary colon for simple statement
```

**Benefits**:
- ✅ Eliminates undefined step errors due to pattern mismatches
- ✅ Improves code readability and consistency
- ✅ Follows standard Gherkin/Cucumber conventions
- ✅ Prevents maintenance issues from mixed patterns

---

## Quality Axioms (8-13)
*Ensuring robustness and reliability*

### Axiom #8: Edge Case Coverage
**Principle**: Critical algorithms MUST include boundary conditions and edge cases.

**Examples**: Priority values (0, 1, 2147483647), Invalid data ("high", "", "#DIV/0!"), System limits

### Axiom #9: Configuration Dependencies in Assertions
**Principle**: Configuration dependencies belong in the ASSERTION, not the scenario description.

**✅ Correct**:
```gherkin
Then component R1 has LCSC property set to "C25804" matching the JLC fabricator configuration
```

### Axiom #10: Algorithmic Behavior Over Hardcoded Assumptions
**Principle**: Scenarios MUST specify the algorithm, not hardcode specific outcomes.

**✅ Algorithmic**: "the BOM selects parts with lowest priority value"
**❌ Hardcoded**: "the BOM selects parts with priority 1 over priority 2"

### Axiom #11: Fabricator Filtering Logic
**Principle**: Multi-source inventory filtering is based on Distributor column VALUES, not filenames.

### Axiom #12: Generic Configuration as Testing Foundation
**Principle**: Use `--generic` fabricator configuration as the primary BDD testing foundation.

### Axiom #13: File Format vs Data Logic Separation
**Principle**: BDD scenarios test file format SUPPORT at workflow level, leaving parsing specifics to unit tests.

---

## Advanced Patterns (14-20)
*Optimizing maintainability and reusability*

### Axiom #14: Step Definition Organization
**Principle**: Step definitions MUST be organized logically by domain, kept reusable, and separate business logic from implementation details.

**Structure**:
```
features/steps/
├── bom/shared.py          # BOM domain steps
├── inventory/shared.py    # Inventory domain steps
├── pos/shared.py          # POS domain steps
└── shared.py              # Cross-domain shared steps
```

### Axiom #15: Step Parameterization
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

### Axiom #16: Fixture-Based Approach with Edge Case Visibility
**Principle**: Use fixtures for common test data, BUT allow inline tables when they provide critical visibility to edge cases being tested.

**Use Fixtures**: Standard component sets, reusable inventory
**Use Inline Tables**: Edge case visibility, algorithmic demonstrations

### Axiom #17: Explicit Field Specification
**Principle**: BOM scenarios MUST explicitly specify which fields are expected in output.

**Preferred**: Use fabricator configurations (`--generic`, `--jlc`)
**Alternative**: Explicit fields only for edge cases

### Axiom #18: Complete Precondition Specification ⭐ NEW
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

### Axiom #19: Dynamic Test Data Builder Pattern ⭐ NEW
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

### Axiom #20: The "Because" Test ⭐ EDITORIAL
**Principle**: Any urge to write "THEN ... BECAUSE..." indicates incomplete GIVEN or vague WHEN statements.

Gherkin's Then step should describe the outcome or result of the action in the When step, verifying a measurable change in the system's state. It should not include a justification, as the Then is purely about observation and validation.
The best practices for writing effective Then steps emphasize clarity, focus, and conciseness:
-  Focus on the Outcome: The primary role of the Then step is to confirm the expected outcome. It answers the question, "What changed as a result of the 'When' action?".
- Avoid Implementation Details: The steps should be written in a business-readable language that describes what the system does, not how it does it.
- Be Specific and Measurable: Instead of "Then the user should be happy," use "Then a confirmation email is sent to the user" or "Then the item is added to the shopping cart".
- Use Declarative Language: The Then step declares the expected state of the system.
Including a justification within the Then step can muddle its purpose. The justification for a specific behavior should be captured in the overarching Feature description or the Scenario title, which provide the business context for why a particular behavior is desired. The Given-When-Then structure is designed to separate context, action, and result for maximum readability and maintainability.

**The Because Test**: When you feel compelled to justify an outcome, check:
1. **GIVEN incomplete?** - Are all preconditions that make the outcome inevitable explicitly stated?
2. **WHEN vague?** - Does the action clearly specify what behavior is being triggered?
3. **THEN over-explaining?** - Is the assertion trying to justify instead of just stating the outcome?

**✅ Properly Structured**:
```gherkin
Given a schematic with R1 (10K, 0603)
And inventory contains R001 (10K, 0603, priority=0) and R002 (10K, 0603, priority=1)
When I generate a BOM with priority-based selection
Then the BOM contains R1 matched to R001
And the BOM excludes R002
```

**❌ "Because" Code Smell**:
```gherkin
Given a schematic with R1 (10K, 0603)
# Missing: what's available in inventory? What selection algorithm?
When I generate a BOM
# Vague: what type of BOM generation?
Then the BOM contains R1 matched to R001
And the BOM excludes R002 due to higher priority values
# Over-explaining: why justify the exclusion?
```

**Application**: If you need "because", "due to", or "based on" in THEN, improve GIVEN and WHEN instead.

---

## Precision Patterns (21-24)
*Eliminating ambiguity and value judgments discovered during Error Handling domain implementation*

### Axiom #21: Named References Over Implicit Context
**Principle**: Use explicit named references for test artifacts to eliminate ambiguity about which inputs are being used.

**✅ Explicit Named References**:
```gherkin
Given a KiCad project named "SimpleProject"
And an inventory named "InvalidInventory"
And the inventory contains:
  | InvalidColumn | AnotherBadColumn |
  | data1         | data2            |
When I generate a generic BOM with SimpleProject and InvalidInventory
```

**❌ Implicit Context** (Violates Axiom #17):
```gherkin
Given a KiCad project named "SimpleProject"
And an inventory file with invalid format
When I generate a BOM with --generic fabricator
# Which project? Which inventory? Ambiguous!
```

**Benefits**:
- ✅ No ambiguity about inputs
- ✅ Explicit binding between Given and When steps
- ✅ Supports multiple projects/inventories in complex scenarios
- ✅ Makes test maintenance easier

### Axiom #22: Descriptive Content Over Value Judgments
**Principle**: Describe what data contains rather than labeling it as "valid" or "invalid" - avoid value judgments in test specifications.

**✅ Descriptive Content**:
```gherkin
And an inventory file contains:
  | InvalidColumn | AnotherBadColumn |
  | data1         | data2            |
```

**❌ Value Judgments**:
```gherkin
And an inventory file with invalid format
# "Invalid" according to whom? For what purpose?
```

**Key Insight**: There's no universal "valid format" - validity depends on context and use case. What's "invalid" for one fabricator might be perfectly valid for another.

**Benefits**:
- ✅ Eliminates assumptions about correctness
- ✅ Focuses on concrete data rather than judgments
- ✅ More maintainable when requirements change
- ✅ Reduces cognitive bias in test design

### Axiom #23: Complete Expected Output Specification
**Principle**: When testing data transformation, specify the complete expected output structure, including empty fields, to validate graceful handling of missing data.

**✅ Complete Output Specification**:
```gherkin
Then the BOM contains:
  | Reference | Quantity | Description | Value | Package | Footprint | Manufacturer | Part Number |
  | R1        | 1        |             | 10k   |         |           |              |             |
  | C1        | 1        |             | 100nF |         |           |              |             |
```

### Axiom #24: KiCad Project/Schematic Architecture Distinction ⭐ NEW
**Principle**: Respect the actual KiCad architecture where projects contain schematics, not components. Use proper project/schematic separation in test specifications.

**✅ Correct KiCad Architecture**:
```gherkin
Given a KiCad project named "PowerSupply"
And the project uses a schematic named "MainBoard"
And the "MainBoard" schematic contains components:
  | Reference | Value | Footprint   | LibID |
  | R1        | 10K   | R_0603_1608 | Device:R |
```

**❌ Incorrect Architecture**:
```gherkin
Given a KiCad project named "PowerSupply" containing components:
  | Reference | Value | Footprint   | LibID |
  | R1        | 10K   | R_0603_1608 | Device:R |
# Projects don't contain components - schematics do!
```

**Actual File Structure**:
```
some_directory/
└── PowerSupply/
    ├── PowerSupply.kicad_pro     # Project file
    ├── PowerSupply.kicad_pcb     # PCB layout (optional)
    └── MainBoard.kicad_sch       # Schematic file
```

**Hierarchical Project Benefits**:
```gherkin
Given a KiCad project named "ComplexBoard"
And the project uses a schematic named "MainBoard"
And the project uses a schematic named "PowerSupply"
And the project uses a schematic named "AnalogSection"
And the "MainBoard" schematic contains components:
  | Reference | Value | Footprint |
  | U1        | MCU   | QFP64     |
And the "PowerSupply" schematic contains components:
  | Reference | Value | Footprint |
  | U2        | VREG  | SOT23     |
And the "AnalogSection" schematic contains components:
  | Reference | Value | Footprint |
  | U3        | OPAMP | SOIC8     |
When I generate a generic BOM for ComplexBoard using inventory.csv
Then the BOM file contains components from all schematic files
And component quantities are correctly aggregated across all schematics
```

**Key Benefits**:
- ✅ Accurate representation of KiCad architecture
- ✅ Enables testing hierarchical designs with explicit component placement
- ✅ Supports multiple schematics per project testing
- ✅ Allows testing edge cases like missing sub-schematics
- ✅ Reflects real-world KiCad project organization

**❌ Partial Output Specification**:
```gherkin
Then the BOM contains components from the schematic:
  | Reference | Quantity | Value |
  | R1        | 1        | 10k   |
  | C1        | 1        | 100nF |
# What about the other fields? Are they empty? Default values?
```

**Benefits**:
- ✅ Tests graceful degradation behavior
- ✅ Validates complete output structure
- ✅ Makes empty field handling explicit
- ✅ Documents expected behavior for missing data
- ✅ Matches fabricator configuration exactly

**Application Example**:
When inventory lacks required columns, the BOM should still be generated with:
- ✅ Data from schematic (Reference, Value)
- ✅ Calculated fields (Quantity)
- ✅ Empty cells for unavailable data (Manufacturer, Part Number)
- ✅ All expected columns present (per fabricator config)

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
- [ ] Consistent colon usage for table/docstring data (Axiom #7)

### Quality (Essential for robustness):
- [ ] Edge cases covered (Axiom #8)
- [ ] Configuration dependencies in assertions (Axiom #9)
- [ ] Algorithmic behavior specified (Axiom #10)
- [ ] Correct fabricator filtering logic (Axiom #11)
- [ ] Uses generic configuration foundation (Axiom #12)
- [ ] File format testing at workflow level (Axiom #13)

### Advanced (Optimizing maintainability):
- [ ] Steps organized by domain (Axiom #14)
- [ ] Steps properly parameterized (Axiom #15)
- [ ] Fixtures used appropriately (Axiom #16)
- [ ] Explicit field specification (Axiom #17)
- [ ] Complete preconditions specified (Axiom #18)
- [ ] Dynamic test data builder used (Axiom #19)
- [ ] No "because" justifications in THEN statements (Axiom #20)

### Precision (Eliminating ambiguity):
- [ ] Named references used over implicit context (Axiom #21)
- [ ] Descriptive content over value judgments (Axiom #22)
- [ ] Complete expected output specification (Axiom #23)
- [ ] Correct KiCad project/schematic architecture (Axiom #24)

---

## Implementation Status

### Completed Domains:
✅ **Back-annotation**: Complete (0 undefined steps)
✅ **BOM**: Complete (0 undefined steps)
✅ **Inventory**: Complete (0 undefined steps)

### Remaining Work:
✅ **Error Handling**: Infrastructure complete, behavior review needed (10 discrepancies documented)
🚧 **POS Component Placement**: ~40 step definitions needed
🚧 **Search**: Integrated with inventory domain

### Architecture Established:
- Automatic multi-modal testing across CLI, API, Plugin
- Advanced parameterization with `{fabricator:w}` patterns
- Domain-specific organization following Axiom #13
- AmbiguousStep conflict resolution
- Dynamic test data builder pattern (Axiom #18)
- Named reference system (Axiom #20)
- Concrete test vector implementation (Axiom #2, #21, #22)
- Behavior vs infrastructure separation methodology

### Key Discoveries:
- **Precision Patterns (Axioms 20-22)**: Eliminate ambiguity and value judgments
- **Behavior Discovery Process**: Systematic identification of expected vs actual behavior
- **Multi-Modal Success Criteria**: Different success indicators for CLI/API/Plugin
- **Graceful Degradation vs Fail Fast**: Design philosophy implications for user experience

**Definition of Done**: Solid foundation of TDD and BDD development patterns achieved for 4 of 6 major jBOM domains, with proven architecture and enhanced axioms for remaining domains.
