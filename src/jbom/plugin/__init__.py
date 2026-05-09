"""jBOM KiCad ActionPlugin adapter.

This is the PCM-installable plugin entry point for the jBOM fabrication
workflow.  Importing this module in a CLI or test environment is safe and
inert — no ``pcbnew`` import is attempted and no ActionPlugin is registered.

Guard pattern
-------------
Mirrors Fabrication Toolkit's ``plugins/__init__.py``:

.. code-block:: python

    _is_standalone = "pcbnew" not in sys.modules or __name__ == "__main__"
    if not _is_standalone:
        from .plugin import JBOMFabricationPlugin
        JBOMFabricationPlugin().register()

``sys.path`` bootstrapping
--------------------------
This module adds two candidate directories to ``sys.path`` so that
``import jbom`` (and vendored runtime deps) succeeds in both deployment modes:

* **PCM install** — ``jbom/`` is vendored *inside* this plugin directory.
  Adding the plugin directory itself (``_this_dir``) makes it discoverable.

* **Dev loop (symlink)** — this directory is ``src/jbom/plugin/``, symlinked
  into KiCad's scripting plugins folder as ``com_spcoast_jbom``.  Adding
  ``src/`` (two levels up from ``plugin/``) makes the editable source tree
  discoverable without a separate ``pip install`` into KiCad's bundled Python.

The two paths are tried in order; the first one that contains a ``jbom``
package wins.

Dev-loop setup (macOS, KiCad 9)::

    ln -s "$PWD/src/jbom/plugin" \\
      ~/Library/Application\\ Support/kicad/9.0/scripting/plugins/com_spcoast_jbom

Important: use ``com_spcoast_jbom`` (not ``jbom``) as the symlink target name
to avoid a naming conflict with the importable ``jbom`` package when KiCad
adds the scripting plugins directory to ``sys.path``.
"""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# sys.path bootstrapping
# ---------------------------------------------------------------------------

# os.path.realpath (not abspath) is required here: abspath makes a path
# absolute but does NOT follow symlinks.  In the dev loop the plugin directory
# is a symlink, so abspath would resolve relative to the symlink location
# (e.g. .../scripting/plugins/com_spcoast_jbom/) instead of the actual source
# tree (src/jbom/plugin/).  realpath follows the symlink first.
_this_dir = os.path.dirname(os.path.realpath(__file__))

# Two levels up from ``src/jbom/plugin/`` lands at ``src/`` in the dev tree.
# In PCM mode (``${KICADX_3RD_PARTY}/plugins/com_spcoast_jbom/``) this
# resolves to ``${KICADX_3RD_PARTY}/plugins/``, which is already in sys.path
# by the time KiCad loads us — adding it again is harmless.
_src_dir = os.path.dirname(os.path.dirname(_this_dir))

for _p in (_this_dir, _src_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# ActionPlugin registration — KiCad context only
# ---------------------------------------------------------------------------

# ``pcbnew`` is pre-loaded by KiCad's embedded Python before any plugin
# ``__init__.py`` runs.  In CLI/test environments it is never present.
_is_standalone = "pcbnew" not in sys.modules or __name__ == "__main__"

if not _is_standalone:  # pragma: no cover — only executes inside KiCad
    try:
        from .plugin import JBOMFabricationPlugin

        JBOMFabricationPlugin().register()
    except Exception:
        import traceback

        traceback.print_exc()
