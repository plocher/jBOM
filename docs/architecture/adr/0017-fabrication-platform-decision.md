# ADR 0017: Fabrication Platform Decision (F-008)
Date: 2026-05-26
Status: Accepted
Related: #304, #247 (F-008), ADR 0005, ADR 0006, ADR 0007

## Context
jBOM has accumulated architecture and delivery decisions that move it beyond a
single-output BOM utility toward a coordinated fabrication workflow surface.

That direction is already reflected in accepted ADRs:

- ADR 0005 commits jBOM to evolutionary supersession with an adapter-neutral
  core and peer CLI/plugin adapters.
- ADR 0006 commits to coordinated fabrication outputs and production-folder
  conventions across adapters.
- ADR 0007 commits to plugin distribution and packaging that preserves a shared
  core architecture.

The architecture audit tracked by #247 identified this strategic direction as a
missing formal ADR decision (finding F-008). The decision itself is currently
implicit across changelog and working notes rather than explicitly published as
an architecture commitment.

## Decision drivers
- Clarify long-term architectural intent in one durable location.
- Keep strategic control and roadmap velocity within jBOM governance.
- Avoid splitting architectural investment across parallel tools with
  overlapping responsibility.
- Preserve adapter neutrality while supporting a complete fabrication workflow.
- Record clear success criteria for what "fabrication platform" means in jBOM.

## Options considered
### Option A: Extend or fork `kicad-jlcpcb-tools/FT` as the primary path
Use an external codebase lineage as the architectural host and move jBOM
capabilities into that direction over time.

Result: Rejected.

Reasons:
- Strategic control remains outside jBOM governance.
- Long-term architecture would be shaped by external constraints rather than
  jBOM's existing ADR commitments.
- Risk of re-introducing coupling to one fabricator/tooling posture.

### Option B: Keep jBOM and `kicad-jlcpcb-tools/FT` as long-term peers
Maintain both tools indefinitely, with partial overlap and selective
cross-pollination of ideas.

Result: Rejected.

Reasons:
- Sustains duplicated architecture investment and user-facing ambiguity.
- Increases drift risk between overlapping workflows and policy behavior.
- Defers a clear system-of-record decision for fabrication orchestration.

### Option C: Evolve jBOM into the fabrication platform (selected)
Treat jBOM as the long-term architecture surface for coordinated fabrication
workflows, while harvesting useful patterns from other tools without adopting
them as the host architecture.

Result: Accepted.

Reasons:
- Aligns with ADR 0005's supersession direction and adapter-neutral model.
- Aligns with ADR 0006's coordinated artifact and policy commitments.
- Aligns with ADR 0007's distribution strategy while preserving shared core
  behavior across adapters.
- Keeps governance and architectural continuity in a single repository.

## Decision
jBOM is the architectural system of record for the fabrication-platform
direction.

jBOM will not extend or fork `kicad-jlcpcb-tools/FT` as a long-term architectural
host. External tools may continue to inform patterns, but jBOM remains the
decision and implementation center for this capability area.

In this context, "fabrication platform" means jBOM provides a coordinated
workflow contract that can produce and package fabrication-ready outputs in one
intentional run, with fabricator-specific policy expressed as configuration and
services rather than adapter-local behavior.

### Success criteria for this decision
This architectural direction is considered realized when jBOM sustains all of
the following as first-class capabilities:

- Coordinated fabrication run semantics covering BOM, placement, fabrication
  plot/archive artifacts, and backup packaging as one workflow contract.
- Fabricator-specific output/policy behavior expressed through shared
  architecture surfaces (config + services), not duplicated per adapter.
- Equivalent architecture intent across CLI and plugin adapters through the same
  core orchestration commitments.
- Continued additive evolution via ADRs when strategic direction changes, rather
  than implicit drift in release notes or ad hoc docs.

## Consequences
### Positive
- Removes ambiguity about jBOM's long-term role.
- Consolidates architectural decision-making and implementation ownership.
- Strengthens coherence of existing ADR commitments (0005, 0006, 0007) under a
  single explicit strategic decision.

### Negative
- Increases expectation that jBOM must carry complete fabrication-platform scope
  over time.
- Requires ongoing discipline to keep adapter-specific UX concerns separate from
  architecture-level commitments.

### Neutral
- Does not prescribe concrete class/module names, CLI flag shapes, or exact
  implementation sequencing.
- Does not prevent compatibility or migration utilities where useful; it only
  defines the long-term architectural host decision.
