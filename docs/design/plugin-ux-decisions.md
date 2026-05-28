# Plugin UX Design Decisions

Status: Current — reflects `src/jbom/plugin/dialog.py` as of Wave B.2 (2026-05)
Related: [ADR 0005](../architecture/adr/0005-jbom-evolutionary-supersession-cli-plugin-session-model.md),
[ADR 0007](../architecture/adr/0007-plugin-packaging-and-distribution.md), #227

This document records the design decisions made in implementing the
`JBOMFabricationDialog`. It supersedes the 2026-05-09 storyboard
(`plugin_ux_storyboard.md`) which drove the initial implementation.
The storyboard was the design; this document is the post-implementation
rationale. Where the two disagree, the code wins per the documentation
charter's content-freshness rule.

## Architectural context

[ADR 0005](../architecture/adr/0005-jbom-evolutionary-supersession-cli-plugin-session-model.md)
commits jBOM to an adapter-neutral core with two peer adapters: CLI and
KiCad plugin. The plugin adapter acquires session context from KiCad,
maps UI settings to workflow requests, drives background execution, and
renders progress — without embedding orchestration policy of its own.
[ADR 0007](../architecture/adr/0007-plugin-packaging-and-distribution.md)
governs how the plugin reaches the user (PCM archive with vendored
pure-Python dependencies; PyPI channel for the CLI is unchanged).

The design decisions below are all at the adapter layer. None of them
imply changes to the service contracts.

## Plugin icons and PCM packaging

jBOM now ships two distinct icon surfaces because KiCad treats them
separately:

- **ActionPlugin toolbar icon (Pcbnew runtime):** the SWIG ActionPlugin docs
  require `icon_file_name` to be an absolute PNG path and recommend 24×24.
  They also support an optional `dark_icon_file_name` override for dark
  themes. jBOM uses:
  - `assets/icons/pcb-fabrication-tool-light-24.png`
  - `assets/icons/pcb-fabrication-tool-dark-24.png`
  wired from `plugin.py` via absolute paths computed from `__file__`.
- **PCM package icon (plugin manager listing):** KiCad addon packaging docs
  define `resources/icon.png` as the optional 64×64 icon shown in Plugin and
  Content Manager. jBOM includes this as `resources/icon.png` in the archive.

These are intentionally independent: the 24×24 toolbar icon is consumed by
Pcbnew's ActionPlugin UI, while PCM uses only `resources/icon.png`.

Creation/update checklist for future icon refreshes:

1. Export/update both toolbar icon variants at 24×24 (`light` + `dark`) in
   `src/jbom/plugin/assets/icons/`.
2. Export/update PCM icon at 64×64 in `resources/icon.png`.
3. Build a local package with `python scripts/build_pcm_package.py` and verify
   archive paths/sizes:
   - `plugins/assets/icons/pcb-fabrication-tool-light-24.png` (24×24)
   - `plugins/assets/icons/pcb-fabrication-tool-dark-24.png` (24×24)
   - `resources/icon.png` (64×64)
4. Validate with unit + feature packaging tests before release.

References:
- KiCad Addon packaging guide:
  <https://dev-docs.kicad.org/en/addons/index.html>
- KiCad PCB Python bindings (ActionPlugin icon fields and sizing guidance):
  <https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/index.html>

## Two-panel dialog structure

The dialog (`JBOMFabricationDialog`) presents two panels that swap on
Generate. The input panel holds configuration controls and the Generate /
Cancel buttons. The progress panel shows four `wx.Gauge` widgets (BOM,
CPL, Gerbers, Backup), a hidden diagnostics text area that appears on
error, and a Cancel button that relabels to Close on completion.

Swapping panels rather than closing and reopening a dialog keeps the
user in a single window throughout the workflow. The progress panel's
Cancel button signals a `threading.Event` that the background worker
checks between steps; it does not kill the thread mid-step, which would
leave the board in an inconsistent state.

## Modeless dialog: `Show()` instead of `ShowModal()`

This is the most consequential dialog-level architectural decision and
the one most likely to surprise a maintainer unfamiliar with KiCad's
ActionPlugin model.

`ShowModal()` blocks the call stack until the dialog returns. Inside a
KiCad ActionPlugin, that means `plugin.Run()` does not return until the
dialog closes. KiCad does not re-enable the toolbar button for an
ActionPlugin until `Run()` returns. The result is that a modal dialog
leaves the toolbar button permanently disabled for the lifetime of the
dialog — the user cannot reopen the plugin if they accidentally dismiss
it.

`wx.Dialog.Show()` (modeless) returns immediately. `Run()` returns,
KiCad re-enables the button, and the dialog owns its own lifecycle until
`self.Destroy()` is called. The `EVT_CLOSE` handler is overridden to
call `Destroy()` directly, because `wx.Dialog`'s default `EVT_CLOSE`
behaviour hides rather than destroys.

Related: the dialog's parent is always `None`. KiCad's C++ dialog
tracking watches the `wxDialog` C++ object and re-evaluates toolbar
state when that object is destroyed. A `None` parent avoids any
window-hierarchy interference from the KiCad main frame. The
`_refresh_and_destroy()` teardown method always calls `pcbnew.Refresh()`
before `self.Destroy()`, mirroring Fabrication Toolkit's `updateDisplay`
pattern — the `Refresh()` posts an event to KiCad's wx loop so that
`UpdateUI` handlers run and button state reflects the closed dialog.

## Fabrication orchestration: no `FabricationWorkflow`

The plugin's background worker directly sequences four service calls:

1. `BOMWorkflow().run()` → `BOMWriter` → `production/jbom.csv`
2. `POSWorkflow().run()` → `POSWriter` → `production/cpl.csv`
3. `PcbnewGerberGenerator(board).generate()` → `GerberPackager` → `production/{stem}.zip`
4. `BackupService().backup()` → `production/backups/{stem}_{timestamp}.zip`

`FabricationWorkflow` is intentionally not used from the plugin for two
reasons. First, its `kicad-cli` subprocess path hangs inside KiCad's
embedded Python interpreter — KiCad holds a lock that the subprocess
cannot acquire. Second, `FabricationWorkflow`'s internal backup runs
before plugin-generated Gerbers are available, so the backup archive
would be incomplete. The plugin's in-process `PcbnewGerberGenerator`
uses KiCad's `PLOT_CONTROLLER` API directly (no subprocess) and
produces Gerbers before the backup step. The CLI path via
`FabricationWorkflow` and `kicad-cli` is unchanged.

After the Gerber step, the board file is auto-saved. `PLOT_CONTROLLER.SetOutputDirectory()`
and related setters write into the board's persisted plot settings,
dirtying the board even though no design data changed. Saving at this
point keeps the board file in sync with the generated Gerbers and clears
the dirty flag — consistent with the zone-fill auto-save rationale
described below.

## Input panel

### Archive name: editable template with live preview

The storyboard specified the archive-name field as a read-only label
showing the expanded title-block value. The implementation made it an
editable `wx.TextCtrl` instead. This is the design choice (F-009
resolved); the storyboard was naive.

The rationale: title blocks vary enough between boards that a fixed
expansion is not always what the user wants as their Gerber archive stem.
The fabricator's upload portal may have naming requirements. An editable
template gives the user control without exposing the raw title-block
token syntax as the default UX — the template defaults to
`${TITLE}_${REVISION}`, and a live preview row below the field shows the
expanded value in italic text as the user types.

Template expansion uses `expand_text_variables()` from
`jbom.services.text_variable_expander`, driven by title-block metadata
pre-read from disk in `__init__`. The metadata is cached so that
`board.GetTitleBlock()` SWIG reads are completely avoided in the
`EVT_TEXT` handler. KiCad 10's ActionPlugin framework marks the board
modified before `Run()` is called; additional SWIG reads would compound
the dirty-flag problem. Standard title-block tokens are supported;
custom `.kicad_pro` project variables are not (acceptable trade-off
given the KiCad 10 dirty-flag behavior).

The archive name template is persisted in `PluginOptions` alongside the
fabricator and inventory path. Its default is `"${TITLE}_${REVISION}"`.

### Fabricator selection

The fabricator dropdown is populated at dialog init time from
`get_available_fabricators()`. A disabled `Config…` button sits beside
it as a placeholder for a future read-only settings viewer. The button
is disabled (not hidden) so that users can see a config inspector is
planned but not yet available.

### Inventory file picker

The inventory path is a text field plus a `Browse…` button that opens a
`wx.FileDialog` filtered to `.csv`, `.xlsx`, and `.numbers`. An empty
path is valid and means "generate BOM without inventory enrichment."

### Checkbox set

The checkboxes and their rationale:

| Checkbox | Default | Notes |
|---|---|---|
| SMD only (placement) | off | Maps to `POSRequest.smd_only` |
| Exclude DNP components | on | Maps to `BOMRequest` DNP exclusion |
| Fill all zones before Gerbers | on | Smart fill — skips if already current; auto-saves board when fill runs |
| Create backup archive | on | Opt-in per storyboard inversion of FT's "no backup" default |
| Open production folder when done | on | Opens `production/` in Finder/Explorer on success |
| Apply placement corrections | off | Uses `transformations.csv` (harvested from FT); corrects KiCad-vs-fabricator orientation mismatches |
| Generate designators.csv | from fab config | `production/designators.csv` lists all reference designators in `REF:COUNT` format; generic fabricator default is off |
| Keep intermediate files (debug) | off | When on, dialog stays open after generation regardless of outcome |

Zone fill uses `fill_zones_if_needed()` from `jbom.plugin.zone_filler`,
a wx-free module extracted for testability. It skips fill when zones are
already current and auto-saves the board when fill actually ran. Running
a fabrication pipeline implies intent to save, so auto-save at this
point is correct rather than surprising.

The placement-corrections checkbox was specified in the storyboard as a
grayed-out placeholder pending the rotation-DB harvest from FT. That
work landed; the checkbox is now fully functional.

The designators checkbox was added after the storyboard and is not in
the original design. Its default state is read from the fabricator config
(`fabricator.generate_designators`), allowing fabricator profiles to
express their own convention.

## Completion behavior

On success with debug mode off, the dialog auto-closes and the
production folder opens in the platform file manager (if "Open
production folder when done" is checked). On success with debug mode on,
or on any error, the dialog stays open with the diagnostics text area
revealed, and the Cancel button relabels to Close. This gives the user a
chance to inspect error messages before the window disappears.

The distinction between error and informational diagnostics is made via
the `production_dir` value in the worker's result: `None` means no
artifacts were produced (treat as error); a valid path means at least
partial success.

## Persistence

`PluginOptions` persists three fields via `jbom-options.json`:

- `fabricator` — fabricator profile identifier, default `"jlc"`
- `inventory_path` — absolute path or empty string
- `archive_name_template` — template string, default `"${TITLE}_${REVISION}"`

All checkboxes are session-only; they reset to their defaults each time
the dialog opens. The rationale is that checkbox state reflects the
user's intent for a specific generation run rather than a persistent
project preference.

The options file resolution order is: `$git_root/.jbom/jbom-options.json`
(preferred — version-controllable, shared across the checkout), falling
back to `~/.jbom/jbom-options.json` when no git root is found. This is
consistent with how jBOM resolves YAML config more broadly
(see [ADR 0007](../architecture/adr/0007-plugin-packaging-and-distribution.md)
configuration-layering section).

## FT control disposition (decision history)

The dialog design started from Fabrication Toolkit's dialog as a
baseline and decided the fate of each FT control:

| FT control | jBOM treatment | Rationale |
|---|---|---|
| Archive name template | Editable field + preview (was: read-only label — see F-009) | User control over archive stem; live preview shows expanded value |
| Additional layers | Dropped | Handled by fabricator `gerbers: layers:` stanza — power users edit YAML |
| Plot all active layers | Dropped | Config-driven, not a dialog toggle |
| V-Cut (User.1) / alt Edge-Cut (User.2) | Dropped for now | FT-specific gerber layer routing; not yet in jBOM |
| Apply automatic component translations | Kept (functional) | Rotation/offset corrections from `transformations.csv` |
| Apply automatic fill for all zones | Kept | `pcbnew.ZONE_FILLER` available in SWIG mode; cheap safety net |
| Exclude DNP from BOM | Kept | Maps to DNP exclusion in `BOMRequest` |
| Open browser after generation | Kept | Opens `production/` in Finder/Explorer on success |
| Do not create backup files | Inverted to: Create backup archive | `BackupService` is opt-out; default on |

Controls added beyond FT's set: fabricator dropdown, inventory file
picker, designators CSV checkbox, archive name template (replaces FT's
read-only archive name display), debug mode.

## MVP exclusions

These are deliberate omissions, not gaps:

**Revision/title block editing** — incrementing the revision or editing
title block fields from within the dialog is out of scope. The dialog is
a fabrication artifact generator, not a schematic editor. Users who need
to bump the revision do so in KiCad's sheet setup before running jBOM.

**Fab config lifecycle manager** — creating, editing, or cloning
fabricator YAML profiles from within the plugin is out of scope. The
disabled `Config…` button is a placeholder for a future read-only
settings viewer; the lifecycle manager is a future enhancement that
warrants its own design.

**Multi-panel / array support** — panelizing decisions are made upstream
in the PCB layout. The plugin generates Gerbers from the board as-is.

**V-Cut / alt Edge-Cut layer options** — these require the FT gerber
layer routing harvest work and are deferred.

**Origin selector** — `jbom pos --origin` is a CLI feature for headless
workflows. The plugin resolves origin automatically from board settings,
matching FT's behavior.

**"Config…" button body** — the button renders in the dialog to signal
intent but is disabled. A full fabricator config viewer is a future
enhancement.
