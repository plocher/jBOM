---
name: plugin-dev-setup
description: Set up the jBOM KiCad ActionPlugin development loop for contributors working on src/jbom/plugin/. Use when creating or recreating the dev symlink, activating the plugin in KiCad's Pcbnew, building the PCM archive for smoke-testing, or understanding the sys.path bootstrap and the KiCad SWIG/CPython GC gotcha.
---

# plugin-dev-setup

Developer workflow for working on `src/jbom/plugin/` — the jBOM KiCad
ActionPlugin. This skill is for contributors modifying the plugin source,
not for end users registering the BOM plugin in Eeschema. For the
end-user setup, see the [kicad-plugin-setup skill](../kicad-plugin-setup/SKILL.md).

## Background

jBOM ships through two independent distribution channels:

- **PyPI** — for CLI and library users (`pip install jbom`)
- **PCM** — for KiCad ActionPlugin users (installed via KiCad Plugin Manager)

The plugin adapter lives in `src/jbom/plugin/`. During development, a
symlink into KiCad's plugin directory makes code edits immediately visible
in KiCad without rebuilding the PCM archive or reinstalling. The PCM archive
is only needed for release preparation or smoke-testing the packaged artifact.

The packaging decision (Option H hybrid model, keeping CLI and plugin in one
repository) is documented in
[ADR 0007](../../../docs-new/architecture/adr/0007-plugin-packaging-and-distribution.md).

## Prerequisites

```bash
# Clone and install jBOM in editable mode with dev dependencies
git clone <repo>
pip install -e ".[dev]"
```

## Dev loop setup — creating the symlink

### Symlink name: why `com_spcoast_jbom`, not `jbom`

The symlink target name **must match the PCM identifier** (`com.spcoast.jbom`
with dots replaced by underscores → `com_spcoast_jbom`). Using a bare `jbom`
as the symlink name shadows the importable `jbom` package on `sys.path` and
causes a circular import when KiCad loads the plugin. This constraint is
documented in ADR 0007 (finding F2).

### macOS

KiCad on macOS stores user scripting plugins under
`~/Library/Preferences/kicad/<ver>/scripting/plugins/`. This directory
does not exist by default; create it before symlinking.

```bash
# KiCad 10
mkdir -p ~/Library/Preferences/kicad/10.0/scripting/plugins
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Preferences/kicad/10.0/scripting/plugins/com_spcoast_jbom

# KiCad 9
mkdir -p ~/Library/Preferences/kicad/9.0/scripting/plugins
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Preferences/kicad/9.0/scripting/plugins/com_spcoast_jbom

# For other versions, substitute the version number in both paths.
```

Note: the user data path on macOS is `~/Library/Preferences/kicad/`, not
`~/Library/Application Support/kicad/`.

### Linux

```bash
ln -s "$PWD/src/jbom/plugin" \
  ~/.local/share/kicad/9.0/scripting/plugins/com_spcoast_jbom
```

### Windows

```powershell
New-Item -ItemType Junction `
  -Path "$env:APPDATA\kicad\9.0\scripting\plugins\com_spcoast_jbom" `
  -Target "$PWD\src\jbom\plugin"
```

Windows requires developer mode to create symlinks without administrator
privileges. A junction (as above) is a viable alternative.

## Activating the plugin in KiCad

The jBOM plugin is a KiCad ActionPlugin that registers a toolbar button in
the PCB editor (Pcbnew), not in the schematic editor (Eeschema).

1. Open the **PCB Editor** (Pcbnew) in KiCad.
2. Open **Tools → Scripting Console**.
3. Run `import pcbnew; pcbnew.LoadPlugins()` to force a plugin rescan, or
   simply close and reopen Pcbnew.
4. The jBOM toolbar button should appear in the right-hand toolbar.

## How the sys.path bootstrap works

`src/jbom/plugin/__init__.py` adds two entries to `sys.path` at load time:

1. **`_this_dir`** — the plugin directory itself. In a PCM install this is
   `${KICADX_3RD_PARTY}/plugins/com_spcoast_jbom/`, which contains the
   vendored `jbom/` package. In the dev symlink case it resolves to
   `src/jbom/plugin/` in the repository tree.

2. **`_src_dir`** — two levels up from `plugin/`, which is `src/` in the
   dev tree. This puts the editable `jbom` source on `sys.path` so
   `import jbom` finds the live source without a separate `pip install`
   into KiCad's bundled Python.

In a PCM install both paths are added; `_src_dir` resolves to the PCM
plugins parent directory, which is harmless (no `jbom` package there).

## KiCad SWIG / CPython GC gotcha

KiCad's ActionPlugin registration stores a **C++ pointer** to the plugin
object via SWIG. If the Python wrapper is created as a temporary and no
Python-level reference is kept, CPython's garbage collector will collect
the Python object between toolbar clicks, leaving KiCad with a dangling
C++ pointer. The toolbar button appears to work on the first click but
silently does nothing on subsequent clicks.

Always keep a module-level reference:

```python
# Correct — module-level reference prevents GC collection
_plugin_instance = JBOMFabricationPlugin()
_plugin_instance.register()

# Wrong — temporary object collected between clicks
JBOMFabricationPlugin().register()
```

This applies to any KiCad ActionPlugin, not just jBOM.

## Building the PCM archive

```bash
# Produces dist/jbom-pcm-{version}.zip
python scripts/build_pcm_package.py

# Also update metadata.json with computed sha256 and sizes (release prep)
python scripts/build_pcm_package.py --update-metadata
```

The archive can be installed manually via **KiCad → Plugin Manager →
Install from File** for smoke-testing without a GitHub release.

## Running the plugin test suite

The pure-Python plugin modules (`options.py`, `__init__.py`) are testable
without KiCad or wxPython:

```bash
pytest tests/plugin/ -v
```

The dialog (`dialog.py`) and the ActionPlugin class (`plugin.py`) import
`wx` and `pcbnew` respectively. These can only be exercised inside a live
KiCad instance. Use the dev-loop symlink for manual smoke-testing of the
dialog and toolbar integration.

## Troubleshooting

### "import jbom fails" inside the KiCad Scripting Console

The symlink name is almost certainly `jbom` instead of `com_spcoast_jbom`.
Check:

```bash
ls -la ~/Library/Preferences/kicad/10.0/scripting/plugins/
```

If you see `jbom -> ...` instead of `com_spcoast_jbom -> ...`, remove and
recreate the symlink:

```bash
rm ~/Library/Preferences/kicad/10.0/scripting/plugins/jbom
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Preferences/kicad/10.0/scripting/plugins/com_spcoast_jbom
```

### Plugin does not appear in the toolbar

1. Verify the symlink exists and points to the correct directory.
2. Open the KiCad Scripting Console and run:
   ```python
   import pcbnew; pcbnew.LoadPlugins(); print("done")
   ```
3. Check **Help → Show Error Log** in KiCad for Python import errors.

### KiCad major version upgrade

KiCad major version upgrades use a new versioned directory under
`~/Library/Preferences/kicad/`. Recreate the symlink pointing at the new
version path:

```bash
mkdir -p ~/Library/Preferences/kicad/10.0/scripting/plugins
ln -s "$PWD/src/jbom/plugin" \
  ~/Library/Preferences/kicad/10.0/scripting/plugins/com_spcoast_jbom
```

## Related

- [ADR 0007](../../../docs-new/architecture/adr/0007-plugin-packaging-and-distribution.md) — plugin packaging decision (Option H hybrid model)
- `scripts/build_pcm_package.py` — PCM archive builder
- `src/jbom/plugin/` — plugin source tree
- [kicad-plugin-setup skill](../kicad-plugin-setup/SKILL.md) — end-user Eeschema BOM plugin registration
