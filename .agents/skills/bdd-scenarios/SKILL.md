---
name: bdd-scenarios
description: Use when writing or reviewing behave/Gherkin scenarios for jBOM — covering the review checklist, colon-consistency rule, step parameterization patterns, annotated examples, and the dynamic test-data builder pattern that must be applied to every scenario in the jBOM BDD suite.
---

# bdd-scenarios

Actionable guidance for writing and reviewing jBOM behave scenarios.
Apply the [24 BDD axioms](../../../docs-new/design/bdd-axioms.md) consistently
across the suite.  This skill covers: how to run the suite, how to apply each
tier of axioms, what anti-patterns look like next to correct alternatives, and
the mechanical review checklist to run before committing any scenario.

---

## Running the suite

```bash
# Full suite (required before any PR merge)
python -m behave --format progress

# By tag during development
python -m behave --tags @regression

# Single feature file
python -m behave features/bom/bom_generation.feature
```

Always run the full suite before opening or merging a PR.  Merges are blocked
when any scenario is failed, errored, or undefined.

---

## Colon-consistency rule (Axiom #7)

Gherkin requires a colon at the end of a step that introduces a table or
docstring block, and forbids it on standalone statements.  behave's step-pattern
matching is sensitive to this: a missing or extra colon causes an "undefined
step" error even when the matching function exists.

**Correct:**

```gherkin
Given the "TestBoard" schematic contains components:
  | Reference | Value | Footprint   |
  | R1        | 10K   | R_0603_1608 |
And a KiCad project named "ComponentTest"
```

**Incorrect — missing colon before table:**

```gherkin
Given a schematic with components
  | Reference | Value | Footprint   |
  | R1        | 10K   | R_0603_1608 |
```

**Incorrect — unnecessary colon on standalone statement:**

```gherkin
Given a KiCad project named "ComponentTest":
```

Apply this rule to every Given, When, and Then step.  When adding a new step
that takes a table, ensure the step-definition regex ends with `:?` or `:` as
appropriate, and update all callers to be consistent.

---

## Step parameterization (Axiom #15)

Step definitions must accept parameters rather than hardcoding values.

**Parameterized (correct):**

```python
@when('I generate a BOM with --{fabricator:w} fabricator')
def step_generate_bom_with_fabricator(context, fabricator):
    # Works with --generic, --jlc, --pcbway, etc.
    ...
```

**Hardcoded (wrong):**

```python
@when('I generate a BOM with JLC fabricator')
def step_generate_bom_jlc_only(context):
    # Cannot be reused for any other fabricator
    ...
```

Use behave's built-in type converters (`{name:w}`, `{value:d}`, `{value:f}`)
to capture typed parameters.  Prefer generic steps that the caller specializes
via the scenario text rather than one step per concrete value.

---

## Multi-modal testing (Axiom #4) [STATUS: needs verification]

The design intent is that a single step definition for core behavior should
exercise CLI, API, and Plugin execution paths automatically, so one scenario
covers all three rather than three near-identical scenarios.

As of the #247 audit the current step library invokes jBOM exclusively via the
CLI (`python -m jbom.cli.main` in `common_steps.py`).  No API-mode or Plugin
invocation was found in `features/steps/`.  Before promoting a scenario as
"multi-modal verified", confirm that the underlying step actually exercises all
three paths.  If it does not, either extend the step implementation or note the
gap in the scenario with a `@wip` tag.

The anti-pattern to avoid is writing three separate scenarios:

```gherkin
# Wrong — DRY violation
Scenario: Generate BOM via API
Scenario: Generate BOM via CLI
Scenario: Generate BOM via Plugin
```

The goal is one scenario backed by a step implementation that dispatches to all
three execution contexts.

---

## Concrete test vectors (Axiom #2)

Every scenario must use literal, measurable values:

- **Priority:** `0`, `1`, `5`, `50`, `100`, `2147483647`
- **Part numbers:** `C25804`, `RC0603FR-0710K`
- **Quantities:** specific integers
- **Tolerance values:** `1%`, `5%`, `10%`

Prohibited abstractions: "high priority parts", "component matches",
"various values", "some inventory items".

---

## Explicit preconditions and dynamic test data (Axioms #18, #19)

Every condition that makes the scenario's outcome inevitable must appear in
Given steps.  Negative conditions — what is absent from the inventory — must be
stated explicitly.  Use the three-tier builder pattern to balance completeness
with DRY:

**Tier 1 — Background (feature-wide foundation):**

```gherkin
Background: Base Test Data Foundation
  Given a clean test environment
  And a base inventory with standard components:
    | IPN   | Category | Value | Package |
    | R001  | RES      | 10K   | 0603    |
    | R002  | RES      | 1K1   | 0603    |
```

**Tier 2 — Dynamic extensions (scenario-specific):**

```gherkin
Given the schematic is extended with component:
  | Reference | Value | Package |
  | R1        | 1K    | 0603    |
And the inventory excludes exact match for "1K 0603 resistor"
```

**Tier 3 — Named fixtures (complex scenarios):**

```gherkin
Given the "HierarchicalDesign" schematic
And the "MultiSupplierInventory" inventory
```

---

## Positive and negative assertions (Axiom #6)

A scenario that tests selection logic must assert both what is selected and what
is excluded.

**Complete (correct):**

```gherkin
Then the BOM contains R1 matched to R001 with priority 0
And the BOM excludes R002 and R003
```

**Incomplete (wrong):**

```gherkin
Then the BOM contains R1 matched to R001
# Does not prove R002 and R003 were rejected
```

---

## The "Because" test (Axiom #20)

Any impulse to write "THEN … because …", "THEN … due to …", or "THEN … based
on …" signals an incomplete Given or a vague When.

**Properly structured:**

```gherkin
Given a schematic with R1 (10K, 0603)
And inventory contains R001 (10K, 0603, priority=0) and R002 (10K, 0603, priority=1)
When I generate a BOM with priority-based selection
Then the BOM contains R1 matched to R001
And the BOM excludes R002
```

**"Because" code smell (wrong):**

```gherkin
Given a schematic with R1 (10K, 0603)
# Missing: inventory contents and selection algorithm
When I generate a BOM
Then the BOM contains R1 matched to R001
And the BOM excludes R002 due to higher priority values
```

Check: Does the Then need to explain itself?  If yes, add the missing context to
Given or sharpen the When.

---

## Named references over implicit context (Axiom #21)

When a scenario involves more than one project, schematic, or inventory, bind
each artifact to an explicit name and use that name in the When step.

**Explicit (correct):**

```gherkin
Given a KiCad project named "SimpleProject"
And an inventory named "InvalidInventory"
And the inventory contains:
  | InvalidColumn | AnotherBadColumn |
  | data1         | data2            |
When I generate a generic BOM with SimpleProject and InvalidInventory
```

**Implicit (wrong):**

```gherkin
Given a KiCad project named "SimpleProject"
And an inventory file with invalid format
When I generate a BOM with --generic fabricator
# Which project? Which inventory?
```

---

## KiCad project/schematic architecture (Axiom #24)

KiCad projects contain schematics; schematics contain components.  Steps must
reflect this hierarchy.

**Correct hierarchy:**

```gherkin
Given a KiCad project named "PowerSupply"
And the project uses a schematic named "MainBoard"
And the "MainBoard" schematic contains components:
  | Reference | Value | Footprint   | LibID    |
  | R1        | 10K   | R_0603_1608 | Device:R |
```

**Wrong — components placed directly in project:**

```gherkin
Given a KiCad project named "PowerSupply" containing components:
  | Reference | Value | Footprint   | LibID    |
  | R1        | 10K   | R_0603_1608 | Device:R |
# Projects don't contain components — schematics do.
```

For hierarchical designs, list every sub-schematic explicitly:

```gherkin
Given a KiCad project named "ComplexBoard"
And the project uses a schematic named "MainBoard"
And the project uses a schematic named "PowerSupply"
And the "MainBoard" schematic contains components:
  | Reference | Value | Footprint |
  | U1        | MCU   | QFP64     |
And the "PowerSupply" schematic contains components:
  | Reference | Value | Footprint |
  | U2        | VREG  | SOT23     |
When I generate a generic BOM for ComplexBoard using inventory.csv
Then the BOM file contains components from all schematic files
And component quantities are correctly aggregated across all schematics
```

---

## Descriptive content over value judgments (Axiom #22)

Do not label test data "valid" or "invalid".  Describe what it contains.

**Descriptive (correct):**

```gherkin
And an inventory file contains:
  | InvalidColumn | AnotherBadColumn |
  | data1         | data2            |
```

**Value judgment (wrong):**

```gherkin
And an inventory file with invalid format
# "Invalid" according to whom?  For what fabricator?
```

---

## Complete output specification (Axiom #23)

When testing data transformation, include every expected output column in the
Then table — including columns expected to be empty.

**Complete (correct):**

```gherkin
Then the BOM contains:
  | Reference | Quantity | Description | Value | Package | Footprint | Manufacturer | Part Number |
  | R1        | 1        |             | 10k   |         |           |              |             |
  | C1        | 1        |             | 100nF |         |           |              |             |
```

**Partial (wrong):**

```gherkin
Then the BOM contains components from the schematic:
  | Reference | Quantity | Value |
  | R1        | 1        | 10k   |
  | C1        | 1        | 100nF |
# What about the other columns?  Are they empty?  Default values?
```

---

## Review checklist

Run this checklist on every scenario before committing.

### Foundational (required for ALL scenarios)

- [ ] Describes behavior, not implementation (Axiom #1)
- [ ] Uses concrete test vectors — no abstract placeholders (Axiom #2)
- [ ] All dependencies explicit in Given steps (Axiom #3)
- [ ] Multi-modal testing confirmed or gap documented (Axiom #4)
- [ ] Table headers match assertion field names (Axiom #5)
- [ ] Includes positive AND negative assertions where applicable (Axiom #6)
- [ ] Consistent colon usage: colon before tables/docstrings, none on statements (Axiom #7)

### Quality (essential for robustness)

- [ ] Edge cases covered for critical algorithms (Axiom #8)
- [ ] Configuration dependencies stated in assertions (Axiom #9)
- [ ] Algorithmic behavior specified, not hardcoded outcomes (Axiom #10)
- [ ] Fabricator filtering uses Distributor column values, not filenames (Axiom #11)
- [ ] Uses generic configuration as testing foundation (Axiom #12)
- [ ] File-format testing at workflow level; parsing details in unit tests (Axiom #13)

### Advanced (optimizing maintainability)

- [ ] Step definitions organized by domain (Axiom #14)
- [ ] Steps use parameterization, not hardcoded values (Axiom #15)
- [ ] Fixtures for reusable data; inline tables for edge-case visibility (Axiom #16)
- [ ] Explicit output field specification using fabricator configs (Axiom #17)
- [ ] All preconditions stated, including negative ones (Axiom #18)
- [ ] Three-tier test data builder pattern applied (Axiom #19)
- [ ] No "because", "due to", or "based on" in Then steps (Axiom #20)

### Precision (eliminating ambiguity)

- [ ] Named references used for all artifacts (Axiom #21)
- [ ] Descriptive content used instead of value-judgment labels (Axiom #22)
- [ ] Complete output specification including empty fields (Axiom #23)
- [ ] Correct KiCad project→schematic→component hierarchy (Axiom #24)
