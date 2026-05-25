# Issue #247 — Documentation Charter Audit

Status: pre-resolved dispositions captured; Pass-1 pending
Charter: [`DOCS-CHARTER.md`](../../../DOCS-CHARTER.md)
Branch: `issue-247-docs-readme-developer-refresh`
Parent issue: #247
Sub-issues: #300 (ADR format normalization 0011–0016)

This audit applies the Documentation Charter to the existing `docs/`
tree and decides the disposition of each file. It is an
evidence-gathering artifact, not a rewrite plan: each non-trivial
disposition becomes its own commit (or follow-up issue) on the working
branch.

Files that move into `docs-new/` after triage are out of scope for
re-audit; the charter governs them from then on.

## Scope

All files currently under `docs/`. Anything created fresh in
`docs-new/` (this audit, the charter, new content) is born
post-charter and is not audited here.

Out of scope: changes to `src/`, behave features, the package's
behavior. Findings that touch those go to follow-up issues.

## Method

Two passes:

1. **Pre-resolved dispositions** — classes of files whose disposition
   is determined by structural policy (architecture content →
   relocate or ADR-convert; closed-issue findings → archive;
   obsoleted workflow → delete). Captured in the section below; need
   no per-file content verdict.
2. **Pass-1 verdict-driven dispositions** — files where the
   disposition depends on content inspection. Each file gets a
   verdict (useful / useless / mixed) and a disposition. Captured in
   the working matrix below.

## Target tree

Per the charter's folder-structure clause, the post-audit `docs/`
tree has exactly six top-level folders:

```
docs/
├── requirements/   ← what the system must do
├── architecture/   ← formal, frozen architectural decisions
├── design/         ← mutable design rationale
├── reference/      ← generated/constructed lookup
├── skills/         ← actionable how-tos (humans + agents)
└── tutorials/      ← curated journeys
```

Migration happens in `docs-new/` during the audit; the final commit
removes empty `docs/` and renames `docs-new/` → `docs/`.

## Disposition vocabulary

- **keep** — Relocate to target folder unchanged.
- **refresh** — Relocate with minor accuracy fixes only.
- **rewrite** — Significant rework; may retain title or topic but
  content is largely new. Often involves consolidation.
- **generate** — Content should come from code via a generator (#269
  pattern). The hand-authored file dies; a generator plus CI staleness
  check replaces it.
- **→ADR** — Content is architectural but pre-ADR-format. Converted
  to formal ADR under separately-tracked sub-issue (#300).
- **→skill** — Procedural how-to; migrates out of `docs/` into the
  project's skill mechanism.
- **→requirements (harvest)** — Content is requirements material
  currently tucked under `features/*/README.md`. Harvested into
  `docs/requirements/`; original location may retain a pointer.
- **archive** — Historical value; preserved under `docs/archive/`
  (typically closed-issue findings, retired plans, genesis docs,
  session logs).
- **delete (obsoleted)** — Superseded by platform primitives or other
  content; no historical value worth archiving.
- **delete** — No job, no audience, or wholly superseded.
- **finding-only** — Disposition is `keep`/`refresh`, but a separate
  finding (content-freshness or other) is filed alongside.

## Standing rules

- **Architecture content is frozen.** ADR conversion under #300 is
  the only permitted content operation outside of adding new ADRs.
  Other drift is recorded as a finding and resolved by fixing the
  code or publishing a superseding ADR.
- **Requirements harvest, don't move.** When pulling requirements out
  of `features/*/README.md`, default to leaving a pointer in the
  features README so the test scaffolding still self-documents. Move
  the whole README only when it's purely a requirements file.
- **One commit per non-trivial disposition.** Bulk archive/delete
  decisions may batch into one commit per class; per-file rewrites get
  their own commit.

## Pre-resolved dispositions

Dispositions determined by structural policy, not file-content
evaluation.

### `dev/architecture/adr/0001`–`0010` — 10 files, **keep** → `docs/architecture/adr/`

Already formal ADRs. Relocate only, no content change.

### `dev/architecture/*.md` ADR-conversion candidates — 9 files → 6 ADRs, **→ADR** via #300

Tracked under #300. Format normalization only; content preserved
verbatim with provenance.

- `project-centric-design.md` → `0011-project-centric-design.md`
- `component-attribute-enrichment.md` → `0012-component-attribute-enrichment.md`
- `domain-centric-design.md` + `design-patterns.md` + `layer-responsibilities.md` + `integration-patterns.md` → `0013-domain-centric-design.md` (four-file consolidation)
- `job-contracts.md` → `0014-job-contracts.md` (**finding F-001**: verify content against `src/jbom/application/jobs/`)
- `config-schema-audit.md` → `0015-config-schema-audit.md`
- `eaglelib2kicad-adapter-requirements.md` → `0016-eaglelib2kicad-adapter-requirements.md`

### `dev/architecture/*.md` other dispositions

- `anti-patterns.md` → `docs/design/` (**keep**) — historical design doc that informs future design work.
- `testing.md` → `features/` (**move**) — test design doc; co-locates with the test scaffolding it documents.
- `workflow-architecture.md` → `docs/requirements/` (**move**) — requirements/use-case content.
- `implementation-plan-250-251.md` → `docs/archive/` (**archive**) — closed-issue implementation plan.
- `why-jbom-new.md` → `docs/archive/` (**archive**) — historical design/genesis document.
- `dev/architecture/README.md` → **delete** — replaced by new top-level structure.

### `dev/requirements/` — 3 files → `docs/requirements/`

- `0-User-Scenarios.md` (**keep**)
- `1-Functional-Scenarios.md` (**keep**)
- `README.md` (**rewrite** as new entry-point if needed)

### `features/*/README.md` — **→requirements (harvest)**

Requirements content extracted into `docs/requirements/`; features
READMEs shrink to test-scaffolding content or retain pointers.
Per-file harvest decisions made during execution.

### `dev/validation/issue-123/*` — 5 files, **archive** → `docs/archive/validation/issue-123/`

Closed-issue validation findings.

### `dev/development_notes/completed/*` — 4 files

- `fabrication_platform_requirements.md` → **archive**
- `federated_inventory_requirements.md` → **archive**
- `inventory_management_requirements.md` → **archive**
- `QUICK_START.md` → **delete (obsoleted)** — paired-agent pattern superseded by `run_agents` and orchestration primitives.

### `dev/workflow/*` — mostly delete or archive

- `HUMAN_WORKFLOW.md` → **delete (obsoleted)** — manual supervisor/subagent pattern superseded by orchestration primitives.
- `NEXT.md` → **delete** — stale.
- `WORK_LOG.md` → **archive** — historical session log.
- `issue-226-plan.md` → **archive** — closed-issue plan.
- `GIT_WORKFLOW.md` → **→skill** — procedural workflow guidance.
- `README.md` → **delete** — replaced by new structure.

### `dev/development_notes/*` — known skill candidates

- `gh_PR_and_Issues.md` → **→skill** — zsh-safe `gh` CLI patterns.

### `dev/guides/*` — known skill candidates

- `plugin-dev-setup.md` → **→skill** — concrete dev-loop setup steps.

## Pass-1 working matrix

Files requiring per-file verdicts (useful / useless / mixed) before
disposition can be assigned. Pass-1 verdicts inform Pass-2
dispositions.

Format per entry:

```
### docs/<path>
- Verdict: TBD
- Disposition: TBD
- Notes:
```

### Root `docs/` files (15)

#### docs/README.md
- Verdict: TBD
- Disposition: TBD
- Notes:

#### docs/README.developer.md
- Verdict: TBD
- Disposition: TBD
- Notes: tactical refresh committed in `f05cc6d` on this branch may have changed the picture; re-read current state, not main.

#### docs/README.man1.md
- Verdict: TBD
- Disposition: TBD
- Notes: CLI reference; candidate for `generate` per #269 pattern.

#### docs/README.man3.md
- Verdict: TBD
- Disposition: TBD
- Notes: Python API; planned v8.x.

#### docs/README.man4.md
- Verdict: TBD
- Disposition: TBD
- Notes: KiCad plugin integration.

#### docs/README.man5.md
- Verdict: TBD
- Disposition: TBD
- Notes: Inventory file format.

#### docs/README.configuration.md
- Verdict: TBD
- Disposition: TBD
- Notes: superseded in part by #269.

#### docs/README.tests.md
- Verdict: TBD
- Disposition: TBD
- Notes: may be superseded by features/ + pytest design.

#### docs/CHANGELOG.md
- Verdict: TBD
- Disposition: TBD
- Notes: automated by semantic-release; placement decision (`docs/` root vs repo root).

#### docs/CONTRIBUTING.md
- Verdict: TBD
- Disposition: TBD
- Notes: procedural sections may split to skills.

#### docs/WARP.md
- Verdict: TBD
- Disposition: TBD
- Notes: may overlap with root `WARP.md`.

#### docs/inventory-field-semantics.md
- Verdict: TBD
- Disposition: TBD
- Notes: likely `reference/`.

#### docs/kicad-best-practices.md
- Verdict: TBD
- Disposition: TBD
- Notes: likely `reference/` or `tutorials/`.

#### docs/lcsc-provider.md
- Verdict: TBD
- Disposition: TBD
- Notes: likely `reference/`.

#### docs/jbom-config-schema.yaml
- Verdict: TBD
- Disposition: TBD
- Notes: likely **delete (obsoleted)** by #269.

### `docs/tutorial/` files (5)

#### docs/tutorial/README.md
#### docs/tutorial/README.context.md
#### docs/tutorial/README.implementation.md
#### docs/tutorial/README.integration.md
#### docs/tutorial/README.documentation.md

### Active development notes (5)

#### docs/dev/development_notes/active/back_annotation_requirements.md
#### docs/dev/development_notes/active/component_rotation_correction_requirements.md
#### docs/dev/development_notes/active/comprehensive_fault_testing_requirements.md
#### docs/dev/development_notes/active/fabricator_integration_requirements.md
#### docs/dev/development_notes/active/plugin_ux_storyboard.md

### Development notes root

#### docs/dev/development_notes/BDD_AXIOMS.md
- Verdict: TBD
- Disposition: TBD
- Notes: skill candidate vs design doc.

#### docs/dev/development_notes/BEHAVE_SUBDIRECTORY_LOADING.md
- Verdict: TBD
- Disposition: TBD
- Notes: likely **→skill** or **archive**.

#### docs/dev/development_notes/development_tasks.md
#### docs/dev/development_notes/README.md
#### docs/dev/development_notes/sample_detailed_validation_report.txt

### Guides

#### docs/dev/guides/DEVELOPER_GUIDE.md
- Verdict: TBD
- Disposition: TBD
- Notes: likely **rewrite/split** — architecture-overview material to `design/`; procedural to `skills/`.

#### docs/dev/guides/USER_GUIDE.md
- Verdict: TBD
- Disposition: TBD
- Notes: likely **rewrite/split** — walk-throughs to `tutorials/`; command overview duplicates `reference/`.

#### docs/dev/guides/README.md

### Tree-level READMEs (likely delete; verify)

#### docs/dev/README.md

## Cross-cutting findings

- **F-001**: `job-contracts.md` content-freshness — needs verification
  against current `src/jbom/application/jobs/` implementation. Tracked
  under #300's `0014-job-contracts.md` conversion; divergence triggers
  a separate code/follow-up issue (not an in-place edit of the
  architecture doc).

## Follow-up issues filed

- **#300** — `docs(architecture): convert pre-ADR architectural
  decisions to formal ADRs (0011–0016)`. Required child of #247.

## Axioms harvested from existing docs

Per the charter, axioms are one of the five reasons docs exist. The
audit collects axioms found in the existing tree here so the rewrite
phase has a single source.

- (To be populated during Pass-1 reading.)

## Done criteria for this audit

- Every file under `docs/` has a disposition: either pre-resolved
  above or pass-1-verdicted in the working matrix.
- All `→ADR` dispositions are tracked under #300 and #300 is closed.
- All `archive`, `delete`, and `delete (obsoleted)` dispositions are
  executed.
- All `→skill` dispositions are migrated to the project's skill
  mechanism.
- All `→requirements (harvest)` dispositions are completed with
  per-file harvest/pointer decisions recorded.
- Axioms section enumerates the axioms extracted from the tree.
- Findings section captures every code/scenario disagreement detected.
- Follow-up issues are filed for findings that require work outside
  the docs sweep.
- Final cleanup commit removes the empty `docs/` and renames
  `docs-new/` to `docs/`.
