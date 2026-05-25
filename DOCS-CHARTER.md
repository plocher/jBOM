# jBOM Documentation Charter

This document governs what documentation jBOM produces, who it serves, how
it is authored, and how it is kept honest. It is policy for the `docs/`
tree (and any documentation adjacent to it); changes to this charter
require the same review as any other architectural decision.

The charter is the test future documentation is evaluated against. When
the charter and an existing doc disagree, the existing doc is wrong until
proven otherwise.

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

## Audiences

Four first-class audiences, served by distinct top-level entry points:

- **User** (including the power-user hat) — runs `jbom` from the CLI or
  the KiCad plugin. Reads `docs/README.man*.md`, tutorials, and how-to
  recipes.
- **Config author** — writes `.jbom.yaml`, builds fabricator and supplier
  profiles. May not read Python. Reads a focused config-authoring guide
  plus the generated `docs/README.configuration.yaml.md` (per #269).
- **Developer** — extends jBOM. Reads `docs/dev/*`. Plugin authors are a
  subset of this audience, distinguished by reading a stable-contract
  marking within the developer surface rather than a separate doc tree.
- **Agent working on jBOM** — automation operating on the repository.
  Reads `WARP.md` and the developer surface.

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
