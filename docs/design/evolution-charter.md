# jBOM Evolution Charter

**Status:** Accepted — 2026-10-16
**Job:** Intent + axioms + negative space for the next medium-term arc
**Not:** a release plan, a sprint board, or a substitute for ADRs

**Grill:** Q1–Q7 locked — see §9.

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
| Matcher (passives + growing actives) | **Transitional** | Extend under ADR 0003; avoid one-off category rules; corpus gates search/ranking policy only (Q4) |
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

### Track 0 — Correctness and conveyor hygiene (ongoing, curated capacity)

**Capacity rule (Q3):** spend the “~20%” on *curation that unlocks agent
progress*, not on open-ended human debugging. If an item can be human-shaped
once (repro, acceptance, boundaries) and handed to an agent or loosely coupled
sub-agent for closure, it belongs here and often simplifies later lifts. If it
cannot be made agent-ready without a design rabbit hole, park it — those become
momentum sinks that destroy Tracks 1–2.

- CPL/FT parity bugs (#395/#398 — likely duplicate): curate then delegate if sharp.
- Ready-for-agent leftovers (#372).
- Thin cost field path (Q5): LCSC/SPN → JLCPCB catalog price at a bulk break
  (e.g. qty 20 or 50 — not the inflated qty-1 price) as an optional BOM
  `--fields` value — good-enough, not KiCost-in-core. Spike/close #381 against
  that bar.
- Label/milestone hygiene once Step 4 runs.

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
2. Promote realization under ADR 0018 **under the current `promote` name**:
   export-in-config (#327), provider-first enrichment (#329), fail-fast
   overlap (#324), vocab-in-defaults (#328). End-state name is
   `inventory merge`; do not rename until internals are real (Q2).
3. Absorb promote into `inventory merge` per ratified sentences (#390) when
   Track 1 grammar + rollout (#401) say switch — not before.
4. Curation power: cross-supplier alternatives (#330), freshness/lifecycle
   stamp (#331).
5. Finish ADR 0008 remnant purge when it collides with the above (#326), not
   as a pure archaeology project.
6. Datasheet residual: group-fill blank URLs in output (#374).

Parked, not cancelled: profile hermetic search-path design (#369).

### Track 3 — Search and match framework (secondary; deliberately deprioritized)

Search is hard. It may need solutions *outside* jBOM (other engines, other
products, thinner integration). Doing search-first is a distraction from the
inventory lifecycle bet. This track stays alive so work does not vanish, but
it does not win calendar fights against Tracks 1–2.

1. Close or rewrite zombie umbrella #195 (children done).
2. Land or supersede ADR 0003 realization via #204 (framework) with
   measurement via #181 (corpus) — when capacity allows, not as a pioneer.
3. Full KiCost absorption stays out of scope. Cost for *this* arc is the thin
   Track 0 path (Q5), not a search-engine project. #381 closes by confirming
   or rejecting that bar — not by importing KiCost.
4. Category expansion follows framework + corpus, not the reverse.
5. Prefer external or shared solutions over deepening one-off search cleverness
   inside jBOM when the problem is general catalog retrieval.

### Track 4 — Horizon and adapters (capacity-boxed)

- KiCad v10 variants (#382): spike against project-centric + generator
  sentences; schedule when KiCad 10 is real for this user base.
- EagleLib2KiCad (#214): keep service-surface-first (ADR 0004/0016); do not
  pull conversion into jBOM core.
- External publish/cost tools: prefer compose-with over absorb-into.
- **Shared Python KiCad API package (ecosystem horizon).** jBOM's services
  layer is already a KiCad API in disguise. The same head-space is shared with
  kproj, kDoctor, FieldUnit (`~/Dropbox/Arduino/libraries/FieldUnit`), and
  FieldUnit-Subdivision (`~/Dropbox/workspace/FieldUnit-Subdivision`). At some
  point those services should coalesce into a shared package consumed by all
  of them. This arc does **not** start that extraction: keep service boundaries
  clean (ADR 0013/0005) so extraction stays possible; open a dedicated map
  only when two or more sister tools are blocked on duplication. Until then,
  treat cross-tool API dreams as horizon, not Track 2 scope.

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
- Absorbing KiCost (or any full multi-supplier cost engine) into jBOM core.
  Thin bulk-break price-as-BOM-field (LCSC/JLC, qty 20 or 50 class) is allowed
  (Q5); that is not KiCost.
- Absorbing Eagle conversion or kproj publish into jBOM core.
- Per-project PDF datasheet trees (library + deep links won).
- Reopening the COMPONENT/ITEM dual RowType model.
- Multi-supplier composition inside `promote` (stays inventory-side).
- Extracting the shared KiCad Python API package during this inventory/CLI
  arc (keep seams clean; extract later under its own map).
- Making search “solved inside jBOM” a gate for inventory lifecycle work.

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

## 9. Grill log and remaining questions

### Locked

1. **Primary bet (Q1) — locked 2026-10-16.** Track ranking stands:
   Track 1 (CLI gate) → Track 2 (inventory lifecycle, primary product bet) →
   Track 3 (search, secondary). Search is hard and may need solutions outside
   jBOM; doing it first would be completely distracting.
2. **Promote timing (Q2) — locked 2026-10-16.** Option A: internals first,
   rename later. Deepen #327/#329/#324/#328 under today’s `promote`; absorb
   into `inventory merge` only when Track 1 + #401 switch. No alias shim.
   Step 4 issues should say “merge intake (today: `promote`)” where useful.
3. **Capacity split (Q3) — locked 2026-10-16.** ~20% Track 0 only when spent
   on *human curation that unlocks agent/sub-agent closure*. Prefer items that
   simplify later loosely coupled orchestration. If an item cannot be shaped
   for handoff without a design sink, park it — do not let it eat Tracks 1–2.
4. **Corpus ownership (Q4) — locked 2026-10-16.** #181 gates search-provider
   and ranking-policy work, not every matcher or BOM-field change.
5. **Cost (Q5) — locked 2026-10-16.** Good-enough path: resolve price from
   LCSC/JLCPCB identity at a **bulk break quantity** (qty 20 or 50 class — not
   qty-1, which is often ~2× bulk) and expose via BOM `--fields` (e.g. `cost`).
   Delegatable Track 0 / small feature — not KiCost-in-core. Close or re-scope
   #381 against that bar. Full multi-supplier cost engine stays negative space.
6. **Charter home (Q6) — locked 2026-10-16.** Lives at
   `docs/design/evolution-charter.md`. On Accept, status bump; graduate binding
   axioms to ADR/CONTEXT only as needed. Track list stays mutable design.
7. **Shared KiCad API package (Q7) — locked 2026-10-16.** Horizon-only this
   arc; heads-up that parallel sister-tool work exists. Forcing function to open
   a map: two or more tools blocked on duplication. Keep service seams clean.

### Still open

- None. Charter **Accepted** 2026-10-16. Next: Step 3 reshape backlog against
  tracks; Step 4 rewrite GitHub issues/milestones/labels.

---

## 10. Revision log

- 2026-10-16 — DRAFT opened from backlog inventory (31 open issues) and
  existing ADRs / maps #385 #342 / ADR 0018. ADRs 0003, 0004, 0008, 0009,
  0010 marked Accepted to match practice.
- 2026-10-16 — Q1 locked (inventory over search). Track 3 deprioritized with
  external-solution bias. Shared Python KiCad API package recorded as
  ecosystem horizon (Track 4 / negative space), not this arc's extraction work.
  §3 axioms accepted as solid.
- 2026-10-16 — Q2 locked: promote internals before `inventory merge` rename.
- 2026-10-16 — Q3–Q7 locked: curation-for-agents capacity rule; corpus scope;
  thin LCSC/JLC bulk-break cost-as-BOM-field; charter home; shared API horizon
  heads-up. Initial grill complete.
- 2026-10-16 — **Accepted.**
