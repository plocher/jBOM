"""
BDD step definitions package for jBOM.

This module dynamically imports all step definitions from subdirectories
to make them available to behave's step discovery mechanism.
"""

import os
import pkgutil

__all__ = []

# Define the path to search within the current directory
PATH = [os.path.dirname(__file__)]

# Dynamically import all modules found in subdirectories
for loader, module_name, is_pkg in pkgutil.walk_packages(PATH):
    __all__.append(module_name)
    _module = loader.find_module(module_name).load_module(module_name)
    globals()[module_name] = _module
