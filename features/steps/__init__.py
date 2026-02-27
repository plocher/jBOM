"""Step definitions for jBOM BDD tests.

This module enables behave to discover step definitions in subdirectories.
See: docs/development_notes/BEHAVE_SUBDIRECTORY_LOADING.md
"""

import importlib.util
import os
import pkgutil
import sys

__all__ = []
PATH = [os.path.dirname(__file__)]

for _finder, module_name, is_pkg in pkgutil.walk_packages(PATH):
    __all__.append(module_name)
    _spec = _finder.find_spec(module_name)
    if _spec is not None:
        _module = importlib.util.module_from_spec(_spec)
        sys.modules[module_name] = _module
        _spec.loader.exec_module(_module)
        globals()[module_name] = _module
