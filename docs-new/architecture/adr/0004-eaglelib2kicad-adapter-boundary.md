# ADR 0004: EagleLib2KiCad Integration Boundary — Service-Surface-First, Phased Convergence
Date: 2026-04-29
Status: Proposed (awaiting review)
Related: #214
## Context
jBOM already has service APIs for project context, inventory context, supplier search, and matching. EagleLib2KiCad integration requires additional contexts (Eagle libraries and KiCad symbol/footprint library management). A new parallel adapter model layer would duplicate contract surfaces and increase maintenance cost.
## Decision drivers
- Keep one stable contract model for jBOM and adjacent tooling.
- Reduce contract drift and duplicated abstractions.
- Preserve domain-centric layer boundaries.
- Support iterative delivery where API surface quality can be production-grade before full backend maturity.
- Keep implementation-heavy import/lib-manager policy in the adjacent repository until semantics stabilize.
## Options considered
### Option A: Introduce a dedicated adapter-model layer
Define separate adapter entities/contracts and map them to service APIs.
Result: Rejected.
Reasons:
- Duplicates contract definitions.
- Creates synchronization risk between adapter contracts and service APIs.
- Increases long-term maintenance and test burden.
### Option B: Service-surface-first contract model with immediate in-jBOM implementation
Treat jBOM service APIs as canonical contracts and implement new Eagle/KiCad library-manager services directly in jBOM now.
Result: Deferred.
Reasons:
- Current library-manager semantics are still evolving and importer-specific.
- Premature in-jBOM implementation would couple unstable policy into jBOM.
### Option C: Service-surface-first contract model with phased convergence
Treat service APIs as canonical contract pattern, incubate implementation-heavy services in `EagleLib2KiCad` first, and converge into jBOM in a future issue when APIs stabilize.
Result: Accepted for issue #214 prep direction.
## Decision
Adopt Option C.
- Existing jBOM service APIs remain the contract surfaces for reuse.
- No parallel adapter entity hierarchy is introduced.
- Implementation-heavy Eagle/KiCad library-manager services are incubated in `EagleLib2KiCad` for now.
- A follow-up convergence issue will refactor mature service APIs into jBOM.
## Consequences
### Positive
- One contract pattern for in-core and adjacent tools.
- Lower cognitive and maintenance overhead from avoiding parallel model hierarchies.
- Cleaner BDD contract testing strategy tied to service APIs.
- Lower short-term risk of embedding unstable importer policy into jBOM.
### Tradeoffs
- Future convergence requires coordinated refactor across repositories.
- Service API compatibility expectations must be explicit before merge-back into jBOM.
## Contract testing policy
- Behave/gherkin scenarios define and validate service contract behavior.
- Pytest validates internal helper logic and implementation details behind those contracts.
## Iteration-1 constraints
- No destructive writes to KiCad artifacts from jBOM.
- No required CLI changes in this jBOM prep slice.
- jBOM focuses on architecture boundary documentation and future expansion seam.
