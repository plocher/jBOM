# Config-Schema Conformity Audit of the Source Tree

Generated: 2026-08-10 — wayfinder ticket #387 (map #385)
Baseline: ADR 0008 (unified `*.jbom.yaml` schema), ADR 0009 (field references), ADR 0010 (pydantic binding), ADR 0015 (key inventory / smell catalogue)

Scope: `src/jbom` only. Question: *where does the source tree still assume the pre-unification typed-config model?*

## Summary verdict

The **loader core conforms**: `config/unified.py` implements D1/D4/D5/D6-notice/D7 faithfully (common chain, first-match named profiles, `extends:` with cycle detection, deep-merge with null-delete, policy notice), `config/profile_search.py` recognises only `.jbom.yaml`, and the built-in files are fully migrated (`config/profiles/*.jbom.yaml`; legacy `fabricators/`, `suppliers/`, `defaults/`, `presets/` subdirectories are gone).

The nonconformities cluster in three places: **(a)** dead legacy-shim code retained inside the three typed loaders, **(b)** the CLI option surface, which reintroduces the dimension flags ADR 0008 D3 explicitly deferred and hand-rolls per-fabricator shorthands inconsistently across commands, and **(c)** a defaults-selection channel (`--defaults` + process-global mutable state) that splits stanza consumption across *two different profiles*, contradicting D2's model of one named profile per invocation.

## Conforming touchpoints (verified)

- `config/unified.py` — D4 extends/cycle detection, D5 cumulative common chain vs first-match named profiles, D6 `policy.jbom.yaml` reserved-name notice, null-delete/list-replace merge (`_deep_merge`), per-stanza `id:` override (`_effective_stanza_id`), D3 flag-vocabulary support via `list_unified_stanza_ids` / `resolve_profile_name_for_stanza_id`.
- `config/profile_search.py` — `.jbom.yaml` only; documented search order matches D5.
- `config/profiles/` — all eight built-ins are unified files; no legacy suffixes anywhere in the package (verified by find).
- `plugin/diagnostics.py` — profile snapshot is fully unified-aware (search dirs, stanza ids, extends chain, common chain).
- `common/cli_fabricator.py` — shorthand `--<id>` flags are generated dynamically from discovered `fab:` stanzas (used by `pos`, `fab`, `gerbers`) — the D3-conforming pattern.

## Nonconformities

### N1 — Dead legacy-shim code in all three typed loaders (D8: "no shim")

The legacy built-in directories no longer exist, so every legacy branch below is unreachable dead code — but it is still the *first thing a reader learns* about config loading, and it keeps the retired vocabulary alive:

- `src/jbom/config/fabricators.py` — `_find_legacy_profile()` (`*.fab.yaml` search, 484–492), the `except UnifiedProfileNotFoundError` legacy fallback in `_load_fabricator_cached` (473–481), `_BUILTIN_DIR` pointing at the removed `config/fabricators/` (408), and `_list_fabricators_cached` scanning it for `*.fab.yaml` (450–458).
- `src/jbom/config/suppliers.py` — same trio for `*.supplier.yaml` (328, 357–366, 383–401).
- `src/jbom/config/defaults.py` — `_load_yaml_resolved()` legacy `*.defaults.yaml` loader (699–719), `_find_legacy_profile` (722–732), `_load_builtin_generic()` fallback to `generic.defaults.yaml` (740–746), and a **second, divergent merge engine** `_deep_merge` (749–758) with *no null-delete semantics* — a silent behavioural fork from the unified engine.

Also: `_find_legacy_profile` is duplicated three times, and two `_deep_merge` implementations coexist (`unified.py` vs `defaults.py`).

### N2 — Dimension flags exist despite ADR 0008 D3 deferring them

D3: "Dimension-specific flags (`--fabricator`, `--defaults`, `--supplier`) are not introduced in v1"; the CLI exposes `--<configname>` per named profile, generated from stanza presence.

- `--fabricator` — `common/cli_fabricator.py:37`, `cli/bom.py:115`, `cli/parts.py:273` (also `jbom fab`, `pos`, `gerbers` via the shared helper).
- `--defaults` — injected into **every** subcommand by `cli/main.py:71-85` (`_add_defaults_argument_to_subcommands`), default `generic`.
- `--supplier` — `cli/search.py:244`, `cli/promote.py:58`, `cli/inventory.py:188`, `cli/audit.py:238`. *Nuance:* in `inventory`/`audit`/`promote` this selects a supplier **context** (which catalog to query), not a config file — the option-group taxonomy should decide whether that is profile-selection or an operational selector, but today the same spelling serves both meanings.
- `jbom search` uses `--supplier ID` instead of the D3 pattern `jbom search --lcsc` (stanza-derived flags are never generated for the `supplier:` stanza anywhere).

### N3 — Hard-coded shorthand flags in `bom` and `parts` (vs dynamic generation elsewhere)

- `cli/bom.py:121-124` and `cli/parts.py:279-282` hard-code `--jlc`, `--pcbway`, `--seeed`, `--generic` as static `store_true` flags plus a hand-rolled resolution ladder (`_resolve_requested_fabricator`, `parts.py:435-446`). Profiles added to the search path (e.g. `digikey`, or a user's `acme-jlc.jbom.yaml`) get shorthands in `pos`/`fab`/`gerbers` but **not** in `bom`/`parts`.
- `cli/promote.py:81-84` hard-codes `--jlc` as "shortcut for `--supplier lcsc`" — a baked-in instance of the per-stanza `id:` mapping (D3's jlc/lcsc example) that the unified loader already computes generically (`resolve_profile_name_for_stanza_id`).

### N4 — Defaults selection bypasses the unified profile model (D2 violation)

D2 says a command consumes the stanzas it needs *from the selected named profile* (`jbom bom --jlc` → `fab:` + `defaults:` of the jlc chain). Actual behaviour:

- `fab:` comes from the `--jlc`/`--fabricator` selection, but `defaults:` **always** comes from the separate `--defaults` profile (default `generic`), plumbed through process-global mutable state: `set_active_defaults_profile()` wraps every handler in `cli/main.py:113-119`, and `get_defaults()` reads the global (`config/defaults.py:671-696`).
- A `jlc.jbom.yaml` `defaults:` stanza is therefore inert for `jbom bom --jlc` unless the user also passes `--defaults jlc`. This is the largest structural divergence from the unified schema and feeds directly into the profile-selection option group and `--show-config` provenance design.
- `get_defaults()` also swallows *any* load error and silently substitutes built-in generic (`defaults.py:677-683`) — masking misconfigured profiles; contrast with the fab path, which raises `Unknown fabricator`.

### N5 — `presets:` stanza is schema-valid but never consumed

- `unified.py:39` accepts `presets` as a stanza and `plugin/diagnostics.py:270` reports its ids, but no code extracts it: global presets are the hard-coded Python dict `FIELD_PRESETS` in `common/fields.py:156` (with profile-flavoured names like `generic`/`jlc`), merged with `fab.presets` in `common/field_parser.py:146-148`. Config-declared top-level presets (e.g. in `generic.jbom.yaml`) are dead weight. (ADR 0015 S3 flagged the presets collision; the Python-side duplicate makes it worse.)
- `transforms:` (ADR 0009's top-level stanza) is likewise absent from `_VALID_STANZA_NAMES` — either the ADR or the loader is stale.

### N6 — Hard-coded profile/supplier IDs in logic paths

- `plugin/options.py:48,68` — plugin default fabricator is the literal `"jlc"`.
- `cli/bom.py:679-684` and `services/bom_field_resolver.py:74` — special-case `lcsc` field token resolution baked into Python.
- `cli/search.py:240-242` — default supplier resolution prefers literal `"generic"`.
- `"generic"` fallback literals are scattered across ~15 files (`application/pos_workflow.py`, `application/fabrication_orchestration.py`, `services/*_field_resolver.py`, `common/field_parser.py:82-91`, `cli_fabricator.py:94`, …). Individually benign per D7, but there is no single constant/owner for "the implicit fallback profile", so the assumption is diffuse.

### N7 — `jbom config` command is typed-config-centric

`cli/config.py` offers only `--schema`, printing the **FabricatorConfig** JSON schema — one stanza of four, addressed by its pre-unification identity. No resolved-config view, no provenance, no supplier/defaults schema. This is the natural home for the deferred `jbom config show` (ADR 0008 deferred item 5) and the `--show-config` provenance design; the unified loader's eval trace (`record_profile_eval`) and the plugin's `ProfileSnapshot` are reusable building blocks.

### N8 — Stale retired-vocabulary references (documentation-severity)

- `services/rotation_correction_service.py:142` — docstring cites "`.fab.yaml` `rotation_convention` key".
- `suppliers/lcsc/query_planner.py:8` — "See generic.defaults.yaml for factory values".
- `cli/fabrication.py:51` — help text suggests "define a custom fabricator config (e.g. myspecialfab.yaml)" (wrong suffix).
- `cli/search.py:567` — comment "(selected by --defaults, default: generic)" documents the N4 split as if intended.
- `cli/search.py:623` — unreachable duplicate `return DiskSearchCache(args.supplier)` (dead code).

## Feed-forward notes

- **Option-group taxonomy (profile-selection group):** today's de-facto selectors are `--fabricator`, per-id shorthands (two generation mechanisms), `--supplier` (two meanings: profile vs catalog context), and the global `--defaults`. N2–N4 are the raw material; the taxonomy must decide one selection idiom and whether supplier-as-context is a selector or a decorator.
- **`--show-config` provenance:** the unified loader already records candidate/match traces and the plugin snapshot computes the full chain (named + extends + common, with role labels). A CLI `jbom config show --<id>` can reuse both; the N4 defaults split must be resolved first or provenance output will faithfully display the confusing two-profile reality.
