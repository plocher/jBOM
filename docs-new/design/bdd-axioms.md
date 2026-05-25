# BDD Axioms — jBOM Test-Suite Invariants

The jBOM BDD suite encodes 24 axioms that every gherkin scenario must honor.
These are design invariants, not style suggestions: violating them produces
scenarios that are ambiguous, fragile, or untestable.  The axioms are organized
into four tiers by scope: foundational principles that apply to every scenario,
quality properties that ensure robustness, advanced structural patterns that
keep the suite maintainable, and precision rules that eliminate ambiguity.

For how to apply these axioms when writing or reviewing scenarios — including
the review checklist and annotated counter-examples — see the
[`bdd-scenarios` skill](../../.agents/skills/bdd-scenarios/SKILL.md).

---

## Foundational Axioms (1–7)

These invariants apply without exception to every scenario in the suite.

**Axiom #1 — Behavior Over Implementation.**
Scenarios must describe business behavior and observable outcomes, never
technical implementation details such as internal method calls, file paths, or
UI widget actions.

**Axiom #2 — Concrete Test Vectors.**
All scenarios must use specific, measurable test data rather than abstract
placeholders.  Priority values, part numbers, and tolerance figures must be
literal.  Phrases like "high priority parts" or "various values" are prohibited.

**Axiom #3 — Explicit Dependencies.**
Every external dependency a scenario relies on — configuration files, fabricator
settings, inventory contents — must be stated explicitly in Given steps.  Hidden
assumptions make scenarios non-reproducible.

**Axiom #4 — Multi-Modal Testing.** [STATUS: needs verification]
Core functionality should be tested across CLI, API, and Plugin execution
contexts rather than writing three separate scenarios for the same behavior.
The intent is that a single well-written step definition exercises all three
execution paths automatically.

*Verification note:* As of the #247 audit, the current step definitions in
`features/steps/` invoke jBOM exclusively via the CLI
(`python -m jbom.cli.main`).  No API-mode or Plugin execution path was found in
the step implementations.  This axiom describes the design goal; whether it is
fully realized in the current step library requires confirmation against the
actual step implementations.  See audit finding in `docs-new/dev/development_notes/247-docs-audit.md`.

**Axiom #5 — Internal Consistency.**
Table column headers in a scenario must exactly match the field names used in
the corresponding assertion steps.  A mismatch causes the step definition to
read from the wrong column and silently pass or fail for the wrong reason.

**Axiom #6 — Positive and Negative Assertions.**
Scenarios that test selection logic must include both what is selected and what
is excluded.  An assertion that only confirms the expected match does not prove
that incorrect candidates were rejected.

**Axiom #7 — Gherkin Colon Consistency.**
Steps that are followed by a table or docstring block must end with a colon
(`:`).  Steps that are standalone statements must not carry a trailing colon.
This is the standard Gherkin convention enforced by behave's step-pattern
matching; inconsistency causes undefined step errors.

---

## Quality Axioms (8–13)

These invariants ensure the suite catches real defects rather than exercising
only the happy path.

**Axiom #8 — Edge Case Coverage.**
Critical algorithms require boundary-condition scenarios: the minimum and maximum
representable priority values, invalid or malformed input (empty strings, Excel
error cells, non-numeric text where a number is expected), and system limits.

**Axiom #9 — Configuration Dependencies in Assertions.**
When an assertion's expected value depends on a fabricator or supplier
configuration, that dependency belongs in the Then step's phrasing, not in the
scenario title.  Embedding configuration context in the assertion makes the
dependency explicit and the scenario self-documenting.

**Axiom #10 — Algorithmic Behavior Over Hardcoded Outcomes.**
Scenarios must specify the algorithm or selection rule rather than hardcoding a
particular outcome that is only correct because of today's data.  An assertion
that "the BOM selects parts with the lowest priority value" survives data
changes; one that "the BOM selects priority 1 over priority 2" does not.

**Axiom #11 — Fabricator Filtering Logic.**
Multi-source inventory filtering is governed by the value of the `Distributor`
column in the inventory, not by the inventory filename.  Scenarios that test
fabricator-specific filtering must reflect this column-value model.

**Axiom #12 — Generic Configuration as Testing Foundation.**
The `--generic` fabricator configuration is the primary foundation for BDD
testing.  Fabricator-specific scenarios extend from this baseline rather than
duplicating a full setup.

**Axiom #13 — File Format vs. Data Logic Separation.**
BDD scenarios test file-format support at the workflow level: does jBOM accept
CSV, XLSX, and Numbers inventory files and produce correct output?  Parsing
specifics — field extraction, encoding handling, dialect variations — belong in
unit tests, not gherkin scenarios.

---

## Advanced Patterns (14–20)

These invariants govern the structure and organization of the step library and
the scenarios that consume it.

**Axiom #14 — Step Definition Organization.**
Step definitions must be organized by business domain rather than by scenario
file.  Shared steps live in domain-specific modules (`bom/shared.py`,
`inventory/shared.py`, `pos/shared.py`) with cross-domain steps in a common
module.  This prevents the name-collision and load-order problems that arise
when unrelated steps accumulate in a single file.

**Axiom #15 — Step Parameterization.**
Step definitions must use behave's parse-expression parameterization to
eliminate hardcoded values.  A step that accepts `--{fabricator:w} fabricator`
works for any fabricator name; one that names a fabricator literally is a
one-off that cannot be reused.

**Axiom #16 — Fixture-Based Approach with Edge-Case Visibility.**
Standard, reusable test data belongs in shared fixtures loaded from Background
sections.  Inline tables are appropriate when the specific data values are the
point of the scenario — that is, when the reader needs to see the exact boundary
condition or algorithmic input to understand why the outcome is expected.

**Axiom #17 — Explicit Field Specification.**
BOM scenarios must state which output fields are expected, using fabricator
configurations (`--generic`, `--jlc`) as the authoritative field source.
Leaving the expected field set implicit makes a scenario incapable of detecting
field-name changes or missing columns.

**Axiom #18 — Complete Precondition Specification.**
Every precondition that makes the scenario's outcome inevitable must appear in
Given steps.  Negative preconditions — what is not in the inventory, which
configuration is absent — must be stated explicitly.  A scenario whose outcome
depends on implicit system state is non-reproducible.

**Axiom #19 — Dynamic Test Data Builder Pattern.**
Explicit preconditions (Axiom #18) and the DRY principle are reconciled through
a three-tier strategy: a Background section establishes a feature-wide base
fixture; scenario-specific Given steps extend or constrain that base; named
fixtures handle complex multi-component setups.  This avoids both
copy-paste repetition and hidden state.

**Axiom #20 — The "Because" Test.**
When writing a Then step, any impulse to include the word "because", "due to",
or "based on" is a signal that the Given or When is incomplete.  The Then step
declares an observable outcome; justification belongs in the scenario's Given
steps or title, not in the assertion itself.

---

## Precision Patterns (21–24)

These invariants eliminate the ambiguity that surfaces when scenarios involve
multiple named artifacts or test data that could be interpreted several ways.

**Axiom #21 — Named References Over Implicit Context.**
When a scenario involves multiple projects, schematics, or inventory files, each
must be bound to a name in Given steps and that name must appear explicitly in
the When step.  Relying on "the current project" or "the inventory" is ambiguous
when more than one such artifact exists.

**Axiom #22 — Descriptive Content Over Value Judgments.**
Test specifications must describe what data contains rather than labeling it
"valid" or "invalid".  Validity is context-dependent: what is invalid for one
fabricator's required columns may be perfectly acceptable input for another.
Concrete descriptions survive requirement changes; value labels do not.

**Axiom #23 — Complete Expected Output Specification.**
When testing data transformation, the expected output table must include every
column, including columns expected to be empty.  Omitting a column from the
expected table makes the scenario unable to detect missing-column failures or
incorrect empty-field handling.

**Axiom #24 — KiCad Project/Schematic Architecture Distinction.**
jBOM follows KiCad's actual data model: a *project* contains one or more
*schematics*, and schematics contain *components*.  Scenarios must reflect this
hierarchy.  A step that places components directly inside a project name
misrepresents the data model and cannot correctly express hierarchical
multi-schematic designs.
