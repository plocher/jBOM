# jBOM Evolution Charter

**Status:** DRAFT — working notes for backlog grooming (2026-10)
**Job:** Intent + axioms + negative space for the next medium-term arc
**Not:** a release plan, a sprint board, or a substitute for ADRs

When this charter and an issue disagree, stop and reconcile deliberately.
When this charter and an Accepted ADR disagree, the ADR wins until amended.

---

## 1. Destination (medium term)

jBOM remains the inventory-aware KiCad manufacturing-handoff tool:

- KiCad holds electronic/mechanical design intent only.
- Supply-chain truth lives in a curated inventory (and its datasheet library).
- Fabricator and supplier knowledge lives in configuration profiles, not code.
- Generators (`bom`, `parts`, `pos`, `gerbers`, `fab`) produce target-specific
  artifacts by matching design → inventory under a chosen fabricator profile.

**Medium-term success looks like:**

1. The CLI surface matches a small set of ratified action sentences, with
   shared option grammar and an axiom-based style guide (map #385).
2. Inventory has a real lifecycle — create, merge (including promote), audit,
   freshness/alternatives — not only “read a CSV at BOM time.”
3. Search/match heuristics grow under one framework (ADR 0003), measured by a
   stable corpus, without per-category ad hoc sprawl.
4. Mature surfaces (bom/parts/fab/pos) stay correct and quiet: regressions are
   fixed, tech-debt is burned when it blocks the above, not as a hobby.
5. Horizon work (KiCad variants, external adapters, cost tools) is spiked and
   either scheduled or explicitly parked — not left as unlabeled open issues.

---

## 2. Product spine (what jBOM is)

```text
Design source (KiCad project)
        │  read-only from jbom's point of view
        ▼
   match / enrich
        │
Inventory (canonical Items + datasheet library refs)
        │  curated by humans; tooling proposes and lints
        ▼
Fabricator profile (ordered suppliers, field presets, transforms)
        │
Generators → BOM / PARTS / POS / gerbers / fab package
```

**Two verbs of work, not one product:**

| Mode | User intent | Primary commands (target shape) |
|------|-------------|----------------------------------|
| **Generate** | “Make the handoff artifacts for this board.” | `bom`, `parts`, `pos`, `gerbers`, `fab` |
| **Curate** | “Grow and keep the inventory healthy.” | `inventory create\|merge\|audit`, `search` |

Promote is a merge intake path (per-invoice supplier export → canonical rows),
not a second product. Cross-supplier discovery and stock/lifecycle stamping
belong to inventory curation (ADR 0018).

Datasheet library tooling is inventory-adjacent curation (admit/audit/check-urls),
with kproj as publish consumer — not a third product line inside jBOM.

---

## 3. Axioms (proposed — under grill)

Short proof statements. Detail and history live in ADRs and maps.

### 3.1 Domain boundary

1. **Design/source split.** KiCad files hold design intent only. Supply-chain
   data lives in inventory and profiles.
2. **Read-only design source.** The `jbom` command never mutates KiCad design
   source. Repair/normalize of design properties is kDoctor (or `jbom-exiled`
   until adopted).
3. **Config over code.** Fabricator and supplier knowledge is declarative
   profile data (ADR 0008). A new supplier is a config drop-in first.
4. **Project is the unit.** Commands resolve a KiCad project (ADR 0011), not a
   loose bag of files, except where an explicit file is the point of the tool.

### 3.2 Command grammar (from map #385 — ratified core)

5. **Action sentence.** Every command reads as a user action
   (`generate bom from project`, `merge inventory from supplier export`, …).
   A sentence that will not parse means the wrong verb or a misplaced feature.
6. **Diagnosis rides the generator.** Failures and guesses announce themselves
   on the command the user already ran. Standalone “inspect everything” is not
   the default shape; dry-run + verbosity is the X-ray.
7. **One concept per command family.** Invoice ETL ≠ inventory curation ≠
   design repair. Adjacent work gets the adjacent command, not a flag pile.

### 3.3 Inventory and matching

8. **Human writes inventory; tooling proposes.** Full-sheet paste / explicit
   apply gates beat silent rewrite of the user’s catalog.
9. **Item is the row.** Component→Item is 1:many ranked candidates. Abandoned
   RowType COMPONENT/ITEM dual-model stays gone (#313).
10. **Match under fabricator.** Selection and field shape follow fabricator
    profile + Distributor semantics, not filename tricks (ADR 0001, BDD #11).
11. **Provider data before regex.** Catalog parametric attributes beat
    description scraping; regex is fallback only (ADR 0018 D1).

### 3.4 Evolution and triage

12. **Mature surfaces defend; immature surfaces design.** Bom/parts/fab/pos
    default to fix-forward and small PRs. Inventory lifecycle and search
    framework default to ADR/map → ready issue → implement.
13. **Wayfind fog; ticket sharpness.** If the question is not yet sharp, chart
    or grill. If it is sharp and bounded, ordinary issue. If it is done or
    rejected, close — do not keep coordinator zombies.
14. **Simple correctness over clever coverage.** Prefer one obvious path that
    is right under generic + named profiles over multi-mode abstractions that
    only tests exercise.
15. **Horizon work is explicit.** Spikes end in a decision: schedule, park with
    rationale, or wontfix. Open spikes without a next decision are backlog
    debt.

---

## 4. Maturity posture (by surface)

| Surface | Posture | Default work shape |
|---------|---------|--------------------|
| bom / parts / pos / gerbers / fab | **Mature** | Bugs, parity, small ergonomics; no redesign without a forcing function |
| Matcher (passives + growing actives) | **Transitional** | Extend under ADR 0003; corpus-gated; avoid one-off category rules |
| Datasheet library loop | **Mostly shipped** | Residual output/UX; curation is data work (SPCoast-inventory) |
| CLI grammar / style guide | **In design** | Finish map #385 before large CLI renames land in bulk |
| Inventory lifecycle (create/merge/audit/freshness/alts) | **Immature** | Realize ADR 0018; multi-file merge; promote→merge absorption |
| Search supplier breadth | **Partial** | Parity slices done; corpus + heuristic framework remain |
| Config unification (0008–0010) | **Accepted, remnants** | Burn legacy shims when they block; do not reopen schema |
| KiCad variants / KiCost / EagleLib adapters | **Horizon** | Spike → decision; no silent open forever |

---

## 5. Medium-term tracks (ordering proposal)

Tracks are parallelizable only where noted. Within a track, prefer finishing
the design gate before a pile of implementation issues.

### Track 0 — Correctness and conveyor hygiene (ongoing, small capacity)

- CPL/FT parity bugs (#395/#398 — likely duplicate).
- Ready-for-agent leftovers (#372).
- Label/milestone hygiene once Step 4 runs.
- Do not let this track consume the whole calendar.

### Track 1 — Finish the CLI concept model (gate)

**Why first among designs:** almost every immature feature wants a flag or
subcommand. Without ratified grammar, inventory and search work re-teaches
inconsistency.

- Remaining #385 tickets: decorator ladder, option taxonomy, mock help,
  style-guide axioms, docs rewrite structure, kproj/kDoctor rollout order.
- Output: ADRs + style-guide axioms + implementation issues (not the map).

### Track 2 — Inventory lifecycle maturity (primary product bet)

**North star:** inventory is a living curated catalog, not only a BOM input.

Suggested sequence (adjust under grill):

1. Multi-file inventory merge in BOMWorkflow / inventory merge (#307) — user
   already thinks this works.
2. Promote realization under ADR 0018: export-in-config (#327), provider-first
   enrichment (#329), fail-fast overlap (#324), vocab-in-defaults (#328).
3. Absorb promote into `inventory merge` per ratified sentences (#390) once
   CLI track allows.
4. Curation power: cross-supplier alternatives (#330), freshness/lifecycle
   stamp (#331).
5. Finish ADR 0008 remnant purge when it collides with the above (#326), not
   as a pure archaeology project.
6. Datasheet residual: group-fill blank URLs in output (#374).

Parked, not cancelled: profile hermetic search-path design (#369).

### Track 3 — Search and match framework (secondary product bet)

1. Close or rewrite zombie umbrella #195 (children done).
2. Land or supersede ADR 0003 realization via #204 (framework) with
   measurement via #181 (corpus).
3. KiCost spike (#381) only as input to “do we integrate cost, or stay
   handoff-only?” — decision required.
4. Category expansion follows framework + corpus, not the reverse.

### Track 4 — Horizon and adapters (capacity-boxed)

- KiCad v10 variants (#382): spike against project-centric + generator
  sentences; schedule when KiCad 10 is real for this user base.
- EagleLib2KiCad (#214): keep service-surface-first (ADR 0004/0016); do not
  pull conversion into jBOM core.
- External publish/cost tools: prefer compose-with over absorb-into.

### Track 5 — Docs and debt that unlock the above

- Schema reference generation (#269) after config surface stabilizes post-CLI.
- BDD fault paths (#302), CHANGELOG generation (#305), RowType purge (#313):
  schedule when they block trust or onboarding, else park with date.

---

## 6. Triage rules (for Step 3–4)

Apply one category and one state label (see `docs/agents/triage-labels.md`).

| If the issue… | Then… |
|---------------|--------|
| Is a closed child’s coordinator with no remaining work | Close as done; link children |
| Duplicates another open bug | Close as duplicate; keep the better repro |
| Restates an Accepted ADR with no new decision | Convert to implementation issue or close |
| Needs a product decision before code | Grill / wayfinder ticket; not `ready-for-agent` |
| Is sharp, bounded, testable, ADR-aligned | `ready-for-agent` or `ready-for-human` |
| Is horizon without a forcing function | Park milestone or `wontfix` with rationale |
| Touches only mature generators | Prefer small fix PR; avoid bundling with Track 2/3 |
| Mutates KiCad design source | Reject from `jbom`; route to kDoctor / exile |

**Milestones (proposed names for Step 4 — not created yet):**

- `cli-concept-model`
- `inventory-lifecycle`
- `search-framework`
- `correctness-hygiene`
- `horizon`

Issues may sit in at most one primary milestone. Wayfinder maps stay maps
until destination is met, then close.

---

## 7. Negative space (deliberate non-goals this arc)

- Becoming a full PLM, purchasing system, or multi-user inventory server.
- Silent auto-rewrite of the user’s inventory file as a default path.
- Compat shims / aliases for CLI renames (in-house retool is acceptable).
- Absorbing KiCost, Eagle conversion, or kproj publish into jBOM core.
- Per-project PDF datasheet trees (library + deep links won).
- Reopening the COMPONENT/ITEM dual RowType model.
- Multi-supplier composition inside `promote` (stays inventory-side).

---

## 8. Relationship to other docs

| Doc | Role vs this charter |
|-----|----------------------|
| `CONTEXT.md` | Ubiquitous language; extend when Track 2/3 terms stabilize |
| `docs/architecture/adr/*` | Binding decisions; charter must not contradict Accepted ADRs |
| Wayfinder maps (#385, #342) | Active design vehicles inside tracks |
| `docs/design/bdd-axioms.md` | Test-suite invariants; orthogonal but aligned |
| GitHub issues | Worklog; rewritten in Step 4 to match this charter |

---

## 9. Open questions (grill list)

Resolve these before treating the charter as Accepted:

1. **Primary bet:** Is Track 2 (inventory lifecycle) correctly ranked above
   Track 3 (search framework) for the next 1–2 quarters?
2. **Promote timing:** Finish promote internals (#327/#329) before CLI rename
   to `inventory merge`, or rename shell first and keep internals behind it?
3. **Capacity split:** What steady fraction of effort stays on Track 0
   (hygiene) vs design tracks while #385 is unfinished?
4. **Corpus ownership:** Is #181 a gate for all matcher changes, or only for
   search-provider work?
5. **KiCost:** Are we open to “cost as a report command,” or is cost forever
   outside jBOM?
6. **Charter home:** Keep as `docs/design/evolution-charter.md` (mutable
   design) and graduate stable axioms into ADR(s) / CONTEXT when accepted?

---

## 10. Revision log

- 2026-10-16 — DRAFT opened from backlog inventory (31 open issues) and
  existing ADRs / maps #385 #342 / ADR 0018. ADRs 0003, 0004, 0008, 0009,
  0010 marked Accepted to match practice.
