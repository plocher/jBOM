# Behave Subdirectory Loading Solution

## Problem
Behave doesn't automatically discover step definitions in subdirectories. When organizing steps into domain-specific subdirectories, behave complains with "Undefined step. Rest part of scenario is skipped".

## Solution
From: https://qc-analytics.com/2019/10/importing-behave-python-steps-from-subdirectories/

### Step 1: Convert subdirectories into modules
Add empty `__init__.py` files in every step subdirectory:
```
features/
+-- steps/
    +-- __init__.py
    +-- bom/
    │   +-- __init__.py
    │   +-- component_matching.py
    │   +-- shared.py
    +-- error_handling/
        +-- __init__.py
        +-- edge_cases.py
```

### Step 2: Dynamic import in steps/__init__.py
Add this code to `features/steps/__init__.py`:

```python
import os
import pkgutil

__all__ = []
PATH = [os.path.dirname(__file__)]

for loader, module_name, is_pkg in pkgutil.walk_packages(PATH):
    __all__.append(module_name)
    _module = loader.find_module(module_name).load_module(module_name)
    globals()[module_name] = _module
```

## Result
- Behave successfully loads step definitions from all subdirectories
- Maintains domain organization
- Avoids the `'__name__' not in globals` KeyError that occurs with import-based approaches

## Tested With
- Python 3.10
- python-behave 1.2.7
- macOS

## Usage in jBOM Project
Successfully implemented for organizing BDD step definitions into:
- `shared.py` - Cross-domain steps
- `bom/` - Bill of Materials domain steps
- `error_handling/` - Error handling domain steps
- Other domain directories as needed

## Important Notes
- Watch for AmbiguousStep errors when multiple files define similar step patterns
- Step parameter names matter for avoiding conflicts
- This approach loads ALL .py files in the steps directory tree
