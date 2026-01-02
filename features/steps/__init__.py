"""
BDD step definitions package for jBOM.

Implements the QC Analytics systematic approach for behave step loading:
https://qc-analytics.com/2019/10/importing-behave-python-steps-from-subdirectories/

Domains:
- shared.py: Cross-domain step definitions
- annotate/: Back-annotation step definitions
- bom/: Bill of Materials step definitions
- error_handling/: Error handling step definitions
- inventory/: Inventory management step definitions
- pos/: Pick-and-place step definitions
- search/: Part search step definitions
"""

import os
import pkgutil

__all__ = []
PATH = [os.path.dirname(__file__)]

for loader, module_name, is_pkg in pkgutil.walk_packages(PATH):
    __all__.append(module_name)
    try:
        _module = loader.find_module(module_name).load_module(module_name)
        globals()[module_name] = _module
    except Exception as e:
        # Log import errors but continue with other modules
        import warnings

        warnings.warn(f"Failed to import step module '{module_name}': {e}")
