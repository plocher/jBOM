# Issue #247 — Documentation Charter Audit

Status: Pass-1 verdicts complete; disposition execution pending
Charter: [`DOCS-CHARTER.md`](../../../DOCS-CHARTER.md)
Branch: `issue-247-docs-readme-developer-refresh`
Parent issue: #247
Sub-issues: #300 (ADR format normalization 0011–0016) — **complete, awaiting user verification**
Follow-up issues filed: #301 (reframed: create design doc, do not amend ADR), #302 (F-006 BDD fault testing), #303 (F-007 CLI flag verify), #304 (F-008 Fabrication Platform ADR), #305 (F-013 CHANGELOG generation)

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
tree has exactly five top-level folders:

```
docs/
├── requirements/   ← what the system must do
├── architecture/   ← formal, frozen architectural decisions
├── design/         ← mutable design rationale
├── reference/      ← generated/constructed lookup
└── tutorials/      ← curated journeys

.agents/                     ← outside docs/, Warp's skill-loader location
└── skills/
    ├── README.md         ← explains the symlink convention
    └── <skill-name>/
        └── SKILL.md

docs/skills → ../.agents/skills    ← convenience symlink
```

Skills live at `.agents/skills/` because the Warp skill loader scans
specific project-relative directories (not `docs/`). A symlink at
`docs/skills/` keeps the `docs/` tree navigable without duplicating
content.

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
- **→skill** — Procedural how-to; migrates out of `docs/` to
  `.agents/skills/<skill-name>/SKILL.md`. The `docs/skills/` symlink
  makes the content reachable from the `docs/` tree as well.
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

## Pass-1 verdicts

Produced by parallel sub-agents (one per cluster, see Execution log).
All 34 in-scope files verdicted.

Format per entry:

```
#### docs/<path>
- Verdict: <useful | useless | mixed> | Charter: <jobs> | Audience: <list>
- Disposition: <verb> → <target>
- Rationale: <one sentence>
- Findings: <terse; cross-cutting elevated to F-NNN registry>
```

### Verdict summary

- **useful** (keep / refresh / relocate as-is): 9 files
- **useless** (delete): 8 files
- **mixed** (rewrite / split / refresh): 17 files

Net flow into target folders:
- `docs/reference/`: kicad-best-practices, lcsc-provider, kicad-plugin (split), cli (generated per #269), inventory-format (generated)
- `docs/tutorials/`: 4 renamed chapters + USER_GUIDE walk-throughs extracted
- `docs/design/`: architecture-overview, configuration-semantics, inventory-field-semantics, inventory-matching-semantics, service-command-architecture, bdd-axioms, plugin-ux-decisions, inventory-data-model, job-contracts (per reframed #301)
- `docs/requirements/`: fault_testing.md (open requirements; tracked by #302)
- `.agents/skills/`: bdd-scenarios, behave-subdirectory-loading, extend-jbom, dev-setup, kicad-plugin-setup (new skills, joining `git-workflow`)
- Repo root: `CHANGELOG.md` (now `generate` per charter; tracked by #305)
- Archive: 4 active-dev-notes (work landed), historical artifacts
- Delete: 8 useless + tree-level READMEs

### Root `docs/` files (15)

#### docs/README.md
- Verdict: mixed | Charter: (none, tree-level metadata) | Audience: all
- Disposition: rewrite → `docs/README.md` (new 5-folder tree index)
- Rationale: Permitted as tree-level metadata; needs full rewrite for the new layout.
- Findings: All 8 cross-reference links break post-migration (resolves on rewrite).

#### docs/README.developer.md
- Verdict: mixed | Charter: axioms, decision-history, pedagogy | Audience: developer, agent
- Disposition: split → conceptual architecture to `docs/design/architecture-overview.md`; extension how-to to `.agents/skills/extend-jbom/SKILL.md`; BOMGenerator private-method API section → delete
- Rationale: Mixes durable design content with procedural how-to and private-method documentation that doesn't belong as a public extension surface.
- Findings: "Automated Releases" duplicates `git-workflow` skill; documents `_`-prefixed methods as extension surface (anti-pattern); module listing missing `sophisticated_inventory_matcher.py` (F-011).

#### docs/README.man1.md
- Verdict: mixed | Charter: pedagogy | Audience: user
- Disposition: generate → `docs/reference/cli.md` (per #269 argparse-extraction pattern); editorial workflow examples extracted to tutorials or a skill
- Rationale: CLI flag enumeration is the textbook `generate` candidate; the narrative workflow examples carry modest pedagogical value worth preserving separately.
- Findings: `--triage` / `--no-aggregate` cross-doc inconsistency with inventory-field-semantics.md (F-007); INVENTORY-SEARCH retirement noted, but lcsc-provider.md still references it as live (resolves in lcsc-provider refresh).

#### docs/README.man3.md
- Verdict: useless | Charter: (none) | Audience: developer
- Disposition: delete
- Rationale: Documents a planned v8.x Python API that doesn't exist and has no gherkin coverage; charter: no scenario → no claim → no doc.
- Findings: InventoryItem field names `amperage`/`wattage` may be stale per README.man5.md's `current`/`power`; resolves at delete.

#### docs/README.man4.md
- Verdict: mixed | Charter: pedagogy | Audience: user, config-author
- Disposition: split → setup to `.agents/skills/kicad-plugin-setup/SKILL.md`; reference (command syntax, output columns) to `docs/reference/kicad-plugin.md`
- Rationale: Procedural setup is skill-shaped; command syntax and output format tables are genuine reference material.
- Findings: Platform config paths (Library/Application Support, %APPDATA%, ~/.config) disagree with README.configuration.md's `.jbom/`-directory profile resolution — stale content. LCSC listed as required column, but README.man5.md marks LCSC deprecated in favor of `Supplier`+`SPN`.

#### docs/README.man5.md
- Verdict: mixed | Charter: axioms, pedagogy, negative-space | Audience: user, config-author
- Disposition: split → column enumeration to `docs/reference/inventory-format.md` (generated from Pydantic field descriptions per #269); matching-semantics axioms (blank-field invariant, tolerance substitution, IPN multi-row intent) to `docs/design/inventory-matching-semantics.md`
- Rationale: Column enumeration is generate material; the blank-field-no-constraint axiom, tolerance-aware substitution invariants, and IPN multi-sourcing explanation are genuine hand-authored axioms that must survive.
- Findings: Typo in IPN paragraph (line 27, "perspectivem"); legacy alias mapping (V/Volts/Voltage etc.) duplicates inventory-field-semantics.md's `annotate --normalize` mapping — cross-doc consistency to verify; LCSC deprecation status disagrees with README.man4.md.

#### docs/README.configuration.md
- Verdict: mixed | Charter: axioms, decision-history | Audience: config-author, developer
- Disposition: split → merge semantics + field reference axioms to `docs/design/configuration-semantics.md` (links to ADR 0008 and 0009); enumerable schema reference to `docs/reference/configuration.md` (generated per #269)
- Rationale: Profile resolution order, inheritance/merge semantics, and namespace axioms are codebase invariants; the stanza enumeration is generate material.
- Findings: `i:package` examples conflict with ADR 0009's `inv:<field>` namespace (F-004 → covered by #282); `jbom config --schema` command stub status needs verification before relying on it as the replacement artifact.

#### docs/README.tests.md
- Verdict: useless | Charter: (none) | Audience: developer
- Disposition: delete (obsoleted)
- Rationale: References legacy monolithic `test_kicad_bom_generator.py`; project is now `tests.test_jbom`; procedural run instructions belong in a skill.
- Findings: All run commands reference the old test module path; the "46 tests" expectation is likely stale; `python -m unittest` should be `python -m behave` per project's BDD-first practice. If run-instruction content is needed, prefer a thin `→skill` over refreshing this doc.

#### docs/CHANGELOG.md
- Verdict: useful (content) but **generate per charter** | Charter: decision-history | Audience: user, developer
- Disposition: generate → repo-root `CHANGELOG.md` with semantic-release; pre-commit hook + CI staleness check (tracked by #305)
- Rationale: Charter amendment `89e890a` (resolving F-013) made CHANGELOG.md fully generated. The hand-curated `[Unreleased]` content observed today will be replaced by the first clean generated output.
- Findings: Malformed `[Unreleased]` section has multiple `### Added` and `### Changed` blocks — evidence of silent drift the new pre-commit hook will prevent (F-013).

#### docs/CONTRIBUTING.md
- Verdict: mixed | Charter: axioms, pedagogy | Audience: developer
- Disposition: split → conceptual contributor-onboarding (code style policy, testing philosophy) to `docs/design/contributing.md`; procedural sections (Development Setup, Running Tests, Common Tasks, Package Distribution) to `.agents/skills/dev-setup/SKILL.md`; git-workflow sections → delete in favor of `git-workflow` skill
- Rationale: Mixes conceptual policy with procedural how-to that is superseded by the existing `git-workflow` skill and a new `dev-setup` skill.
- Findings: Line 105 lists retired `workflows/registry.py` as an extension point (stale); line 231 references `sophisticated_inventory_matcher.py` (F-011); line 114 hard-codes `docs/CHANGELOG.md` — needs updating when CHANGELOG relocates to repo root.

#### docs/WARP.md
- Verdict: mixed | Charter: axioms | Audience: agent, developer
- Disposition: extract writing-standards clause (jBOM spelling, SEE ALSO conventions, prose style) into `DOCS-CHARTER.md` authoring-rules section; delete the rest
- Rationale: Writing standards are legitimate doc-authoring axioms; the rest is pre-migration structural guidance that will be invalid post-rename.
- Findings: Structure section lists pre-migration layout (will mislead any post-rename agent); update-requirements section duplicates charter maintenance section.

#### docs/inventory-field-semantics.md
- Verdict: useful | Charter: axioms, negative-space, decision-history | Audience: config-author, developer
- Disposition: keep → `docs/design/inventory-field-semantics.md`
- Rationale: Two-state blank/explicit model and `~`-semantics section are genuine axioms + negative-space material; scope-bounded write-back rules are precise behavioral contracts.
- Findings: Sources of F-007 (`--triage`, `--no-aggregate` flag references vs man1).

#### docs/kicad-best-practices.md
- Verdict: useful | Charter: axioms, pedagogy, negative-space | Audience: user, config-author
- Disposition: keep → `docs/reference/kicad-best-practices.md`
- Rationale: Category routing signal tables encode matching-code invariants; property-population guidance is pedagogical without duplicating extractable content; `~` don't-care convention is clean negative-space documentation.
- Findings: "Phase 4" internal terminology should be verified against current search-layer naming; defaults config path (`.jbom/generic.defaults.yaml`) inconsistent with `src/jbom/config/defaults/generic.defaults.yaml` in other docs.

#### docs/lcsc-provider.md
- Verdict: mixed | Charter: axioms, negative-space | Audience: user, config-author
- Disposition: refresh → `docs/reference/lcsc-provider.md` (update retired CLI references; verify parametric-fallback table)
- Rationale: Known-limitations section is high-value negative-space; MPN-vs-parametric flow is a behavioral axiom; but cache-management commands and config path reference retired CLI / legacy suffix format.
- Findings: `jbom inventory-search --no-cache` / `--clear-cache` commands reference the RETIRED `inventory-search` subcommand; legacy `*.supplier.yaml` suffix is superseded by unified `*.jbom.yaml`. Resolves at refresh.

#### docs/jbom-config-schema.yaml
- Verdict: useless | Charter: (none) | Audience: config-author, developer
- Disposition: delete (obsoleted)
- Rationale: Hand-authored YAML schema superseded by Pydantic schema generation per #269; cannot be CI-staleness-checked; charter explicitly prohibits hand-authored docs duplicating machine-extractable content.
- Findings: `i:package` namespace prefix throughout (F-004 → #282); Digi-Key distributor entry doesn't appear elsewhere (aspirational, never implemented).

### `docs/tutorial/` files (5)

#### docs/tutorial/README.md
- Verdict: mixed | Charter: pedagogy | Audience: user
- Disposition: refresh → `docs/tutorials/README.md` (rename chapters to numbered filenames; fix command error)
- Rationale: Tutorial index has stale `jbom inventory-search` reference; chapter filenames are legacy artifacts that should become numbered.
- Findings: Correct command is `jbom inventory --supplier`, not `jbom inventory-search` (retired).

#### docs/tutorial/README.context.md
- Verdict: useful | Charter: pedagogy, intent | Audience: user
- Disposition: keep → `docs/tutorials/01-key-concepts.md` (rename only)
- Rationale: Conceptual orientation; no procedural scenario needed (concepts, not commands).
- Findings: Exit-code semantics claim needs freshness verification at rename.

#### docs/tutorial/README.implementation.md
- Verdict: mixed | Charter: pedagogy | Audience: user
- Disposition: refresh → `docs/tutorials/02-first-bom.md` (add hypothesis marker; rename)
- Rationale: Individual commands have scenario coverage, but no end-to-end scenario chains the full tutorial workflow; per charter, mark as hypothesis until E2E scenario lands.
- Findings: No E2E scenario — hypothesis marking required.

#### docs/tutorial/README.integration.md
- Verdict: mixed | Charter: pedagogy | Audience: user
- Disposition: refresh → `docs/tutorials/03-finding-enriching-parts.md` (add hypothesis marker; rename)
- Rationale: Core supplier-populate and audit-freshness workflows are scenario-backed, but `--dry-run`, `--list-fields`, and cache-management flags have no coverage; no E2E chain.
- Findings: Flag-level coverage gaps; hypothesis marking required.

#### docs/tutorial/README.documentation.md
- Verdict: mixed | Charter: pedagogy | Audience: user, config-author
- Disposition: rewrite → `docs/tutorials/04-customising-workflow.md`
- Rationale: Documents unimplemented `based_on:` profile syntax (canonical is `extends:`); admits `--defaults` flag is planned-not-implemented; zero scenario coverage; needs substantive rewrite.
- Findings: `based_on:` doesn't exist; should be `extends:` per ADR 0008 (F-012); uses Windows `copy` instead of Unix `cp`; Step B3 admits `--defaults` is unimplemented.

### Active development notes (5)

#### docs/dev/development_notes/active/back_annotation_requirements.md
- Verdict: useful | Charter: decision-history | Audience: developer
- Disposition: archive → `docs/archive/development_notes/active/back_annotation_requirements.md`
- Rationale: Work fully implemented (`Component.uuid`, `InventoryItem.uuid`, `jbom annotate --repairs` all landed per CHANGELOG); doc is historical context.
- Findings: Spec named class `SchematicPatcher`; actual implementation is `AnnotationService`; `--repairs`/`--normalize` flags not in spec; `--per-instance` mode replaced the originally-proposed UUID column. Informational only.

#### docs/dev/development_notes/active/component_rotation_correction_requirements.md
- Verdict: mixed | Charter: decision-history, requirements | Audience: developer
- Disposition: archive → `docs/archive/development_notes/active/component_rotation_correction_requirements.md`
- Rationale: Core rotation correction implemented but via materially different architecture (footprint-regex against `transformations.csv`, not per-part MPN lookup); domain knowledge has historical value but architecture section is superseded.
- Findings: Implementation diverged from spec (footprint-regex vs per-part-MPN); phases 2–4 (MPN/DPN DB import, math offset, more fabricators) appear unimplemented; product decision needed whether to track those as code work.

#### docs/dev/development_notes/active/comprehensive_fault_testing_requirements.md
- Verdict: useful | Charter: requirements | Audience: developer
- Disposition: keep → `docs/requirements/fault_testing.md`
- Rationale: Identifies an open testing gap (no BDD coverage for file-parsing fault paths); content is forward-looking requirements, not history.
- Findings: F-006 — BDD scenarios don't cover file-parsing fault paths (tracked by #302).

#### docs/dev/development_notes/active/fabricator_integration_requirements.md
- Verdict: useful | Charter: decision-history | Audience: developer
- Disposition: archive → `docs/archive/development_notes/active/fabricator_integration_requirements.md`
- Rationale: All "Next Steps" implemented (`jbom fab`, `GerberExporter`, fabricator-specific Gerber naming, zip packaging); spec is historical.
- Findings: F-008 — "Fabrication Platform" architectural framing exists here and in CHANGELOG but not as an ADR (tracked by #304).

#### docs/dev/development_notes/active/plugin_ux_storyboard.md
- Verdict: mixed | Charter: decision-history | Audience: developer
- Disposition: rewrite → `docs/design/plugin-ux-decisions.md`
- Rationale: Substantially implemented (cited by `src/jbom/plugin/dialog.py`) but with one design divergence and a missing post-storyboard rationale; a light rewrite strips the ASCII mockup and captures the current design-rationale state.
- Findings: F-009 — archive-name field implemented as editable, storyboard specified read-only (storyboard was naive per user; rewrite reflects implementation choice); #249 (grayed-out checkbox) referenced; #250 referenced; modeless `Show()` rationale in `dialog.py` (Blocker 2) not in storyboard — capture in rewrite.

### Development notes root (5)

#### docs/dev/development_notes/BDD_AXIOMS.md
- Verdict: mixed | Charter: axioms, pedagogy | Audience: developer, agent
- Disposition: split → axiom definitions to `docs/design/bdd-axioms.md`; checklist + annotated examples to `.agents/skills/bdd-scenarios/SKILL.md`
- Rationale: 24 axioms are genuine test-suite invariants (design); review checklist and annotated examples are procedural how-to (skill).
- Findings: "Implementation Status" section (lines 478–506) embeds ephemeral PM state — must not survive to either destination; Axiom #4 (multi-modal testing) needs freshness verification against current step definitions before promotion.

#### docs/dev/development_notes/BEHAVE_SUBDIRECTORY_LOADING.md
- Verdict: useful | Charter: decision-history, pedagogy | Audience: developer, agent
- Disposition: →skill → `.agents/skills/behave-subdirectory-loading/SKILL.md`
- Rationale: Self-contained procedural solution for a concrete, recurring technical problem; per charter, procedural how-to lives in skills.
- Findings: Overlaps with development_notes/README.md (consolidate sources during skill creation); referenced external URL should be verified accessible.

#### docs/dev/development_notes/development_tasks.md
- Verdict: useless | Charter: (none) | Audience: (expired)
- Disposition: delete
- Rationale: One-time agent session brief for completed work; no persistent charter job.
- Findings: none

#### docs/dev/development_notes/README.md
- Verdict: useless | Charter: (none) | Audience: (navigation index)
- Disposition: delete
- Rationale: Directory navigation index for a directory being dissolved; only substantive content (BDD Step Loading Design Pattern) duplicates BEHAVE_SUBDIRECTORY_LOADING.md (which is migrating to skill).
- Findings: none

#### docs/dev/development_notes/sample_detailed_validation_report.txt
- Verdict: useless | Charter: (none) | Audience: (none)
- Disposition: delete
- Rationale: Snapshot of program output from a single validation run dated 2025-12-21; no charter job; not a test fixture; no link to a gherkin scenario.
- Findings: "Methodology Observations" section has design-relevant notes (Unicode normalization, package variation, tolerance matching) that could be harvested for a future inventory-search design doc IF that feature is actively developed; document decision in commit message.

### Guides (3)

#### docs/dev/guides/DEVELOPER_GUIDE.md
- Verdict: mixed | Charter: axioms, decision-history, pedagogy | Audience: developer, agent
- Disposition: split → architecture rationale + core principles to `docs/design/service-command-architecture.md`; procedural "how to extend jBOM" patterns to `.agents/skills/extend-jbom/SKILL.md`
- Rationale: Genuinely durable design content (service/common axiom, dependency direction, inventory data model, performance/error axioms) interleaved with procedural code templates and extension recipes.
- Findings: src/jbom/ layout description may be stale (no `application/jobs/` mention); aggregate-with-dedup function name needs verification; F-005 (first-file-wins dedup) appears here and in USER_GUIDE — docs stale, code wins (resolves at split); dependency-direction assertion to cross-check against ADR 0013.

#### docs/dev/guides/USER_GUIDE.md
- Verdict: mixed | Charter: pedagogy, decision-history | Audience: user, config-author
- Disposition: split → workflow walk-throughs to `docs/tutorials/inventory-workflows.md` and `docs/tutorials/manufacturing-handoff.md`; Command Overview + CSV File Formats → delete (replace with generated reference per #269); Inventory Data Model rationale to `docs/design/inventory-data-model.md`
- Rationale: Workflow sections are genuine pedagogy; command overview + format tables duplicate extractable reference material that the charter assigns to generated docs.
- Findings: F-005 (first-file-wins multi-source dedup ignoring Priority); `jbom fab` description details need verification; tutorial sections require gherkin-scenario backing per charter — file gaps as separate issues if not already tracked.

#### docs/dev/guides/README.md
- Verdict: useless | Charter: (none) | Audience: (navigation index)
- Disposition: delete
- Rationale: Four-sentence directory navigation index for a directory being dissolved.
- Findings: none

### Tree-level READMEs

#### docs/dev/README.md
- Verdict: useless | Charter: (none) | Audience: (navigation index)
- Disposition: delete
- Rationale: Navigation index for `docs/dev/`, a directory being dissolved under the new 5-folder structure.
- Findings: References `workflow/QUICK_START.md` which is pre-resolved to `delete (obsoleted)` — stale before this audit even started.

## Execution log

Dispositions actually executed on this branch (in commit order):

- `f05cc6d` — pre-charter tactical refresh of `docs/README.developer.md` (predates this audit; will be re-evaluated under Pass-1).
- `2b0a0f6` — Charter + audit scaffold introduced.
- `ed74e68` — Charter amended: layering axiom, architecture/design split, skills synonymy, freshness rules.
- `66c8873` — Audit doc: pre-resolved dispositions captured, target tree, #300 filed.
- `9ce1cd1` — Charter corrected: skills location moved to `.agents/skills/` with `docs/skills/` as symlink.
- `ab9dfd4` — Audit doc corrected: 5 docs folders + `.agents/skills/`.
- `a158d25` — **Executed**: GIT_WORKFLOW.md → `.agents/skills/git-workflow/SKILL.md` (skill promotion), `.agents/skills/README.md`, `docs/skills` symlink.
- `0fc44ee` — Asset commit: `docs/assets/icons/` plugin icons (out-of-band addition, future plugin work).
- `3398832` — **Executed (via #300)**: ADR 0011 (project-centric-design).
- `77c0580` — **Executed (via #300)**: ADR 0012 (component-attribute-enrichment).
- `143fe7a` — **Executed (via #300)**: ADR 0013 (domain-centric-design, 4-file consolidation).
- `fedc407` — **Executed (via #300)**: ADR 0014 (job-contracts) — F-001 verified, divergence filed as #301.
- `95d62d5` — **Executed (via #300)**: ADR 0015 (config-schema-audit).
- `563288a` — **Executed (via #300)**: ADR 0016 (eaglelib2kicad-adapter-requirements).

## Cross-cutting findings

- **F-001** — *Resolved.* Surfaced under #300 (ADR 0014 conversion); initially filed as #301. Reframed under charter amendment `89e890a` (see F-010): implementation specifics belong in design docs, not ADRs. Resolution now: create `docs/design/job-contracts.md`; ADR 0014 stays as-is. Tracked by reframed #301.
- **F-002** — ADR 0013 (domain-centric-design consolidation) contains a minor stale cross-reference within the `Layer responsibilities` subsection (original "See also: design-patterns.md" now points to content within the same ADR). Cosmetic only; not corrected.
- **F-003** — ADR 0013 `Integration patterns` subsection contains language asserting CLI orchestrates services, slightly at odds with the layered design that places orchestration in the application layer. Original wording preserved verbatim; resolve via superseding ADR if needed.
- **F-004** — Namespace prefix inconsistency (`i:` / `s:` / `p:` / `a:` vs `inv:` / `sch:` / `pcb:` / `ann:`) spanning `README.configuration.md`, `jbom-config-schema.yaml`, `kicad-best-practices.md`, and other files. **Covered by existing #282** (`refactor(config): finish s:/p:/i:/a: → sch:/pcb:/inv:/ann: namespace rename`). No new issue needed.
- **F-005** — Multi-source inventory dedup described as "first file wins, ignoring Priority" in `DEVELOPER_GUIDE.md` and `USER_GUIDE.md`. **Resolution: docs are stale, code is correct** (per user disposition; code reflects tight binding of subcommand intent and priority). Resolves in those docs' split dispositions; no new issue.
- **F-006** — No BDD scenarios cover file-parsing fault paths (KiCad S-expression edge cases, Excel/Numbers/CSV malformed inputs). **Filed as #302**.
- **F-007** — `jbom annotate --triage` and `jbom inventory --no-aggregate` referenced in `inventory-field-semantics.md` but absent from `README.man1.md`. **Filed as #303**.
- **F-008** — "Fabrication Platform" architectural framing (jBOM superseding `kicad-jlcpcb-tools`) referenced in `CHANGELOG.md` and `fabricator_integration_requirements.md` but not formalized as an ADR. **Filed as #304**.
- **F-009** — Plugin dialog implements archive-name field as editable; storyboard specified read-only label. **Resolution: implementation is the design choice** (per user disposition; storyboard was naive). Resolves in `plugin-ux-decisions.md` rewrite; no new issue.
- **F-010** — *Resolved by charter amendment `89e890a`.* Architecture-vs-design *content* boundary now explicit: implementation detail belongs in design docs, not in architecture/ADRs. Per the new rule, #301's resolution path was reframed from "amend ADR 0014" to "create `docs/design/job-contracts.md`".
- **F-011** — `sophisticated_inventory_matcher.py` cross-doc references (CONTRIBUTING.md, DEVELOPER_GUIDE.md, README.developer.md) need verification against current `src/`. **Resolves naturally** through the per-file rewrites/splits in this audit; no new issue.
- **F-012** — Tutorial 4 documents `based_on:` fabricator-profile syntax that doesn't exist in code; canonical is `extends:` per ADR 0008. **Resolution: extends is canonical** (per user disposition). Resolves in T4 rewrite; no new issue.
- **F-013** — *Resolved by charter amendment `89e890a`.* `CHANGELOG.md` is now defined as fully generated; hand-edits rejected by pre-commit hook + CI staleness check. Malformed `[Unreleased]` section observed today resolves at first generated output. **Implementation tracked by #305**.

## Follow-up issues filed

- **#300** — `docs(architecture): convert pre-ADR architectural
  decisions to formal ADRs (0011–0016)`. Required child of #247.
  **Complete**; six ADRs cherry-picked into the parent branch;
  awaiting user verification before #300 is closed.
- **#301** — **Reframed.** Originally `docs(architecture): amend ADR
  0014 — job-contracts omits implementation details (F-001)`. Now:
  `docs(design): create docs/design/job-contracts.md for
  implementation specifics`. ADR 0014 stays as-is.
- **#302** — `test(features): add BDD scenarios for file-parsing
  fault paths (F-006)`.
- **#303** — `chore(cli): reconcile docs vs implementation for `jbom
  annotate --triage` and `jbom inventory --no-aggregate` (F-007)`.
- **#304** — `docs(architecture): publish ADR for the Fabrication
  Platform decision (F-008)`.
- **#305** — `chore(release): make CHANGELOG.md fully generated
  with pre-commit hook + CI staleness check (F-013)`. Implements the
  charter clause added in `89e890a`.

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
