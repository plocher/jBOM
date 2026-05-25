---
name: extend-jbom
description: Use when adding a new jBOM CLI command, domain service, inventory file format, package type, component classifier, output column preset, or fabricator profile. Covers registration patterns, service skeletons, extension points in common/ and services/, and required testing steps. Also applicable when an agent needs to understand stable extension contracts vs. internal implementation details.
---

# extend-jbom

Procedural recipes for extending jBOM. Each recipe is self-contained and references
the relevant source file. Read
[`docs/design/architecture-overview.md`](../../docs/design/architecture-overview.md)
for the structural overview and
[`docs/design/service-command-architecture.md`](../../docs/design/service-command-architecture.md)
for the design rationale behind the patterns used here.

## When to use

- Adding a new `jbom <command>` subcommand
- Adding a new domain service (business logic with state)
- Supporting a new inventory file format (.ods, .tsv, etc.)
- Adding a new package type (footprint identifier)
- Injecting a custom component classifier for a non-standard KiCad library
- Defining fabricator-specific column presets or supplier output formats

---

## Adding a New CLI Command

CLI commands follow a simple two-step registration pattern. There is no plugin
registry — all commands are explicitly imported by `cli/main.py`.

**Step 1 — Create `src/jbom/cli/<command>.py`:**

```python
"""<command> command — thin CLI adapter."""
import argparse
import sys
from pathlib import Path

# Import from services or application, never the reverse
from jbom.services.schematic_reader import SchematicReader


def register_command(subparsers: argparse._SubParsersAction) -> None:
    """Register <command> with the argument parser."""
    parser = subparsers.add_parser(
        "<command>",
        help="One-line description for --help output",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Path to schematic or project directory (default: current directory)",
    )
    parser.add_argument("-o", "--output", help="Output file path")
    parser.set_defaults(handler=handle_<command>)


def handle_<command>(args: argparse.Namespace) -> int:
    """Handle <command>."""
    try:
        reader = SchematicReader()
        components = reader.load_components(Path(args.input))
        # ... your logic here ...
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
```

**Step 2 — Register in `src/jbom/cli/main.py`:**

```python
# Add to the imports at the top of create_parser():
from jbom.cli import bom, inventory, pos, ..., <command>

# Add inside create_parser():
<command>.register_command(subparsers)
```

Look at any existing command module (e.g., `cli/bom.py` or `cli/pos.py`) for a
complete example including fabricator flags, output modes, and verbose handling.

**Testing requirement:** Add a Gherkin feature file at
`features/<command>/<command>.feature`. The command must have at least one passing
scenario before merging. Unit tests for the handler function go in
`tests/cli/test_<command>.py`.

---

## Adding a New Domain Service

A service is any module in `services/` that has an `__init__` method with instance
state. Services encapsulate business logic; they never import from `cli/` or
`application/`.

**Service skeleton:**

```python
"""<ServiceName> — one-line description of what this service produces."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from jbom.common.types import Component, InventoryItem


@dataclass(frozen=True)
class <Service>Config:
    """Configuration for <ServiceName> behavior."""
    some_option: bool = False
    threshold: int = 50

    def __post_init__(self) -> None:
        if self.threshold < 0:
            raise ValueError("threshold must be non-negative")


class <ServiceName>:
    """<Brief description of the service's single responsibility>."""

    def __init__(self, config: <Service>Config) -> None:
        """Configure service behavior."""
        self.config = config
        self._state = self._build_state()

    def process(self, inputs: List[Component]) -> List[InventoryItem]:
        """Core business operation. (docstring required on public methods)"""
        # domain logic here
        return []

    def _build_state(self) -> dict:
        """Internal factory method: build operational state from config."""
        return {}
```

**Dependency rules:**
- May import from `common/` and other `services/` modules.
- Must NOT import from `application/` or `cli/`.
- Must NOT call `print()`, write files, or read `os.environ` directly; surface those
  as diagnostics in the return value or raise domain-specific exceptions.

**Testing requirement:** Unit tests go in `tests/services/test_<service_name>.py`.
Test the service in isolation using domain objects (`Component`, `InventoryItem`, etc.)
as inputs. Do not mock `common/` utilities — call them for real.

---

## Adding a New Inventory File Format

Inventory file format support lives entirely in `src/jbom/services/inventory_reader.py`.
All formats normalize to the same list of row-dict output; downstream matching code
is format-neutral.

**Steps:**

1. Add a guard-imported dependency at the top of `inventory_reader.py`:

```python
try:
    import yourlib
    HAS_YOURLIB = True
except ImportError:
    HAS_YOURLIB = False
```

2. Add the file extension to the format-detection block:

```python
def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".csv",):
        return "csv"
    if suffix in (".xlsx", ".xls"):
        return "excel"
    if suffix == ".numbers":
        return "numbers"
    if suffix in (".ods",):          # <-- add here
        return "ods"
    raise ValueError(f"Unsupported inventory format: {suffix}")
```

3. Implement the reader returning normalized row dicts:

```python
def _load_ods(self, path: Path) -> list[dict]:
    if not HAS_YOURLIB:
        raise ImportError(
            "Reading .ods files requires 'yourlib'. Install with: pip install yourlib"
        )
    # Load and normalize rows; ensure all field names are stripped strings
    rows = []
    # ... yourlib parsing here ...
    return rows
```

4. Wire it into `_load_file()`.

5. Add test coverage in `tests/services/test_inventory_reader.py` using a fixture
   file in `tests/fixtures/` and at least one Gherkin scenario in
   `features/inventory/`.

---

## Adding a New Package Type

Package matching in jBOM is driven by a single authoritative list, `SMD_PACKAGES` in
`src/jbom/common/packages.py`. Adding a new SMD package type is a one-liner.

**To add WLCSP support:**

```python
# In src/jbom/common/packages.py
SMD_PACKAGES = [
    ...,
    "wlcsp",   # <-- add here
]
```

That is the only change required. Automatic dash removal handles inventory naming
variants automatically: `wlcsp` in the list matches both `wlcsp` and `wl-csp` in
inventory and footprint strings.

For through-hole package types, add to `THROUGH_HOLE_PACKAGES` in the same file.

**Why this works:** `package_matching.py` uses `SMD_PACKAGES` directly for both
footprint extraction and inventory matching, with longer patterns matched first to
avoid substring conflicts. There are no separate extraction patterns or mapping tables
to maintain.

**Testing:** Add the new package to the relevant test cases in
`tests/common/test_package_matching.py`.

---

## Customizing Component Matching

### Extending the component type alias table

`COMPONENT_TYPE_MAPPING` in `src/jbom/common/constants.py` maps `lib_id` substrings
and prefixes to canonical component types (`RES`, `CAP`, `IND`, `LED`, etc.).

To add support for a non-standard library symbol that jBOM does not recognize:

```python
# In src/jbom/common/constants.py
COMPONENT_TYPE_MAPPING = {
    ...,
    "MyLib:MyCustomResistor": "RES",   # exact lib_id match
    "MyLib:Sensor_":          "IC",    # prefix match
}
```

Entries are checked in order; first match wins.

### Injecting a custom classifier

For more complex classification logic (e.g., a whole custom library with its own
naming scheme), implement the `ComponentClassifier` Protocol and pass it to
`get_component_type()`:

```python
from jbom.common.component_classification import get_component_type, ComponentClassifier


class MyLibClassifier:
    def classify(self, lib_id: str, footprint: str = "") -> str | None:
        """Return a type string or None to fall through to the default classifier."""
        if lib_id.startswith("MyLib:"):
            if "Resistor" in lib_id:
                return "RES"
            if "Capacitor" in lib_id:
                return "CAP"
            return "IC"
        return None  # fall through to HeuristicComponentClassifier


comp_type = get_component_type(lib_id, footprint, classifier=MyLibClassifier())
```

The default `HeuristicComponentClassifier` is used as fallback when your classifier
returns `None`.

### Adding category-specific fields

`CATEGORY_FIELDS` in `src/jbom/common/constants.py` controls which inventory columns
are automatically included for a given component category. To add fields for a new
category or extend an existing one:

```python
CATEGORY_FIELDS = {
    ...,
    "SENSOR": ["Sensitivity", "Range", "Interface"],
}
```

---

## Output Customization

### Fabricator-specific column presets

Fabricator profiles are loaded from `*.jbom.yaml` configuration files. To add a
new fabricator preset with custom output columns, create a profile file:

```yaml
# .jbom/myfab.jbom.yaml
fabricator:
  name: MyFab
  columns:
    - Reference
    - Value
    - Footprint
    - MPN
    - Manufacturer
```

For Python-side fabricator schema definitions, see
`src/jbom/config/fabricators.py`. The `extends:` key supports profile inheritance so
you can build on an existing fabricator preset.

### Field presets for CLI output

`FIELD_PRESETS` in `src/jbom/common/fields.py` maps preset names (prefixed with `+`)
to lists of field names. The user selects a preset with `-f +preset_name`. To add a
new preset:

```python
# In src/jbom/common/fields.py
FIELD_PRESETS = {
    ...,
    "+compact": ["Reference", "Value", "Footprint", "MPN"],
    "+full":    ["Reference", "Value", "Footprint", "MPN", "Manufacturer",
                 "LCSC", "Supplier", "SPN", "Match_Quality", "Priority"],
}
```

### Custom BOM aggregation strategy

`BOMGenerator` accepts an `aggregation_strategy` constructor parameter. The only
currently implemented strategy is `"value_footprint"` (groups components by matching
inventory item IPN + footprint). To implement a different strategy, add a handler in
`src/jbom/services/bom_generator.py` and route to it from the constructor. Follow
the Command/Query Separation rule: the strategy handler must return a new list of
`BOMEntry` objects without mutating its inputs.

---

## Pattern Reference

Three patterns appear throughout jBOM's extension surface. Understanding them helps
you write extensions that fit naturally:

**Strategy via constructor:** Services accept behavior flags at construction time, not
per-call. If your new service has two modes of operation, add a parameter to
`__init__` that selects the mode, not a parameter to each method.

**Factory methods:** Complex internal state is built by a private `_build_*` method,
keeping `__init__` readable. If your new service pre-computes a lookup table or index
from its configuration, do it in a factory method.

**Command/Query Separation:** Public methods that produce artifacts (commands) are
separate from public methods that inspect state (queries). Commands return a new
domain object; queries return a scalar or analysis result. If a method both modifies
state and returns analysis, split it.

---

## Related

- [`docs/design/architecture-overview.md`](../../docs/design/architecture-overview.md)
  — Module structure and key principles
- [`docs/design/service-command-architecture.md`](../../docs/design/service-command-architecture.md)
  — Design rationale for the service/command layering
- [`docs/architecture/adr/0013-domain-centric-design.md`](../../docs/architecture/adr/0013-domain-centric-design.md)
  — Formal architectural commitment
- [`docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md`](../../docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md)
  — Fabricator-aware selection decision
