# jBOM Documentation

This tree contains all jBOM documentation. Five top-level folders, each
with a single purpose:

- [`requirements/`](requirements/) — what the system must do
- [`architecture/`](architecture/) — formal, frozen architectural decisions (ADRs)
- [`design/`](design/) — mutable design rationale
- [`reference/`](reference/) — generated lookup material
- [`tutorials/`](tutorials/) — curated learning journeys

Skills (procedural how-tos for humans + agents) live outside `docs/`
at [`../.agents/skills/`](../.agents/skills/). A convenience symlink
is available at [`skills/`](skills/).

The rest of this document is the **Documentation Charter** — the
policy that governs this tree, its folder structure, and the skills
directory. When the charter and an existing doc disagree, the
existing doc is wrong until proven otherwise.

Changes to the charter portion of this document require the same
review as any other architectural decision.

---

## Why docs exist

The code is a complete, executable artifact. Documentation only earns its
place when it carries something the code cannot:

1. **Intent** — what we wanted, vs what the code does today.
2. **Axioms** — invariants future changes must honor.
3. **Negative space** — what jBOM deliberately *doesn't* do, and why.
4. **Pedagogy** — guided journeys that the code's structure won't reveal on its own.
5. **Decision history** — why this design rather than plausible alternatives.

Anything outside those five is either machine-extractable (and should be
generated) or destined to rot. Each doc in the tree must be able to point
at the job(s) above that it does. Docs that cannot make that claim are
candidates for deletion.

## Structural axiom — layering and validation pairing

jBOM documentation follows the same layering as the codebase, with each
layer paired to its validation mechanism:

```
docs/requirements/   ← what the system must do
docs/architecture/   ← how we meet the requirements
features/*           ← how we validate the requirements (BDD)
docs/design/         ← how we instantiate the architecture
src/*                ← how we implement the design
pytest/*             ← how we validate the design (unit)
```

Each layer answers a different "how" question. The folder structure of
`docs/` is dictated by this layering — not by audience, not by historical
accident.

## Architecture vs Design — durability hierarchy

Within the "decision history" job, two distinct sub-categories exist:

- **Architecture** — formal, frozen, additive. Changes only by adding a
  new ADR (or similarly formal published decision). Existing
  architectural content is not rewritten; if it appears to disagree with
  the code, a content-freshness finding is filed and resolved by either
  correcting the code or publishing a superseding ADR.
- **Design** — mutable rationale below architecture. Changes as needed,
  kept honest by the BDD/TDD scaffold. Design decisions may graduate
  into architecture by being published as ADRs.

Format-level normalization of architecture documents (adding ADR
scaffolding, recording provenance) may be applied to existing
architecture documents that lack the standard form. Such
normalization preserves source content verbatim and is tracked as a
discrete, reviewable change. It is the only modification of
architecture content other than publishing a new ADR.

## Architecture vs Design — content boundary

Beyond durability, architecture and design carry different *kinds* of
content:

- **Architecture docs (ADRs)** name the decision — the contract,
  principle, or commitment. They describe the *what* and *why* at the
  level of commitment. Their stability comes from the stability of the
  underlying decision.
- **Design docs** describe how the architecture is currently
  instantiated: concrete field shapes, type relationships, helpers,
  ordering rules. They are mutable because instantiation evolves
  while the underlying decision holds.
- **Implementation** (`src/`) is the executable artifact. It is the
  source of truth for "what the code does today."
- **Tests** (`features/`, `pytest/`) validate that implementation
  honors architecture and design.

When an architecture doc accumulates implementation detail (specific
field names, type signatures, exact ordering enforcement points), it
accrues maintenance cost without earning durability — the detail
changes whenever the implementation evolves. Such content belongs in
design docs, not architecture docs.

When in doubt: would adding, removing, or renaming this field require
a new ADR? If yes, the content is architecture. If no, the content is
design.

## Folder structure

`docs/` contains exactly these top-level folders, each with a single
purpose:

- `requirements/` — what the system must do (user scenarios, functional
  scenarios, use cases)
- `architecture/` — formal, frozen architectural decisions (ADRs)
- `design/` — mutable design rationale; bounded by BDD/TDD
- `reference/` — generated/constructed lookup material
- `tutorials/` — curated learning journeys

Skills live at `.agents/skills/<skill-name>/SKILL.md`, not inside
`docs/`, because the Warp skill loader scans specific project-relative
directories (`.agents/skills/`, `.warp/skills/`, `.claude/skills/`,
etc.) and does not scan `docs/`. A convenience symlink at
`docs/skills/` → `../.agents/skills/` keeps the `docs/` tree navigable
for humans without duplicating content. On platforms where symlinks
degrade (Windows without developer mode), the real path under
`.agents/skills/` remains accessible; the symlink is navigation aid
only, with a `README.md` in the directory explaining the convention.

Files at `docs/` root (e.g. `README.md`) are tree-level metadata, not
content.

## Audiences

Four first-class audiences. The folder structure serves them, but
audience and folder are not 1:1 — most folders serve multiple audiences
with different content:

- **User** (including the power-user hat) — runs `jbom` from the CLI or
  the KiCad plugin. Primary folders: `tutorials/`, `reference/`.
- **Config author** — writes `.jbom.yaml`, builds fabricator and
  supplier profiles. May not read Python. Primary folders: a focused
  config-authoring guide under `skills/`, plus the generated
  configuration reference (per #269).
- **Developer** — extends jBOM. Primary folders: `architecture/`,
  `design/`, `skills/`, `requirements/`. Plugin authors are a subset
  distinguished by a stable-contract marking within the developer
  surface.
- **Agent working on jBOM** — automation operating on the repository.
  Reads `WARP.md` and the same `skills/` content as developers.
  Procedural skill content is a single source serving both developer
  onboarding and agent execution; this audience collapses partially
  into "developer" for skill-shaped content.

Agents *using* jBOM are not a first-class audience; the CLI and KiCad
plugin already absorb that workflow, and the user-facing docs cover it.

## Authoring rules

### Generated where it serves the reader; curated where comprehension matters

- **Generate** when the artifact is naturally enumerable and the reader's
  job is lookup, not understanding: CLI flag references, config schema
  references, exhaustive parameter tables. Generated docs without a CI
  staleness check do not count as generated — they're hand-authored docs
  in disguise that nobody trusts.
- **Curate** (hand-author) when editorial judgment is the value: intent
  statements, axioms, architecture explanations, tutorials, ADRs.

Completeness is a property of reference material, not a virtue in itself.
Generated docs win where the reader benefits from exhaustiveness; they
lose where they would crowd out a curated narrative.

**`CHANGELOG.md` is fully generated.** The repository's changelog is
produced from conventional commit messages by semantic-release.
Hand-edits to `CHANGELOG.md` are rejected by a pre-commit hook plus a
CI staleness check that fails if the committed file diverges from a
fresh regeneration. Change history lives in commit messages and PR
descriptions; the changelog is a derived view.

### Tests appropriate to the job

- **User-behavior docs** (how-to, reference for user-visible commands)
  must trace to a passing gherkin scenario. No scenario → no claim → no
  doc. If a documented capability lacks a scenario, the doc waits until
  the scenario lands.
- **Intent / axiom / architecture docs** are tested by peer review
  against the code. They do not require gherkin coverage; gherkin
  cannot express the *why* or the *not*.
- **Tutorials** drive their own scenarios. A tutorial without a
  runnable end-to-end scenario behind it is a hypothesis and must be
  marked as such.
- **Generated docs** are tested by CI: the build fails if the committed
  artifact diverges from a fresh regeneration.

### Skills are the canonical form for procedural how-to

Procedural "how to do X" content — historically authored as "guides" —
is a single artifact serving both human onboarding and agent execution.
Skills (per the project's skill mechanism) are the canonical form;
they live at `.agents/skills/<skill-name>/SKILL.md` (Warp's
tool-agnostic project-skill location). The `docs/skills/` symlink
points there as a navigation convenience for the `docs/` tree. There
is no separate `guides/` folder; the audiences differ but the content
does not.

This is what collapses the developer and agent-working-on-jBOM
audiences for procedural content. Explanatory and conceptual content
(design rationale, architectural decisions, etc.) remains
audience-specific because its presentation differs by reader.

## Anti-goals

- No documentation for documentation's sake. A doc with no audience and
  no job is deleted, not refreshed.
- No completeness-by-default. The bar is "does a reader need this?",
  not "does this surface exist?"
- No silent behavior corrections during a docs sweep. If an audit
  finds that the code disagrees with documented intent, file a separate
  issue rather than fix it in a docs PR.
- No prose duplicating `--help` output, Pydantic field descriptions, or
  other already-extractable content. If the reader's job is lookup,
  generate it.
- No 1:1 doc-to-feature correspondence as a goal. Curated docs follow
  reader journeys, not feature inventories.
- No silent rewriting of frozen architecture content. If an audit
  finds the code disagrees with documented architecture, file a finding
  and resolve by either correcting the code or publishing a superseding
  ADR — not by editing the existing architecture doc.
- No procedural how-to as docs. If a piece of content tells someone how
  to do a task (rather than explaining a concept or recording a
  decision), it is a skill, not a doc.

## Maintenance

This charter is itself a hand-authored doc. Adding to it is a design
decision (PR with rationale, behave passes, peer review); removing or
amending a clause is the same. Drift from the charter in any doc PR
should be either contested or codified by amending the charter — not
silently tolerated.

Audits like the one tracked in #247 are periodic re-evaluations: they
re-apply the charter to the extant tree and produce evidence-based
disposition decisions. The charter does not change as a side effect of
an audit; an audit either confirms the charter is being honored or
files findings that lead to charter amendments through normal review.

Format-level normalization of architecture documents requires its
own tracking (a discrete, reviewable change set). It produces no
substantive content modifications — only scaffolding and provenance.

Content-freshness drift in any frozen doc is recorded as a finding,
not corrected in place. The finding is resolved by either fixing the
code (most common) or publishing a superseding decision (architecture).
