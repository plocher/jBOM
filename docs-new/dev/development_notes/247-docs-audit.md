# Issue #247 — Documentation Charter Audit

Status: in progress
Charter: [`DOCS-CHARTER.md`](../../../DOCS-CHARTER.md)
Branch: `issue-247-docs-readme-developer-refresh`

This audit applies the Documentation Charter to the existing `docs/`
tree (the pre-charter tree) and decides the disposition of each file.
It is an evidence-gathering artifact, not a rewrite plan: each
disposition decision becomes its own commit (or follow-up issue) on
the working branch.

Files that move into `docs-new/` after triage are out of scope for
re-audit; the charter governs them from then on.

## Scope

All files currently under `docs/`. Anything created fresh in `docs-new/`
(this audit, the charter, new content) is born post-charter and is not
audited here.

Out of scope: changes to `src/`, behave features, the package's behavior.
Findings that touch those go to follow-up issues.

## Method

For each file under `docs/`:

1. **Bucket(s)** — which of the five charter jobs (Intent, Axioms,
   Negative space, Pedagogy, Decision history) does this file actually do?
   May be multiple. May be none (→ delete candidate).
2. **Stated audience** — which audience(s) (User, Config author,
   Developer, Agent) does the file claim or appear to address?
3. **Apparent original audience** — by inference from tone and content,
   who was this *originally* written for? A mismatch with stated audience
   is a finding.
4. **Accuracy** — current / partially stale / mostly stale / contradicts
   code / orphan (no longer applicable).
5. **Disposition** — see vocabulary below.
6. **Notes** — rationale, follow-up issues, dependencies on #269 or
   other in-flight work.

## Disposition vocabulary

- **keep** — Move to `docs-new/` unchanged; charter approves as-is.
- **refresh** — Move to `docs-new/` with minor accuracy fixes only.
- **rewrite** — Significant rework; possibly retains title or topic but
  content is largely new. Often involves consolidation with sibling files.
- **generate** — Content should come from code via a generator (#269
  pattern). The hand-authored file dies; a generator plus CI staleness
  check replaces it.
- **move** — Content stays valid but belongs in a different audience tree
  or at a different abstraction level.
- **delete** — No job, no audience, or wholly superseded by code.
- **archive** — Historical value (decisions, retired designs, ADRs);
  preserved under `docs-new/dev/archive/` rather than deleted.

## Working matrix

Populated incrementally. Each row's disposition becomes a separate commit
when executed.

Format per entry:

```
### docs/<path>

- Bucket(s):
- Stated audience(s):
- Apparent original audience:
- Accuracy:
- Disposition:
- Notes:
```

### docs/README.md
- Bucket(s): TBD
- Stated audience(s): TBD
- Apparent original audience: TBD
- Accuracy: TBD
- Disposition: TBD
- Notes: TBD

### docs/README.developer.md
- Bucket(s): TBD
- Stated audience(s): TBD
- Apparent original audience: TBD
- Accuracy: TBD (note: tactical refresh committed in `f05cc6d` on this
  branch may have changed the picture; re-read current state, not main)
- Disposition: TBD
- Notes: TBD

### docs/README.man1.md
### docs/README.man3.md
### docs/README.man4.md
### docs/README.man5.md
### docs/README.configuration.md
### docs/README.tests.md
### docs/CONTRIBUTING.md
### docs/CHANGELOG.md
### docs/WARP.md
### docs/kicad-best-practices.md
### docs/lcsc-provider.md
### docs/inventory-field-semantics.md
### docs/jbom-config-schema.yaml

### docs/tutorial/README.md
### docs/tutorial/README.context.md
### docs/tutorial/README.documentation.md
### docs/tutorial/README.implementation.md
### docs/tutorial/README.integration.md

### docs/dev/README.md

### docs/dev/architecture/README.md
### docs/dev/architecture/anti-patterns.md
### docs/dev/architecture/component-attribute-enrichment.md
### docs/dev/architecture/config-schema-audit.md
### docs/dev/architecture/design-patterns.md
### docs/dev/architecture/domain-centric-design.md
### docs/dev/architecture/eaglelib2kicad-adapter-requirements.md
### docs/dev/architecture/implementation-plan-250-251.md
### docs/dev/architecture/integration-patterns.md
### docs/dev/architecture/job-contracts.md
### docs/dev/architecture/layer-responsibilities.md
### docs/dev/architecture/project-centric-design.md
### docs/dev/architecture/testing.md
### docs/dev/architecture/why-jbom-new.md
### docs/dev/architecture/workflow-architecture.md
### docs/dev/architecture/adr/

### docs/dev/guides/README.md
### docs/dev/guides/DEVELOPER_GUIDE.md
### docs/dev/guides/USER_GUIDE.md
### docs/dev/guides/plugin-dev-setup.md

### docs/dev/requirements/README.md
### docs/dev/requirements/0-User-Scenarios.md
### docs/dev/requirements/1-Functional-Scenarios.md

### docs/dev/validation/
### docs/dev/workflow/
### docs/dev/development_notes/

## Cross-cutting findings

Captured as evidence accumulates. Findings that warrant code or scenario
changes become follow-up GitHub issues; findings that warrant charter
amendments come back here.

- **F-001**: (placeholder — first finding)

## Follow-up issues filed

(Empty — to be populated as audit progresses.)

## Axioms harvested from existing docs

Per the charter, axioms are one of the five reasons docs exist. The audit
collects axioms found in the existing tree here so the rewrite phase has
a single source. Each entry lists the axiom and the file(s) it was
extracted from.

- (Empty — to be populated.)

## Done criteria for this audit

- Every file under `docs/` has a row in the matrix with non-TBD
  disposition.
- Axioms section enumerates the axioms extracted from the tree.
- Findings section captures every code/scenario disagreement detected.
- Follow-up issues are filed for findings that require work outside
  the docs sweep.
- This document is itself reviewed against the charter (an audit of the
  audit) before being marked complete.
