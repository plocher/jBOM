# ADR 0005: jBOM Evolutionary Supersession Path — Adapter-Neutral Core, Shared Session/Job Model, Dual Adapters (CLI + KiCad Plugin)
Date: 2026-05-06
Status: Accepted
Related: #220, #221, #222, #223, #224, #225, #226, #227, #228
## Context
Two tools currently occupy adjacent problem space:
- Fabrication Toolkit (FT): strong KiCad ActionPlugin integration and one-stop fabrication artifact flow, but tightly coupled to JLC-specific assumptions and project-field conventions.
- jBOM: service-oriented architecture with broad BOM/POS/inventory/search capabilities and fabricator flexibility, but currently centered on CLI orchestration and without full FT-equivalent fabrication artifact flow.

Strategic constraints and goals for this decision:
- FT governance is external and motivation for deep co-evolution is uncertain.
- jBOM governance is fully controllable.
- jBOM can be treated as pre-release for migration-risk purposes.
- Desired end-state is "best of both": plugin-integrated user experience plus adapter-neutral service architecture and multi-fabricator policy support.

## Decision drivers
- Keep architectural control within jBOM governance.
- Preserve and strengthen jBOM's service-first domain investment.
- Avoid duplicating fabrication engines that already exist in KiCad runtime/tooling.
- Restore "thin adapter" contract by moving orchestration policy out of CLI command handlers.
- Support both CLI and KiCad plugin from one execution model.
- Avoid importing FT's JLC-specific policy coupling into jBOM domain/core.

## Options considered
### Option A: Integrate jBOM into FT (FT-centric convergence)
Treat FT as the host architecture and embed jBOM capabilities into FT.

Result: Rejected.

Reasons:
- Depends on external governance and roadmap alignment.
- Pulls strategic center toward a scope-complete project not optimized for multi-fabricator and inventory-service expansion.
- High risk of reintroducing fabricator coupling patterns that conflict with jBOM goals.

### Option B: Integrate FT into jBOM by direct code transplant
Move FT implementation modules into jBOM and adapt around them.

Result: Rejected as a primary method; retained only as pattern-harvest reference.

Reasons:
- Direct transplant carries runtime/UI and policy coupling not aligned with jBOM service boundaries.
- Better approach is capability re-expression behind jBOM contracts, reusing KiCad APIs and proven process patterns instead of code-level merge.

### Option C: Build a new greenfield superseding tool
Create a third codebase that supersedes both FT and jBOM.

Result: Rejected.

Reasons:
- Duplicates domain logic already represented in jBOM services.
- Increases migration and maintenance surface without adding strategic control benefits beyond jBOM-only evolution.
- Delays value by restarting fundamentals already solved in jBOM.

### Option D: Co-evolve FT and jBOM in a long-running dual-track
Incrementally evolve both projects toward convergence.

Result: Rejected.

Reasons:
- Operationally equivalent to Option A risk profile because FT governance remains an external dependency.
- Adds coordination overhead and architecture drift risk.

### Option E: jBOM-only evolutionary supersession (selected)
Evolve jBOM into the long-term "best of both" architecture:
- extract adapter-neutral orchestration from CLI,
- introduce shared session/job execution model,
- add missing fabrication capabilities as services,
- implement KiCad plugin and CLI as peer adapters over the same core.

Result: Accepted.

## Decision
Adopt Option E: jBOM-only evolutionary supersession with adapter-neutral core and dual adapters.

This decision includes five architectural commitments:
1. Thin adapter contract restoration:
   - CLI is an adapter only (argument parsing, rendering, process exit semantics).
   - KiCad plugin is an adapter only (session acquisition, UI/progress display, user interaction).
2. Shared session/job execution model:
   - common request/context contract,
   - structured progress + diagnostics stream,
   - cancellation + completion semantics,
   - deterministic artifact result contract.
3. Service-level fabrication expansion:
   - gerber/drill/netlist generation expressed as jBOM services that delegate generation to KiCad capabilities (no custom CAM reimplementation).
4. Policy isolation:
   - correction and mapping mechanisms (rotation/offset/transforms, overrides) become explicit policy services/configuration, not adapter-specific behavior.
5. Output and persistence normalization:
   - project option persistence and packaging/archive conventions defined at service boundary and shared across adapters.

## Why this is the right path
- Aligns with governance reality: no external dependency for architectural progress.
- Preserves jBOM strengths: service APIs, testability, multi-fabricator posture.
- Captures FT strengths as reusable patterns (workflow, UX, correction mechanics) without inheriting FT's project-policy coupling.
- Produces a plugin-first UX outcome without sacrificing CLI or automation workflows.

## Architecture shape (target)
### Core layers
- Domain services: BOM/POS/inventory/matching/fabricator policy plus fabrication-artifact services.
- Application/orchestration services: use-case/job execution, sequencing, diagnostics/progress emission, artifact collation.
- Adapters:
  - CLI adapter
  - KiCad ActionPlugin adapter

### Session/job contract (shared)
- JobRequest: intent + options + project reference/session source.
- JobContext: resolved project/session + runtime capabilities.
- JobEvent stream: progress, diagnostics, warnings, actionable errors.
- JobResult: generated artifacts, metadata, and outcome status.

### Adapter responsibilities
- CLI adapter:
  - parse CLI arguments,
  - map to JobRequest,
  - render JobEvents to terminal,
  - map JobResult to exit code and outputs.
- KiCad plugin adapter:
  - acquire active project/session context,
  - map UI settings to JobRequest,
  - render JobEvents in non-blocking UI,
  - support cancellation and completion UX.

## Non-goals
- No dependence on FT repository changes.
- No direct copy/paste integration of FT internals as architecture.
- No elimination of CLI support.
- No custom reimplementation of Gerber/Drill/IPC generation logic where KiCad already provides generation capabilities.

## Consequences
### Positive
- Single architecture supports CLI automation and plugin UX parity.
- Cleaner boundaries and improved long-term maintainability.
- Easier capability growth (additional fabricators, policy modules, workflows).
- Better test strategy: contract tests for orchestration + adapter behavior tests.

### Tradeoffs
- Short-term refactor cost to move orchestration out of CLI command handlers.
- Requires new execution contracts and adapter rewiring before visible plugin parity gains are complete.
- Need careful compatibility handling while transitioning current CLI behavior.

### Risks and mitigations
- Risk: scope creep during "thin CLI restoration."
  - Mitigation: move orchestration in bounded vertical slices (BOM, POS, fabrication pipeline).
- Risk: plugin UX complexity (threading/cancellation/progress).
  - Mitigation: standardize on job event contract first, then adapter rendering.
- Risk: policy drift between adapters.
  - Mitigation: enforce shared orchestration path and adapter conformance tests.

## Phased execution model
Phase 1: Boundary restoration
- Extract BOM/POS orchestration and policy selection from CLI modules into application services.
- Keep CLI behavior equivalent via adapter remapping.

Phase 2: Shared job/session contract
- Define and implement JobRequest/JobContext/JobEvent/JobResult contracts.
- Rewire CLI to execute through shared job runner.

Phase 3: Fabrication capability completion
- Add gerber/drill/netlist service APIs and implementations using KiCad-provided generation paths.
- Add correction-policy services (rotation/offset DB + field overrides).
- Add packaging/output and per-project option persistence services.

Phase 4: KiCad plugin adapter
- Implement ActionPlugin-based adapter over shared job runner with background execution and progress UI.
- Validate parity with CLI-generated artifacts for overlapping workflows.

## Issue policy
This ADR is implemented via a dedicated issue set that maps to phases above:
- boundary restoration,
- shared job/session contracts,
- fabrication services and policies,
- plugin adapter,
- parity and conformance tests.
