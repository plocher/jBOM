# jBOM Plugin Development Setup

This guide covers the local development workflow for the jBOM KiCad ActionPlugin
(`src/jbom/plugin/`). It assumes you have already cloned the repository and
installed the jBOM CLI dependencies (`pip install -e ".[dev]"`).

## Background

jBOM ships through two independent distribution channels:

| Channel | Users | Install step |
|---------|-------|--------------|
| PyPI | CLI / library users | `pip install jbom` |
| PCM | KiCad plugin users | "Install from File" in KiCad Plugin Manager |

The plugin adapter lives in `src/jbom/plugin/` and uses a **symlink** during
development so code edits are immediately visible in KiCad — no zip rebuild,
no reinstall. The PCM archive is only needed for release or smoke-test purposes.

See `docs/dev/architecture/adr/0007-plugin-packaging-and-distribution.md` for
the full packaging rationale (Option H hybrid model).

## Dev loop setup

### macOS (KiCad 9)

```bash
# IMPORTANT: the symlink target name MUST match the PCM identifier
# (com.spcoast.jbom → com_spcoast_jbom).
# Using "jbom" as the name would shadow the importable jbom package
# on sys.path and cause a circular import. See ADR 0007 F2.
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Application\ Support/kicad/9.0/scripting/plugins/com_spcoast_jbom
```

To apply for a different KiCad version, replace `9.0` with the appropriate
version directory (e.g. `8.0`, `7.0`).

### macOS (KiCad 8 / 7)

```bash
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Application\ Support/kicad/8.0/scripting/plugins/com_spcoast_jbom
```

### Linux

```bash
ln -s "$PWD/src/jbom/plugin" \
  ~/.local/share/kicad/9.0/scripting/plugins/com_spcoast_jbom
```

### Windows

```powershell
New-Item -ItemType Junction -Path "$env:APPDATA\kicad\9.0\scripting\plugins\com_spcoast_jbom" `
         -Target "$PWD\src\jbom\plugin"
```

## Activating the plugin

1. Open KiCad's **PCB Editor** (Pcbnew).
2. Open **Scripting Console** (Tools → Scripting Console).
3. Type `import pcbnew; pcbnew.LoadPlugins()` to force a plugin rescan, or
   simply close and reopen Pcbnew.
4. The jBOM toolbar button should appear in the right-hand toolbar.

## How the sys.path bootstrap works

`src/jbom/plugin/__init__.py` adds two paths to `sys.path` at load time:

1. **`_this_dir`** — the plugin directory itself (resolves to
   `src/jbom/plugin/` via the symlink). In a PCM install this would be
   `${KICADX_3RD_PARTY}/plugins/com_spcoast_jbom/`, which contains the
   vendored `jbom/` package.

2. **`_src_dir`** — two levels up from `plugin/`, which is `src/` in the dev
   tree. This puts the editable `jbom` source package on `sys.path` so
   `import jbom` finds the live source without a separate
   `pip install` into KiCad's bundled Python.

In production (PCM install) both paths are added; `_src_dir` resolves to the
PCM plugins parent directory, which is harmless (no `jbom` package there).

## Building the PCM archive

```bash
# Produces dist/jbom-pcm-{version}.zip
python scripts/build_pcm_package.py

# Also patch metadata.json with computed sha256 + sizes (for release prep)
python scripts/build_pcm_package.py --update-metadata
```

The archive can be installed manually via KiCad → Plugin Manager →
"Install from File" for smoke-testing without a GitHub release.

## Running the test suite

The plugin's Python-only modules (`options.py`, `__init__.py`) are fully
testable without KiCad or wxPython:

```bash
pytest tests/plugin/ -v
```

The dialog (`dialog.py`) and the ActionPlugin class (`plugin.py`) import
`wx` and `pcbnew` respectively, and can only be exercised inside a live
KiCad instance. Manual smoke-testing via the dev-loop symlink is the
appropriate method for these.

## Troubleshooting

### "import jbom fails" inside KiCad scripting console

Check that the symlink name is `com_spcoast_jbom` (not `jbom`):

```bash
ls -la ~/Library/Application\ Support/kicad/9.0/scripting/plugins/
```

If you see `jbom -> ...` instead of `com_spcoast_jbom -> ...`, remove the
old symlink and re-create it with the correct name:

```bash
rm ~/Library/Application\ Support/kicad/9.0/scripting/plugins/jbom
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Application\ Support/kicad/9.0/scripting/plugins/com_spcoast_jbom
```

### Plugin does not appear in the toolbar

1. Verify the symlink exists and points to the correct directory.
2. Open the KiCad Scripting Console and run:
   ```python
   import pcbnew; pcbnew.LoadPlugins(); print("done")
   ```
3. Check the KiCad error log (Help → Show Error Log) for Python import errors.

### KiCad major version upgrade

KiCad major version upgrades (e.g. 9 → 10) use a new plugin root directory
(`KICAD10_3RD_PARTY`). Re-create the symlink pointing at the new version path:

```bash
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Application\ Support/kicad/10.0/scripting/plugins/com_spcoast_jbom
```

## SEE ALSO

- `docs/dev/architecture/adr/0007-plugin-packaging-and-distribution.md` —
  packaging decision (Option H hybrid model)
- `docs/dev/development_notes/active/plugin_ux_storyboard.md` —
  dialog design specification
- `scripts/build_pcm_package.py` — PCM archive builder
- `src/jbom/plugin/` — plugin source tree
