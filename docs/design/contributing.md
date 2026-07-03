# Contributing to jBOM — Contributor Policy

This document captures the code-style philosophy, testing philosophy, and
project-structure orientation that govern contributions to jBOM. It records
design intent: the *why* behind the conventions, not the step-by-step
mechanics of executing them. For the procedural how-to — setting up your
development environment, running the test suite, or building distribution
packages — see the [dev-setup skill](../../.agents/skills/dev-setup/SKILL.md).
For the git workflow (branching, committing, and opening PRs), see the
[git-workflow skill](../../.agents/skills/git-workflow/SKILL.md).

## Code Style Philosophy

jBOM follows PEP 8 with three non-negotiable invariants:

**Type hints are required throughout.** jBOM's domain is rich with ambiguous
field names and format-sensitive values; the type system is a first-class
reader for both humans and static analysis tools. A function without type
annotations is an invitation to misinterpret its contract.

**Docstrings are required for all public methods and classes.** The jBOM
codebase is navigated by contributors who may not have written the code they
are reading, and by agents executing repository tasks. Docstrings are the
primary contract between a service and its callers. The `normalize_field_name`
function is a canonical example of the expected form: it documents accepted
formats, the invariant it enforces, and its edge-case behavior — all without
requiring the reader to trace through the implementation.

**Line length is capped at 100 characters.** This is wider than the PEP 8
default of 79 and narrower than "no limit." The 100-character cap was chosen
to accommodate the domain-specific identifier lengths common in this codebase
(supplier part numbers, fabricator column names, KiCad property paths) without
sacrificing diff readability in standard terminal widths.

Import ordering follows the standard three-group convention: standard library,
then third-party, then local — each group separated by a blank line. This is
enforced mechanically by the pre-commit hook stack, so contributors should not
spend mental effort on it; the hooks will fix violations automatically.

## Testing Philosophy

jBOM practices Test-Driven Development with a two-layer test suite:

**BDD scenarios** in `features/` use Gherkin to describe user-visible behavior.
Each scenario is a contract between the codebase and its users: "given these
inputs, these outputs will appear." BDD scenarios must pass before any PR is
opened — not because the CI pipeline enforces it (though it does), but because
a failing BDD scenario means a broken contract with a user.

**Unit tests** in `tests/` cover key internal abstractions using pytest. They
exist to validate the correctness of the implementation details that BDD
scenarios are too coarse to pin down: value parsing for specific component
classes (resistors, capacitors, inductors), scoring edge cases in the
inventory matching algorithm, field normalization behavior for pathological
input strings, SMD detection heuristics. Unit tests are more tightly coupled
to implementation than BDD scenarios and may need to be updated or deleted
when internal design changes.

The division of labor is deliberate. BDD scenarios are stable across
refactors because they are written at the level of user intent. Unit tests
are fast to run and specific in their failure messages, making them the right
tool for diagnosing regressions. Neither replaces the other; together they
form the validation scaffold that gives the codebase its [layered
architecture](../architecture/) its integrity.

One principle governs when a test is required: if a design decision is worth
making, it is worth testing. There is no separate "test debt" process; tests
accompany the code that needs them, in the same commit, written before or
alongside the implementation. See the [dev-setup
skill](../../.agents/skills/dev-setup/SKILL.md) for the concrete commands used
to run the full suite.

## CI lane model (issue #290)

The repository CI uses a tiered sequence to reduce feedback latency while
preserving pre-merge confidence:

- **Canary (fast):** a small, high-signal pytest + behave slice for rapid PR
  feedback.
- **Fat canary on failure:** runs only when the fast canary fails; executes a
  broader pytest/behave slice with richer timing detail to accelerate root
  cause analysis.
- **Comprehensive lanes:** full pytest compatibility matrix, full behave run,
  and coverage once the canary is green (or on branch pushes).

Local equivalents:

- Fast canary:
  `PYTHONPATH=src python -m pytest tests/unit/test_cli_help.py tests/unit/test_unified_loader.py tests/unit/test_fabricator_config_schema.py tests/unit/test_supplier_config_schema.py -q`
  and
  `PYTHONPATH=src python -m behave --format progress features/cli/basics.feature features/project/file.feature features/bom/core.feature features/pos/core.feature features/inventory/core.feature features/audit/core.feature`
- Comprehensive:
  `PYTHONPATH=src python -m pytest tests/ -v`
  and
  `PYTHONPATH=src python -m behave --format progress features/`

## Project Structure

The codebase is organized around a domain-centric layering that separates
the CLI (a thin presentation layer) from the services (business logic) and
the common domain types (shared vocabulary). This is not an accident of
history; it is a deliberate architectural decision documented in
[ADR 0013](../architecture/adr/0013-domain-centric-design.md).

```
jBOM/
├── src/jbom/
│   ├── application/      # Orchestration and workflow coordination
│   ├── cli/              # CLI commands (thin wrappers over services)
│   ├── common/           # Shared domain types, utilities, constants
│   ├── config/           # Fabricator and supplier configuration
│   ├── plugin/           # KiCad Eeschema plugin integration
│   ├── services/         # Business logic (reader, matcher, generator)
│   └── suppliers/        # Supplier-specific integrations
├── tests/                # pytest unit tests
├── features/             # Behave BDD scenarios (Gherkin)
│   └── steps/            # Step definitions
├── legacy/               # Archived v6 source (read-only reference)
├── pyproject.toml        # Python packaging config
├── kicad_jbom_plugin.py  # KiCad Eeschema integration wrapper
├── README.md             # Quick start
└── CHANGELOG.md          # Generated version history (do not hand-edit)
```

The dependency direction is one-way: `cli/` depends on `services/` and
`common/`; `services/` depends on `common/`; nothing in `services/` or
`common/` imports from `cli/`. Violating this direction creates circular
imports and, more importantly, couples business logic to presentation
concerns in ways that resist testing.

`CHANGELOG.md` at the repo root is fully generated from conventional commit
messages by semantic-release. Hand-edits are rejected by the pre-commit hook
stack. Change history lives in commit messages and PR descriptions; the
changelog is a derived view (see [charter](../README.md#generated-where-it-serves-the-reader-curated-where-comprehension-matters)).

## Core Domain Types and Design Invariants

Three data classes in `common/types.py` form the domain vocabulary that
flows through the entire system:

`Component` represents a schematic component as read from a `.kicad_sch`
file: it has a reference designator, a library identifier, a value, a
footprint, and an open-ended property map. Everything jBOM reads from a
schematic flows through this type.

`InventoryItem` represents an entry in an inventory file (CSV, Excel, or
Numbers). Its primary key is the IPN (internal part number); it carries
category, value, package, and an attribute map that includes supplier
part numbers and URLs. The blank-field semantics — a blank field means
"no constraint," not "zero" — are a domain invariant documented in
[inventory-matching-semantics](inventory-matching-semantics.md).

`BOMEntry` is the output row type: a reference designator, a quantity,
the matched inventory fields, and any reconciliation notes. It is
produced by `BOMGenerator` and consumed by writers.

The services that operate on these types follow a single-responsibility
principle: `SchematicReader` parses; `InventoryReader` loads;
`InventoryMatcher` reconciles; `BOMGenerator` formats. This decomposition
is an axiom — adding business logic to a reader or presentation logic to
a service violates the design and should be contested in review.

The `common/` package also hosts the utility functions that enforce domain
invariants: `normalize_field_name` converts any field name format to
canonical `snake_case`; `get_component_type` classifies a component from
its library identifier and footprint; `field_to_header` converts field
names to `Title Case` for output headers. These functions are the
enforcement points for the normalization rules that allow jBOM to accept
inventory files authored in arbitrary formats.

Matching is implemented in `services/inventory_matcher.py` for standard
category-driven matching and `services/sophisticated_inventory_matcher.py`
for value-parametric and tolerance-aware matching. The scoring logic in
the latter encodes the tolerance substitution rules documented in
[inventory-matching-semantics](inventory-matching-semantics.md).

## Extension Points

The intended extension surface for jBOM contributors is:

- **New component types**: add to `ComponentType` in `common/constants.py`,
  extend `COMPONENT_TYPE_MAPPING` for aliases, and add category-specific
  scoring fields to `CATEGORY_FIELDS`.
- **New spreadsheet formats**: add optional import with try/except in
  `services/inventory_reader.py`, extend the file-extension detection
  logic, and implement a reader returning normalized row dicts.
- **New CLI commands**: create `src/jbom/cli/mycommand.py` with
  `register_command(subparsers)` and `handle_mycommand(args)`, then import
  and register in `src/jbom/cli/main.py`.
- **Matching algorithm changes**: modify `services/inventory_matcher.py`
  or `services/sophisticated_inventory_matcher.py`, and update value
  parsing in `common/value_parsing.py` if new value formats are needed.

Every extension must be accompanied by pytest unit tests and, for
user-visible behavior, BDD scenarios.

## Contributor Agreement

By contributing to jBOM, you agree that your contributions will be
licensed under the MIT license. Contributions of all kinds are
welcome — bug fixes, features, documentation, tests, and feedback. Be
respectful and professional.
