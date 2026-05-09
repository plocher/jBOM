# SPIKE 2: jBOM Plugin UX Storyboard
Date: 2026-05-09
Related: #227, ADR 0007
Status: Design closed — ready for implementation

## Reference: FT's dialog (baseline)
Fabrication Toolkit's dialog exposes:
- Archive name template (`${TITLE}_${REVISION}`)
- Additional layers (comma-separated)
- Checkboxes: Plot all active layers, V-Cut (User.1), alt Edge-Cut (User.2),
  auto component translations, auto zone fill, exclude DNP, open browser,
  no backup

## jBOM's dialog — decided disposition of each FT control

| FT control | jBOM treatment | Rationale |
|---|---|---|
| Archive name template | **Show as read-only label** (expanded title+revision) | jBOM derives naming from title block per ADR 0006; no need to expose a template in v1 |
| Additional layers | **Drop** | Handled by fabricator `gerbers: layers:` stanza — power users edit YAML |
| Plot all active layers | **Drop** | Same — config-driven, not a dialog toggle |
| V-Cut (User.1) / alt Edge-Cut (User.2) | **Drop for now** | FT-specific gerber layer routing; not yet in jBOM |
| Apply automatic component translations | **Grayed-out placeholder** | Pending issue #249 (rotation/offset correction harvest from FT) |
| Apply automatic fill for all zones | **Keep** | `pcbnew.ZONE_FILLER` available in SWIG mode; cheap safety net |
| Exclude DNP from BOM | **Keep** | Maps to `include_dnp=False` in `FabricationRequest` |
| Open browser after generation | **Keep** | Opens `production/` in Finder/Explorer on success |
| Do not create backup files | **Invert to: Create backup archive** | BackupService is opt-out |

## jBOM additions beyond FT

1. **Fabricator dropdown** — dynamically populated from `get_available_fabricators()`.
   Persisted in `$repo-root/.jbom/jbom-options.json` (or `~/.jbom/jbom-options.json`
   if no git root found). POC default: `jlc`.

2. **Inventory file picker** — browse to `.csv`/`.xlsx`/`.numbers` inventory file.
   Persisted alongside fabricator in `jbom-options.json`. Empty = no enrichment (valid).

3. **[Config...]** button — opens a read-only panel showing the selected fabricator's
   effective settings (layers, drill config, BOM fields). Debugging aid.
   Placeholder text for MVP; full viewer is a future enhancement.

4. **SMD only** (placement) — maps to `FabricationRequest.smd_only`.

5. **Keep intermediate files (debug)** — maps to `FabricationRequest.debug`.
   Off by default.

## Dialog layout (MVP v0.0.1)

```
┌──────────────────────────────────────────────┐
│  jBOM Fabrication                            │
├──────────────────────────────────────────────┤
│  Archive:    MyProject_1.0                   │  ← read-only, from title block
│  Fabricator: [ JLC PCBA      ▼ ]  [Config…] │
│  Inventory:  [ path/to/inv.csv  ] [Browse…] │
├──────────────────────────────────────────────┤
│  [✓] SMD only (placement)                   │
│  [✓] Exclude DNP components                 │
│  [✓] Fill all zones before Gerbers          │
│  [✓] Create backup archive                  │
│  [✓] Open production folder when done       │
│  [ ] Apply placement corrections  (soon)    │  ← grayed, pending #249
│  [ ] Keep intermediate files (debug)        │
├──────────────────────────────────────────────┤
│  [       Generate       ]  [    Cancel     ] │
└──────────────────────────────────────────────┘
```

## Generate flow

When **Generate** is pressed the dialog morphs to a progress view:

```
┌──────────────────────────────────────────────┐
│  jBOM Fabrication — Generating...            │
├──────────────────────────────────────────────┤
│  BOM      [████████████████████████] ✓       │
│  CPL      [████████████████████████] ✓       │
│  Gerbers  [████████████░░░░░░░░░░░░] ...     │
│  Backup   [░░░░░░░░░░░░░░░░░░░░░░░░]         │
└──────────────────────────────────────────────┘
```

**Behavior after completion:**
- **Success**: dialog closes automatically, Finder/Explorer opens on `production/`
- **Error**: dialog stays up, error diagnostics visible (from `result.diagnostics`)
- **Debug mode on**: dialog stays up regardless of outcome

## Persistence

Plugin preferences are written/read via jBOM's existing config file mechanism.
Write target priority:
1. `$repo-root/.jbom/jbom-options.json` — preferred (git-tracked, shared across project dir)
2. `~/.jbom/jbom-options.json` — fallback if no git root found

Fields persisted: `fabricator`, `inventory_path`.
Session-only (not persisted): skip toggles, debug mode.

## Origin selector — NOT included

`jbom pos --origin` is a CLI feature for headless workflows. FT does not expose
it in the dialog (it always uses the aux origin if set). The plugin follows suit:
origin is resolved automatically from the board settings.

## Open issues created from this spike

- **#249** — harvest FT `transformations.csv` rotation/offset DB into jBOM
- **#250** — config file naming convention cleanup (`jbom`-namespaced files/dirs)

## Not in scope for MVP

- Revision/title block editing (increment revision, etc.)
- Fab config lifecycle manager (create/edit/clone YAML) — R/O viewer placeholder is sufficient
- Multi-panel / array support
- V-Cut / alt Edge-Cut layer options (requires FT harvest work separate from #249)
