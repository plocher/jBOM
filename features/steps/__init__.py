"""
BDD step definitions package for jBOM.

This module dynamically imports all step definitions from subdirectories
to make them available to behave's step discovery mechanism.

Domains:
- shared.py: Cross-domain step definitions
- bom/: Bill of Materials step definitions
- error_handling/: Error handling step definitions
"""

import os
import pkgutil

__all__ = []
PATH = [os.path.dirname(__file__)]

for loader, module_name, is_pkg in pkgutil.walk_packages(PATH):
    __all__.append(module_name)
    _module = loader.find_module(module_name).load_module(module_name)
    globals()[module_name] = _module
