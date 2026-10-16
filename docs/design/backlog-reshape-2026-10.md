# Backlog reshape — 2026-10

**Status:** Step 4 executed (2026-10-16)
**Charter:** [`evolution-charter.md`](evolution-charter.md) (Accepted 2026-10-16)
**Docs PR:** https://github.com/plocher/jBOM/pull/410
**Step 3 locks:** close #342; reframe #381 in place; use `docs-debt` milestone; no Track 2 drops.

Legend for **Action**:

| Action | Meaning |
|--------|---------|
| `close-done` | Work complete or parent exhausted; close with pointer |
| `close-dup` | Duplicate; close pointing at survivor |
| `keep-map` | Active wayfinder map/ticket; leave body, set milestone |
| `reframe` | Rewrite title/body/labels to match charter; stay open |
| `curate-agent` | Human-shape once → `ready-for-agent` (Track 0 capital) |
| `park` | Stay open but deprioritized; milestone + short park note |
| `close-park` | Horizon without near forcing function; close or wontfix with revive condition |

Milestones to create in Step 4 (names from charter §6):

- `cli-concept-model`
- `inventory-lifecycle`
- `search-framework`
- `correctness-hygiene`
- `horizon`
- `docs-debt` (Track 5; optional sixth if five is too coarse)

---

## By track

### Track 0 — correctness / curated agent handoff

| Issue | Action | Notes |
|------:|--------|-------|
| 395 | `close-dup` | Same CPL/FT failure as #398; keep #398 (has local-vs-CI signal) |
| 398 | `curate-agent` | Survivor bug. Shape: confirm still fails on main, note env delta vs CI, acceptance = test green locally+CI. Milestone `correctness-hygiene`. Labels: `bug`, `ready-for-agent` after brief |
| 372 | `keep` + milestone | Already `ready-for-agent`. Milestone `correctness-hygiene`. No rewrite needed |
| 381 | `reframe` | Retitle/body: thin LCSC/JLC **bulk-break** price as optional BOM `--fields` (qty 20/50 class), not KiCost import. Close KiCost-eval framing. Then `curate-agent` or small ready ticket. Milestone `correctness-hygiene` |
| *(new)* | `create` in Step 4 only if #381 is cleaner closed | Optional: `feat(bom): optional cost field from LCSC/JLC bulk-break price` — only if reframe of #381 is messier than a fresh issue |

### Track 1 — CLI concept model (gate)

| Issue | Action | Notes |
|------:|--------|-------|
| 385 | `keep-map` | Active map. Milestone `cli-concept-model`. Add charter pointer comment in Step 4 |
| 389 | `keep-map` | Decorator ladder. Same milestone |
| 391 | `keep-map` | Option taxonomy |
| 392 | `keep-map` | Mock help screens |
| 393 | `keep-map` | Style-guide axioms |
| 400 | `keep-map` | Docs rewrite structure |
| 401 | `keep-map` | kproj/kDoctor rollout — gates promote→`inventory merge` rename (Q2) |

### Track 2 — inventory lifecycle (primary bet)

| Issue | Action | Notes |
|------:|--------|-------|
| 307 | `reframe` | **Product feature**, not `documentation`. Retitle clear multi-file inventory merge. Labels: `enhancement`, drop misleading docs-only vibe. Milestone `inventory-lifecycle`. Strong early Track 2 candidate |
| 324 | `reframe` | Fail-fast overlap under current `promote` (merge intake). Tag “today: promote”. Milestone `inventory-lifecycle` |
| 326 | `park` lightly | ADR 0008 remnant purge — do when it collides with promote/config work, not archaeology-first. Milestone `inventory-lifecycle` or `docs-debt` |
| 327 | `reframe` | `supplier.export:` — merge intake internals (today: promote). Milestone `inventory-lifecycle` |
| 328 | `reframe` | Vocab → defaults. Same |
| 329 | `reframe` | Provider-first enrichment. Same; pairs with #327 |
| 330 | `reframe` | Cross-supplier alts — after merge intake solid. Milestone `inventory-lifecycle`; sequence after 327/329 |
| 331 | `reframe` | Freshness/lifecycle stamp — same sequencing note as #330 |
| 374 | `curate-agent` | Datasheet group-fill in BOM/PARTS output. Residual of map #342. Labels: `enhancement`, `datasheet-library`, then ready after brief. Milestone `inventory-lifecycle` or `correctness-hygiene` (lean inventory) |
| 369 | `park` | Profile hermetic search path — explicit park; not blocking. Milestone `horizon` or leave unlabeled park note |

### Track 3 — search (deprioritized)

| Issue | Action | Notes |
|------:|--------|-------|
| 195 | `close-done` | Children #197/#199/#200/#201 done. Close omnibus; point at #204/#181 as remaining search spine |
| 181 | `park` | Corpus — gates search/ranking only (Q4). Milestone `search-framework`. No pioneer work |
| 204 | `park` | Heuristic framework — ADR 0003 accepted; realization when capacity allows. Milestone `search-framework` |

### Track 4 — horizon

| Issue | Action | Notes |
|------:|--------|-------|
| 214 | `park` | EagleLib2KiCad adapter reqs. Milestone `horizon`. ADR 0004/0016 stand |
| 382 | `park` | KiCad v10 variants spike. Milestone `horizon`. Revive when K10 is real for this user base |
| 342 | `close-done` or `keep` as hub | Planning complete; impl #355–#359 closed. Prefer **close map** with pointer to residual #374 + SPCoast #1 + kproj tickets — or leave open as coordination hub with comment “planning done”. **Recommend close-done** so open count reflects real work |

### Track 5 — docs / debt

| Issue | Action | Notes |
|------:|--------|-------|
| 269 | `park` | Pydantic schema reference — after CLI/config surface settles. Milestone `docs-debt` |
| 302 | `park` | BDD fault paths F-006. Milestone `docs-debt` |
| 305 | `park` | CHANGELOG generation F-013. Milestone `docs-debt` |
| 313 | `park` / light `curate-agent` | RowType purge — good agent chore if brief is mechanical. Milestone `docs-debt`. Prefer curate if docs+code grep is bounded |

---

## Close / merge summary (Step 4 batch)

**Close first (low risk):**

1. #195 — omnibus done
2. #395 — dup of #398
3. #342 — map destination met (if maintainer agrees hub not needed)

**Curate-for-agent next (Track 0 capital):**

1. #398 — CPL/FT parity
2. #372 — already ready (just milestone)
3. #374 — datasheet group-fill
4. #381 — reframe to thin bulk-break cost, then ready
5. #313 — if mechanical enough

**Reframe in place (Track 2 spine):**

#307, #324, #327, #328, #329, #330, #331 — shared blurb:

> Charter: [`docs/design/evolution-charter.md`](../design/evolution-charter.md).
> Track: inventory-lifecycle.
> End-state CLI: `inventory merge` absorbs promote; **this issue implements behavior under today’s `promote` name** until Track 1 + #401 switch (Q2).

**Do not touch bodies of open #385 children** beyond milestone + optional charter one-liner — map is mid-flight.

---

## Suggested Step 4 order of operations

1. Create milestones (and `docs-debt` if used).
2. Close #195, #395, (#342).
3. Milestone-tag all remaining opens per tables above.
4. Reframe Track 2 titles/labels (#307 first — wrong labels today).
5. Reframe #381 → cost field story.
6. Write agent briefs on #398, #374, (#313), (#381).
7. Pin or comment on #385 / charter link from a single “evolution” tracking comment — optional; charter in-repo is source of truth.
8. Open PR for docs branch (`evolution-charter` + this file + ADR status).

---

## Counts after reshape (approx)

| Disposition | ~Count |
|-------------|-------:|
| Close | 3 |
| Active CLI map tickets | 7 (#385 + 6 children) |
| Track 2 open spine | ~9 |
| Track 3 parked | 2 |
| Horizon parked | 2–3 |
| Docs-debt parked | 3–4 |
| Track 0 ready/curate | 3–5 |
| **Open remaining** | **~25** (down from 31, healthier shape) |

---

## Step 3 locks (2026-10-16)

1. **#342** — close map as done (hub not required).
2. **#381** — reframe in place to thin bulk-break cost field.
3. **`docs-debt` milestone** — yes.
4. **Track 2 drops** — none; keep full spine.

Step 4 executed under these locks:

- Milestones created: `cli-concept-model`, `inventory-lifecycle`, `search-framework`, `correctness-hygiene`, `horizon`, `docs-debt`
- Closed: #195 (done), #395 (dup of #398), #342 (map done)
- Track 2 reframed + charter comments; #307 product labels fixed
- #381 reframed to bulk-break cost + agent brief + `ready-for-agent`
- Agent briefs: #398, #374, #313; notes on #372, #385
- Park comments: search/horizon/docs-debt issues
