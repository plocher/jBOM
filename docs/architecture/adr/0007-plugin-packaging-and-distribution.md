# ADR 0007: jBOM Plugin Packaging and Distribution Model
Date: 2026-05-09
Status: Accepted
Related: #227, ADR 0005 Phase 4, ADR 0006
## Context
Issue #227 begins implementation of the KiCad ActionPlugin adapter described in
ADR 0005 Phase 4. That work is blocked on a packaging decision: jBOM must ship
as **three things at once** without forcing the user to assemble them by hand.
1. A CLI tool (`jbom` on `$PATH`).
2. An importable Python library (`import jbom` from any project venv).
3. A KiCad plugin discoverable by KiCad's Plugin and Content Manager (PCM) and
   surfaced as an ActionPlugin button inside the PCB editor.
The plugin adapter requires `import pcbnew`, which is only available inside
KiCad's embedded Python interpreter. The CLI and library must continue to
import jBOM in any user Python environment without ever attempting to load
`pcbnew`. The runtime environments are not the same interpreter.
The issue lists three candidate models (A.1, A.2, B). This SPIKE evaluates
those three plus a hybrid option that emerged from the research, validates
them against the actual KiCad addon ecosystem rules, and records the resulting
decision.
## Decision Drivers
- **Single source of truth.** One git repo, one `jbom` package, one version
  number. No dual maintenance of fork copies.
- **Adapter-neutral core.** The `import pcbnew` boundary must stay isolated to
  the plugin adapter (ADR 0005). CLI/library installs must never fail because
  KiCad is absent.
- **First-run UX must be one step per delivery channel.**
  CLI users: `pip install jbom`. Plugin users: install through the KiCad
  Plugin and Content Manager ("Install from File" today, official repo later).
  Failures must not require PYTHONPATH editing or symlink hacks.
- **Survive KiCad minor upgrades in place.** A KiCad point release (e.g.
  9.0.5 → 9.0.6) must not break the plugin or the CLI. KiCad **major**
  upgrades (e.g. 9 → 10) reset the third-party plugin root by design and
  always require a reinstall regardless of packaging model — see F3.
- **Coexist with FT and other PCM plugins** (ADR 0006).
- **Forward path to KiCad's IPC plugin model** (KiCad 9+) without throwing
  away the SWIG ActionPlugin investment in the meantime.
## Research Findings
The following constraints come from KiCad's official addon documentation, the
PLUGIN_CONTENT_MANAGER source, the FT precedent, and KiCad community issues
referenced at the bottom of this ADR.
### F1. PCM packages cannot install pip dependencies
The KiCad 6.0 launch blog stated the limitation explicitly: "Plugins that
require pip packages need the pip packages installed manually by the user."
That has not changed for SWIG-based ActionPlugins through KiCad 8.x. PCM
extracts the zip into `${KICADX_3RD_PARTY}/plugins/<identifier>/` and then
runs whatever Python is found on import. There is no PCM hook that runs
`pip install` against KiCad's bundled interpreter.
Implication: any pure-Python deps the plugin needs at import time must either
(a) already be present in KiCad's bundled interpreter, or
(b) be vendored inside the PCM archive itself.
### F2. PCM archive layout is fixed and shallow
Per KiCad's "Publishing KiCad Addons" doc, a Python plugin archive must be:
```
Archive root/
  plugins/
    __init__.py
    ... your code ...
  resources/
    icon.png        # optional, 64x64
  metadata.json
```
"Place your plugin directly inside the `plugins` subdirectory, not inside a
second level of subdirectory." This is enforced by the PCM extractor. Dots
in the package `identifier` become underscores when extracted. The toolbar
icon (24x24) lives **inside** `plugins/`, not in `resources/`.
### F3. ActionPlugin search paths are version- and OS-dependent
ActionPlugins are discovered from these directories
(`pcbnew.PLUGIN_DIRECTORIES_SEARCH`):
- Linux: `~/.local/share/kicad/<ver>/scripting/plugins/`,
  `/usr/share/kicad/scripting/plugins/`
- Windows: `%APPDATA%\kicad\<ver>\scripting\plugins\`
- macOS: `~/Library/Application Support/kicad/<ver>/scripting/plugins/`,
  `/Applications/KiCad/KiCad.app/Contents/SharedSupport/scripting/plugins/`
- All platforms (PCM-installed): `${KICADX_3RD_PARTY}/plugins/<identifier>/`
A pip-installed Python package will **never** land in any of these by
accident. Even `pip install --user` writes to `~/.local/share/kicad/.../scripting/plugins/`
**only** on Linux, and even there KiCad-side path discovery is unreliable
(see GitLab issue kicad#5823).
**Major-version upgrade reality.** Every path above is namespaced by KiCad
major version (`9.0/`, `10.0/`, …) and the PCM root is namespaced as
`KICAD9_3RD_PARTY`, `KICAD10_3RD_PARTY`, …. A KiCad 9 → 10 upgrade does **not**
carry forward third-party plugins; the new install starts with an empty
3rd-party root and the user must reinstall via PCM (or re-symlink for the
dev path in F5). This is a property of KiCad's filesystem layout, not of
any packaging choice. PCM at least makes the re-install one click; manual
install paths require re-symlinking by hand.
### F4. The current `kicad_jbom_plugin.py` is a Tools-menu BOM generator, not an ActionPlugin
The file at `kicad_jbom_plugin.py` is the legacy
`Eeschema → Tools → Generate BOM` shim that shells out to the `jbom` CLI via
`subprocess`. It is unrelated to the in-PCB ActionPlugin work in #227 and to
this packaging decision. It can keep shipping as-is in `MANIFEST.in` for
existing users; #227 does not modify or remove it.
### F5. FT's distribution pattern is "PCM zip + the same package as a CLI module"
Fabrication Toolkit ships a single `metadata.json` + `plugins/` archive. The
`plugins/__init__.py` registers the ActionPlugin only when `pcbnew` is already
loaded, which is the runtime fingerprint of "we're inside KiCad":
```python
is_standalone = 'pcbnew' not in sys.modules or __name__ == "__main__"
if not is_standalone:
    from .plugin import Plugin
    Plugin().register()
```
FT's own CLI is reachable only as
`python -m com_github_bennymeg_JLC-Plugin-for-KiCad.cli`, which requires:
- the KiCad-bundled Python (only that interpreter has `pcbnew`),
- `wx` to be `pip install`-ed into that interpreter (manual step),
- `PYTHONPATH` set to the PCM extraction directory.
FT issue #204 documents the friction this causes — users repeatedly fail to
get the CLI running outside the GUI. **This is the failure mode to avoid.**
### F6. KiCad 9+ introduces a managed-venv IPC plugin model
The new "API plugin" system (KiCad 9.0+) replaces the SWIG ActionPlugin model
with out-of-process plugins driven by a `plugin.json` manifest. KiCad creates
a per-plugin venv at `${KICAD_CACHE_HOME}/python-environments/<id>/`, runs
`pip install -r requirements.txt` on first load, and talks to KiCad over a
Unix socket / Windows named pipe via the `kicad-python` (`kipy`) library.
Four observations shape jBOM's migration timing:
- The SWIG ActionPlugin path is "deprecated as of KiCad 9.0" but still ships
  through at least KiCad 10. Removal is targeted for KiCad 11.
- IPC API in KiCad 9 / 10 is PCB-only. There is **no schematic IPC**, and
  the official roadmap only states that schematic API support is a future
  goal.
- IPC in KiCad 9 / 10 also has no plotting/export. KiCad 11 adds it. Until
  then, `kicad-cli` is the supported route for export.
- jBOM **does not depend on either gap**. ADR 0006 already routes gerber
  generation through `kicad-cli`, and jBOM's schematic reader uses `sexpdata`
  to parse `.kicad_sch` files directly from disk — it never required a
  KiCad in-process schematic API. The only thing the plugin actually needs
  from a live KiCad runtime is the active board path
  (`pcbnew.GetBoard().GetFileName()` today; `kipy.KiCad().get_board().filename`
  on IPC). Everything downstream is filesystem-driven.
Net effect: an IPC migration is gated on **PCB IPC + `kicad-cli` export**,
both of which exist in KiCad 9. It is *not* gated on schematic IPC ever
shipping. The SWIG ActionPlugin model is the right answer **today** because
it is the only one that works on KiCad 6/7/8, but the IPC variant becomes
viable as soon as the user cohort is on KiCad ≥ 9 — sooner than the
"deprecation removal" timeline implied.
### F7. jBOM's runtime dependency surface is small and pure-Python
From `pyproject.toml`:
- Required: `sexpdata>=0.0.3`, `PyYAML>=5.4.0`
- Optional (`all` extras): `openpyxl>=3.0`, `numbers-parser>=3.0`,
  `requests>=2.28.0`
None of these contain compiled extensions other than `numbers-parser` (which
is optional and not needed by the fab workflow). All can be vendored into a
PCM archive without binary-compatibility risk against KiCad's bundled Python.
### F8. ProjectMetadata is read from the `.kicad_pro` / title block, not from the runtime
Per ADR 0006, jBOM resolves project context from on-disk files. Inside the
plugin we get a free hint via `pcbnew.GetBoard().GetFileName()` but the rest
of the resolution path (schematic discovery, fabricator config, inventory)
is identical to CLI mode. The plugin adapter does **not** require any deeper
SWIG API surface than what FT already uses, so the IPC migration in F6 is not
blocked by hidden `pcbnew` dependencies in jBOM core.
## Options Considered
The first three options are the candidates listed verbatim in #227. Option H
emerged from the research above.
### Option A.1 — Standalone manual install ("pip install jbom" + manual plugin path)
Ship CLI/library on PyPI as today. Provide a separate plugin file (or
`jbom install-plugin` helper) that imports jBOM from the user's Python and
gets dropped into the user's `…/scripting/plugins/` directory by hand.
Pros:
- Single Python install. No vendoring. CLI and plugin import the same code.
- Immediate to implement; mirrors the existing `kicad_jbom_plugin.py` pattern.
Cons:
- Plugin is invisible to PCM. Users cannot discover, update, uninstall, or
  see version status from KiCad's plugin manager. Loses the "feels like a
  real KiCad plugin" UX bar set by FT.
- Plugin and CLI are coupled to the **user's chosen Python interpreter**, but
  KiCad on Windows/macOS uses its own bundled Python. So the plugin cannot
  reliably `import jbom` from `pip install`'s site-packages on those
  platforms unless the user installed jBOM into KiCad's bundled python (which
  is not where `pip install jbom` lands by default).
- No "survive KiCad upgrades" story: KiCad 8 → 9 changes the search-path
  conventions and the user's manual symlink is silently abandoned.
**Verdict: rejected as primary model.** Useful only as a power-user fallback.
### Option A.2 — KiCad PCM only (no PyPI involvement)
Ship a single PCM-installable archive. Drop PyPI distribution.
Pros:
- Cleanest UX for the plugin user.
- One channel to maintain, one place to publish.
Cons:
- Eliminates the CLI/library use case entirely, which is a core jBOM design
  goal (ADR 0005, README.man1.md). PCM-installed code lives in
  `${KICADX_3RD_PARTY}/` and is reachable from the shell only through the
  exact `python -m` incantation that is FT issue #204. Headless / CI BOM
  generation effectively dies.
- Locks jBOM to KiCad's bundled Python version, which lags the system Python
  the user might want for other tooling.
**Verdict: rejected.** Conflicts with the explicit "three things at once"
goal in #227.
### Option B — PyPI extras with post-install plugin shim (`pip install jbom[plugin]`)
Plugin adapter lives in `src/jbom/plugin/` with conditional `pcbnew` imports.
A post-install hook drops a discovery file into KiCad's plugin search path.
Pros:
- Single PyPI publish step; everything follows from `pip install`.
Cons:
- **Wrong interpreter problem (same as A.1).** On Windows/macOS, KiCad uses
  its own Python; the user's `pip install` lands somewhere KiCad's plugin
  loader cannot import from. We would have to detect KiCad's Python at
  install time, which is fragile (multiple KiCad versions installed,
  KICAD8_3RD_PARTY vs. KICAD9_3RD_PARTY drift).
- Post-install hooks in setuptools are widely discouraged (PEP 517 build
  isolation makes them quiet failures) and `pip install --user` writes to a
  path KiCad does not search except on Linux.
- KiCad upgrades change `KICADX_3RD_PARTY` and the shim is orphaned.
- Invisible to PCM. Users cannot uninstall through KiCad UI.
**Verdict: rejected.** Highest implementation cost, lowest reliability.
This option is what KiCad maintainers explicitly cite as the broken model
(GitLab kicad#5823).
### Option H — Hybrid: PyPI for CLI/library; PCM for the plugin (selected)
Treat the **two delivery channels as orthogonal** and stop trying to make a
single artifact serve both interpreters.
1. **PyPI channel — CLI and library.** Continue publishing `jbom` to PyPI
   exactly as today. `jbom.cli`, `jbom.application`, `jbom.services`,
   `jbom.workflows`, `jbom.config` etc. ship unchanged. The plugin code is
   present in the source tree under `src/jbom/plugin/` but is **never**
   imported by CLI/library entry points and never imports `pcbnew` at module
   import time (TYPE_CHECKING + lazy guard). PyPI users get the CLI and the
   library; nothing in this channel touches KiCad.
2. **PCM channel — the plugin bundle.** Build a PCM-compliant zip artifact
   from the same git repo. The build copies `src/jbom/` and the small,
   pure-Python required runtime deps (`sexpdata`, `PyYAML`, plus any optional
   deps the plugin scope actually exercises) into the archive's `plugins/`
   directory under a single namespace package. The thin
   `plugins/__init__.py` adopts FT's idiom: only register the ActionPlugin
   when `pcbnew` is loaded; otherwise stay silent so `python -m` still works
   for tests.
   The same package version goes in both PyPI and the PCM `metadata.json`.
   The build is reproducible from `pyproject.toml`'s declared dependency
   pins, so the vendored copies match a given jBOM release.
3. **Distribution.** PyPI is already wired up. PCM publishing happens in two
   stages:
   a. Self-hosted PCM repository on GitHub Pages (the
      `hatch-kicad`/`adamws/kicad-plugin-template` pattern), produced as a
      release artifact and announced in `README.md`. Users add the URL to
      KiCad's "Manage Repositories" once.
   b. Submit the package to the official KiCad PCM index after one or two
      stable releases on the self-hosted feed.
4. **Forward path to IPC plugins.** Once the user cohort is on KiCad ≥ 9
   (F6), add a parallel `plugin.json` IPC manifest variant whose
   `requirements.txt` simply lists `jbom==<version>` from PyPI. KiCad will
   create a per-plugin venv and `pip install jbom` into it, and the
   **vendoring is no longer needed**. The current SWIG bundle stays in
   maintenance for KiCad 6/7/8 users until the long tail thins out.
5. **Development loop uses a symlink, not a rebuild.** During plugin
   development, the maintainer creates a symlink from KiCad's user plugin
   path to the working tree:
   ```
   ln -s $PWD/src/jbom/plugin \
     ~/Library/Application\ Support/kicad/9.0/scripting/plugins/jbom
   ```
   This is the workflow KiCad's own developer docs recommend
   ("a symbolic link can be created in the KiCad plugin path … useful for
   development"). It is conceptually a degenerate Option A.1 and is the
   *only* role A.1 retains under this decision. Code edits land in KiCad
   on the next plugin reload — no zip rebuild, no re-install. CI also
   benefits: a `make pcm` target produces a local PCM zip, and a tiny
   self-hosted `repository.json` plus that zip is enough for KiCad in a CI
   container to install the plugin via PCM and run smoke tests against it.
6. **No post-install hooks. No PYTHONPATH instructions. No
   `pip install jbom[plugin]` extra.** These are explicitly *not* used in
   either the dev or production path.
#### Configuration layering under PCM
jBOM resolves YAML config from a hierarchical search path: `$CWD`,
`$ProjectDir`, `$HOME`, `$JBOM_INSTALL_DIR`. Mapping these onto a
PCM-installed plugin:
- `$JBOM_INSTALL_DIR` resolves at runtime to
  `os.path.dirname(__file__)` of the plugin package — i.e. the PCM
  extraction directory `${KICADX_3RD_PARTY}/plugins/jbom/`. This layer is
  treated as **read-only shipped defaults**. Any file PCM rewrites on
  update lives here: `config/*.yaml`, `config/fabricators/*.yaml`,
  `config/presets/*.yaml`, `config/suppliers/*.yaml` — already declared as
  `package-data` in `pyproject.toml`, so they ride along into the PCM zip
  by the same packaging step that puts them on PyPI.
- `$CWD`, `$ProjectDir`, `$HOME` are **fully writable, untouched by PCM**.
  Per ADR 0006, the plugin's per-project options (`jbom-options.json`) are
  written to `$ProjectDir`, never to `$JBOM_INSTALL_DIR`. User-authored
  fabricator overrides land in `$HOME/.jbom/fabricators/*.yaml` or
  `$ProjectDir/jbom/fabricators/*.yaml`. A KiCad PCM update of jBOM does
  not touch any of those paths.
- KiCad 7+ supports a `keep_on_update` regex in `metadata.json` that
  preserves named files inside the PCM extraction dir across updates. The
  design **does not rely on this**; it is reserved as a future affordance
  if a use case appears for an install-dir-local writable file.
Writability summary across PCM and PyPI updates:
- `$JBOM_INSTALL_DIR` (PCM zip): read-only baseline; rewritten on PCM
  update.
- `$JBOM_INSTALL_DIR` (PyPI / system Python site-packages): same — owned
  by `pip`, treated as read-only.
- `$HOME`, `$ProjectDir`, `$CWD`: writable; preserved across both PCM and
  pip updates because neither installer touches those paths.
This layout is actually *cleaner* than A.1 or B would be: in those models
the shipped-defaults directory is sometimes the same as a `pip install --user`
site-packages directory, blurring the read-only/writable boundary. Under
H the boundary is enforced by the installer itself.
Pros:
- Each channel matches the interpreter that runs it. PyPI lands in the
  user's Python; PCM lands in KiCad's Python. No cross-interpreter import
  attempts.
- Plugin is fully PCM-managed: install, update, uninstall, version-display
  all work in the KiCad UI. Survives KiCad **point-release** upgrades in
  place; KiCad **major-version** upgrades require a one-click reinstall via
  PCM (F3). Manual install paths require re-symlinking by hand at the same
  boundary, so this is the best available behavior, not a regression.
- CLI/library is fully PyPI-managed and decoupled from KiCad's release
  cadence and bundled Python version.
- Same source tree, same version number, no dual maintenance.
- Clean migration to the KiCad IPC plugin model (KiCad ≥ 9, see F6): same
  code, smaller archive (no vendoring), declared deps via
  `requirements.txt`.
Cons:
- The PCM archive is larger than strictly necessary (carries vendored
  `sexpdata` and `PyYAML`). Acceptable: under a few hundred KB combined.
- Two release artifacts must be produced from one release commit. Adds CI
  complexity but is mechanical (the `hatch-kicad` builder solves it for the
  PCM half; existing `python-semantic-release` keeps handling PyPI).
- Vendored deps must be refreshed on each release. Mitigated by pinning in
  `pyproject.toml` and copying from the resolved wheel cache during build.
**Verdict: accepted.**
## Decision
Adopt **Option H**:
- CLI and library: PyPI (unchanged channel).
- Plugin: PCM-installable archive (new channel) built from the same source
  tree, vendoring the small set of pure-Python runtime dependencies.
- Migrate to KiCad's IPC plugin model (managed venv + `requirements.txt`)
  as a parallel artifact when the user cohort is on KiCad ≥ 9 (gated only
  on PCB IPC + `kicad-cli` export, both already shipped — see F6).
The current `kicad_jbom_plugin.py` Eeschema-BOM shim is orthogonal to this
decision and is preserved as-is.
## Open Questions Answered
The four questions in #227 SPIKE 1 resolve as follows.
- **How does KiCad discover ActionPlugins on macOS / Windows / Linux?**
  See F3. PCM-installed plugins land in `${KICADX_3RD_PARTY}/plugins/<id>/`
  on every platform. User-installed plugins use a per-OS path. Option H only
  uses the PCM path, eliminating the OS-specific user paths from the
  end-user experience.
- **Can a PyPI-installed entry point register a KiCad plugin, or does it
  require a file at a fixed path?**
  No, a PyPI-installed entry point cannot register an ActionPlugin. KiCad's
  plugin loader scans fixed directories listed in
  `pcbnew.PLUGIN_DIRECTORIES_SEARCH`; it does not consult Python entry
  points or `sys.path`. An archive at the PCM-managed fixed path is
  required (F2, F3).
- **How do FT and other established KiCad Python plugins handle
  distribution?**
  FT, InteractiveHtmlBom, jsreynaud/kicad-action-scripts, and
  adamws/kicad-plugin-template all use the same pattern: a PCM-compliant zip
  with `plugins/`, `resources/`, `metadata.json`. None of them try to be a
  pip-installable library at the same time. jBOM's choice to be both is
  what motivates Option H's split-channel approach.
- **What is the right isolation boundary for `import pcbnew` so CLI mode
  never fails?**
  The `src/jbom/common/kicad_runtime.py:is_running_inside_kicad()` predicate
  already encodes the right test ("can we import `pcbnew`?"). The plugin
  adapter package will:
  - Use `from __future__ import annotations` and `if TYPE_CHECKING:` for any
    `pcbnew` types in signatures.
  - Confine actual `import pcbnew` calls to inside ActionPlugin methods that
    only run when KiCad invokes them.
  - Mirror FT's `__init__.py` guard: register the ActionPlugin only when
    `pcbnew` is already in `sys.modules`. CLI imports of `jbom.plugin.*`
    must be no-ops (importable but inert).
## Consequences
### Positive
- Three distribution stories, three correct interpreters: `pip install jbom`
  (system Python), KiCad PCM (KiCad's bundled Python), and the future
  KiCad-managed IPC venv.
- The user-visible install steps stay one-step per channel.
- Plugin gets a real PCM identity: install/update/uninstall in KiCad UI,
  versioned and discoverable.
- No regressions for headless/CI workflows.
### Tradeoffs
- New CI job: build and publish a PCM zip + a `repository.json` index per
  tag. Tooling exists (`hatch-kicad`).
- Vendoring step in the PCM build must keep deps in lockstep with the
  current `pyproject.toml` pins.
- The same code path (workflow services) is now exercised under two Python
  interpreters; tests should run against KiCad's bundled Python in CI for
  parity (already a goal of #228).
- **Two update flows for users who install both channels.** A user who has
  both `pip install jbom` and the PCM plugin must update each. Mitigations:
  KiCad shows an in-UI badge for available PCM updates (one click); pip
  users have a habitual `pip install -U`. Versions are released from a
  single git tag so they cannot diverge at the source. Residual risk: a
  user updates one and forgets the other and the two are then on different
  versions. Given jBOM's stability posture and contract testing
  (see #228), the impact of a one-version skew is small — accepted.
### Risks and mitigations
- **Risk:** vendored copies of `sexpdata` / `PyYAML` go stale.
  **Mitigation:** the PCM build resolves them from the same lock that pins
  the PyPI release; CI fails if the vendored versions diverge.
- **Risk:** KiCad's bundled Python ABI shifts (e.g. 3.11 → 3.12) and a
  vendored dep stops importing.
  **Mitigation:** vendor only pure-Python deps (true today). For any future
  binary dep, switch the plugin path to PyPI-on-IPC (F6).
- **Risk:** PCM archive size review by the official repository maintainers.
  **Mitigation:** target < 500 KB compressed by trimming docstrings/tests
  from vendored deps; confirmed achievable by the FT footprint precedent.
- **Risk:** KiCad major version upgrade (e.g. 9 → 10) leaves the plugin
  uninstalled in the new install root.
  **Mitigation:** none available at the packaging layer — this is a KiCad
  filesystem-layout property (F3). Document the one-click PCM reinstall
  step in the upgrade notes for each KiCad major release.
## Phased Execution
Phase 1 (this PR / SPIKE outcome):
- Land this ADR.
- Add a build target stub (`scripts/build_pcm_package.py` or `hatch-kicad`
  config in `pyproject.toml`) that produces a draft archive locally for
  inspection. No CI integration yet.
- Validate import-cleanliness via a tiny POC: zip up `src/jbom/` plus
  vendored `sexpdata` / `PyYAML`, drop into a local PCM, run an empty
  ActionPlugin that just prints `jbom.__version__`. Confirms F1/F7 hold on
  macOS.
Phase 2 (issue #227 implementation):
- Build the actual ActionPlugin adapter under `src/jbom/plugin/` per ADR 0005
  Phase 4.
- Wire CI to publish the PCM archive to GitHub Releases on tag.
- Stand up a self-hosted PCM repository on GitHub Pages.
Phase 3 (post-bootstrap, separate issue):
- Submit the package to the official KiCad PCM index.
- Add the parallel `plugin.json` IPC manifest variant for KiCad ≥ 9 users
  once the cohort warrants it (see F6 and the Future Directions section).
## Future Directions
The items below are *not* part of this decision. They are recorded so they
do not get lost when the SPIKE 1 branch is merged.
### Schematic IPC: prototype a jBOM-shaped server
KiCad's IPC API roadmap names schematic-editor support as a future goal but
does not yet publish a protobuf schema for it. jBOM has a mature in-tree
schematic reader (`sexpdata`-based) that already exposes the operations a
BOM/POS workflow needs: enumerate components, read fields, follow hierarchy,
resolve sub-sheet references, dereference variants. That surface is a
plausible *shape* for a future KiCad schematic IPC contract.
A worthwhile follow-up — outside the scope of #227 — would be:
1. Define a small protobuf for the schematic operations jBOM actually uses
   (component iteration, hierarchy walk, field read, title-block read).
2. Wrap jBOM's existing `sch_api` services as a local IPC server that
   speaks that protobuf over a Unix socket / named pipe, mirroring KiCad's
   `KICAD_API_SOCKET` conventions.
3. Have the jBOM plugin adapter speak that protocol both to its own
   embedded server (today) and to a future `kicad` process (when KiCad
   ships schematic IPC).
This would yield two practical benefits:
- jBOM's plugin and CLI adapters share one transport, with the same
  serialization on both sides.
- The protobuf schema itself becomes a working concrete proposal we could
  open as an upstream RFC. KiCad's IPC working group has an explicit
  invitation: "We encourage developers to report issues and request new
  capabilities as they use the API."
Not a commitment, just a recorded option. If pursued, it would warrant
its own ADR.
### IPC plugin variant for KiCad ≥ 9
Once the user cohort is on KiCad 9+, publish a parallel `plugin.json`
manifest variant whose `requirements.txt` lists `jbom==<version>` from
PyPI. KiCad creates the venv, `pip install`s jBOM, and the vendoring step
disappears from the build. The SWIG zip continues for KiCad 6/7/8 users
until the long tail thins out. This is in scope for a future ADR, not
this one.
## References
- KiCad Addons / PCM packaging spec:
  https://dev-docs.kicad.org/en/addons/index.html
- KiCad ActionPlugin developer guide and search paths:
  https://dev-docs.kicad.org/en/apis-and-binding/pcbnew/
- KiCad IPC API (KiCad 9+) for add-on developers:
  https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/
- "Third Party Content Improvements" KiCad blog (no auto-pip in PCM):
  https://www.kicad.org/blog/2021/12/Development-Highlight-Third-Party-Content-Improvements/
- `hatch-kicad` PCM build backend:
  https://github.com/adamws/hatch-kicad
- KiCad plugin template:
  https://github.com/adamws/kicad-plugin-template
- Fabrication Toolkit precedent (PCM zip + `metadata.json`):
  `/Users/jplocher/Dropbox/workspace/Fabrication-Toolkit/metadata.json`
  `/Users/jplocher/Dropbox/workspace/Fabrication-Toolkit/plugins/__init__.py`
- FT CLI-from-PCM friction (illustrating the Option B failure mode):
  https://github.com/bennymeg/Fabrication-Toolkit/issues/204
- KiCad pip path incompatibility:
  https://gitlab.com/kicad/code/kicad/-/issues/5823
- jBOM ADR 0005 (adapter-neutral core):
  `docs/dev/architecture/adr/0005-jbom-evolutionary-supersession-cli-plugin-session-model.md`
- jBOM ADR 0006 (production folder & service decomposition):
  `docs/dev/architecture/adr/0006-production-folder-packaging-projectmetadata-diagnostic-collection.md`
- jBOM in-tree KiCad runtime detection:
  `src/jbom/common/kicad_runtime.py`
