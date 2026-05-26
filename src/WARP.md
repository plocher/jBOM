# Source Code Guidelines

## Core Application Structure
- `src/jbom/__version__.py` — Version information (auto-updated by semantic-release)
- `src/jbom/cli/` — Command-line adapters (thin wrappers over application/services)
- `src/jbom/application/` — Adapter-neutral workflow orchestration
- `src/jbom/services/` — Business logic
- `src/jbom/common/` — Shared domain types and utilities
- `src/jbom/config/` — Unified profile loading and schema models
- `src/jbom/plugin/` — KiCad plugin integration

Layering and per-layer responsibilities are documented in the ADR
series under `docs/architecture/adr/`. Naming conventions are below.

## Code Organization Rules
- Type hints required on all functions
- Docstrings required for public methods
- Use dataclasses for structured data (`Component`, `InventoryItem`, `BOMEntry`)
- Validation at data intake points
- Single responsibility principle for functions
- Coding practices to adhere to:
    - See release-management/WARP.md
- Agent behavior expectations
    - When uncertain about alternate paths or solutions, ask for guidance

## Design Documentation Expectations
- Significant architectural decisions are recorded in
  `docs/architecture/adr/` as numbered ADRs.
- Mutable design rationale (how the architecture is currently
  instantiated) lives in `docs/design/`. See the documentation
  charter at `docs/README.md` for the architecture-vs-design
  content boundary.
- After implementing a feature that introduces or changes an
  architectural pattern, update the relevant `docs/` content — not
  just code comments or the GitHub issue.
- The `src/WARP.md` file records agent-behavior directions and
  source-code conventions; `docs/` is for human-readable design and
  architecture content.

## Naming Convention (established in issues #224/#237)
- Class names reflect the **promise** (what the class produces/delivers), not the mechanism.
- The `Service` suffix is omitted when the module path already provides context (`jbom.application.*`, `jbom.services.*`).
- `Orchestration` is omitted from names — it describes *how*, not *what*.
- Examples: `BOMWorkflow`, `POSWorkflow`, `FabricationWorkflow`, `GerberExporter`.
- Application workflow classes expose a single public method named `.run(request)` — functional, not mechanistic.
- Private helpers use descriptive functional names: `_list_fields`, `_generate`, not `_orchestrate_*`.


## See also

- Component-matching behavioral semantics (tolerance substitution,
  priority system, field normalization) are documented in
  `docs/design/inventory-matching-semantics.md` once that doc lands
  in Wave B.
- Extension-point recipes (adding a CLI command, a service, a
  fabricator profile, a supplier provider) live in the
  `extend-jbom` skill at `.agents/skills/extend-jbom/SKILL.md`
  once that skill lands in Wave B.
