---
name: behave-subdirectory-loading
description: Procedural solution for configuring behave to load step definitions from subdirectory packages. Use when organizing behave step definitions into domain-specific subdirectories and encountering "Undefined step" errors, or when setting up a new subdirectory-based step structure for a behave feature suite.
---

# behave-subdirectory-loading

Behave does not automatically discover step definitions in subdirectories.
When steps are organized into domain-specific subdirectory packages, behave
reports "Undefined step. Rest part of scenario is skipped" for any step
defined outside the flat `steps/` directory. This skill describes the
self-contained fix used in jBOM.

Source: adapted from
<https://qc-analytics.com/2019/10/importing-behave-python-steps-from-subdirectories/>
(verify URL is still accessible; content reproduced here for reliability).

## When to use

- You are splitting a flat `steps/` directory into domain subdirectories and
  behave stops finding steps.
- You are adding a new domain subdirectory to an existing organized structure.
- You are onboarding a new feature area that warrants its own step package.

## Solution

Two steps: convert each subdirectory into a Python package, then add a
dynamic-import shim in `steps/__init__.py`.

### Step 1 — Convert subdirectories into packages

Add an empty `__init__.py` to every step subdirectory. The resulting
structure looks like this:

```
features/
└── steps/
    ├── __init__.py          ← dynamic-import shim (Step 2)
    ├── shared.py            ← cross-domain steps
    ├── bom/
    │   ├── __init__.py      ← empty
    │   └── component_matching.py
    ├── error_handling/
    │   ├── __init__.py      ← empty
    │   └── edge_cases.py
    └── <domain>/
        ├── __init__.py      ← empty
        └── <domain>_steps.py
```

### Step 2 — Dynamic import shim in `steps/__init__.py`

Replace (or create) `features/steps/__init__.py` with exactly this content:

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

The shim walks the `steps/` directory tree and loads every `.py` module it
finds. Behave then sees all step definitions regardless of how deeply they
are nested.

**Why this pattern and not a direct `import`?** A naive
`from steps.bom import component_matching` in `__init__.py` triggers a
`KeyError: '__name__' not in globals` from behave's step-loading machinery.
The `pkgutil.walk_packages` + `loader.load_module` approach bypasses that
constraint.

## Tested with

- Python 3.10
- python-behave 1.2.7
- macOS

## Usage in jBOM

The jBOM feature suite uses this pattern to organize step definitions into:

- `shared.py` — cross-domain steps (component matching, BOM output assertions)
- `bom/` — Bill of Materials domain steps
- `error_handling/` — error handling and edge-case steps
- Additional domain directories as the feature suite grows

## Pitfalls to avoid

- **AmbiguousStep errors** — when two files define step patterns that match
  the same text. Disambiguate with more specific wording or unique parameter
  names. The dynamic loader surfaces all definitions simultaneously, so
  conflicts that would be invisible in a flat structure become errors here.
- **Step parameter name collisions** — steps that share a parameter name
  (e.g. `{name}`) across files can create unexpected matches. Keep parameter
  names semantically specific to their domain.
- **Forgetting `__init__.py`** — every level of a new subdirectory must have
  one, or `pkgutil.walk_packages` will not descend into it.

## Adding a new domain directory

```bash
# Create the directory and make it a package
mkdir features/steps/<domain>
touch features/steps/<domain>/__init__.py

# Add your step file
touch features/steps/<domain>/<domain>_steps.py
```

No changes to `features/steps/__init__.py` are needed; the shim picks up
the new package automatically on the next behave run.

## Related

- [`docs-new/README.md`](../../../docs-new/README.md) — documentation charter
- [jBOM WARP.md](../../../WARP.md) — project workflow rules; see Testing
  Requirements for how behave is run in this project
- [`git-workflow`](../git-workflow/SKILL.md) — commit and PR procedure
