# Testing Architecture and Axioms

This document defines how we design and write tests across jBOM. It is a contract for future contributors and a checklist for reviews.

## Core Axioms
- User-facing outcomes over narration: Prefer asserting produced artifacts (tables/files/content, exit codes) instead of explanatory strings.
- Layered vocabulary: Keep a small, generic step API for most features, and feature-scoped micro steps for edge-case completeness. Do not force features to import each other’s step vocabularies.
- DRY via Background: Put minimal, stable setup in Background; keep scenario steps focused on the specific user interaction being exercised.
- Sandboxed execution: Every scenario runs in a per-scenario temp directory; tests must never write into the repo working tree.
- Safe by default: Steps must validate all write destinations are under the sandbox; fixture sources come from repo, never modified by tests.

## Step Vocabulary

### Generic layer (shared; for most features)
- `Given a KiCad project named "<Project>"`
- `Given a schematic with components:`
- `And an inventory with parts:`
- `When I run jbom command "<args>"`
- `Then the command should succeed|fail`
- `And the output contains "<text>"` (only when asserting table content/value)

Behavior:
- Creates `<Project>.kicad_pro`, default root schematic `<Project>` (schema file name is implicit), optional PCB if the feature needs it.
- Names of directories/files are incidental; assertions focus on content and exit codes.

### Micro layer (feature-scoped; explicit edge cases)
Only in the feature that owns the semantics (e.g., project resolution, POS units/origin, inventory source selection). Examples:
- Project resolution:
  - `Given a directory "<dir>"`
  - `And a project named "<project>"`
  - `And the project uses a root schematic "<root>" that contains:`
  - Optional hierarchy only when needed:
    - `And the root references child schematic "<child>"`
    - `And the child schematic "<child>" contains:`

Notes:
- Do not require file extensions in steps (e.g., no `.kicad_sch` in Gherkin). Step implementations resolve concrete filenames.
- Introduce hierarchy steps only when the scenario exercises hierarchy-specific behavior.

## Assertions
- Prefer verifying the produced content (rows/fields/counts) and exit codes.
- Only assert names (project/root) if the UI explicitly surfaces them and the scenario is about that.
- Error/reporting: assert non-zero exit codes and, where it serves a user need, assert a small number of actionable messages in feature-specific scenarios.
- Help/usage wording: favor unit tests for exact strings; keep BDD checks minimal or skip entirely if not user-critical.

## Safety and Hygiene
- All steps write inside the per-scenario sandbox; refuse to write elsewhere.
- Fixture copying reads from repo (jbom-new/features/fixtures) and writes into the sandbox; never deletes/modifies repo fixtures.
- Pre-commit and CI must fail if tests mutate the repo worktree.

## Formatting and Names
- Gherkin steps should express intent, not implementation details. Avoid embedding file extensions or paths unless the scenario is specifically about paths.
- Keep Background minimal; avoid re-stating project resolution rules in non-project features.

## Migration Guidance
- New scenarios: use the generic layer by default; add micro steps only within the feature that owns the semantics.
- Existing scenarios that assert verbose discovery lines should be migrated to assert artifacts (content, files) unless the message is the feature under test.
- Legacy fixtures may remain for convenience; avoid name-dependent fixtures for edge-case combinatorics—prefer explicit construction steps.
