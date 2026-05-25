# Service-Command Architecture

jBOM organizes code into four layers—`common/`, `services/`, `application/`, and
`cli/`—with dependency flowing strictly inward. This document describes the design
rationale for each layer boundary and the patterns used within them. The underlying
architectural commitment is recorded in
[ADR 0013 (Domain-Centric Design)](../architecture/adr/0013-domain-centric-design.md);
this document describes how ADR 0013 is currently instantiated in the codebase.

## The Service vs Common Axiom

The single most important structural rule: **the presence of an `__init__` method with
instance variables is what makes something a service**.

`services/` modules have state and behavior. They capture business processes,
maintain configuration established at construction time, and may call other
services. `BOMGenerator`, `SchematicReader`, and `InventoryMatcher` are services.

`common/` modules are stateless. They contain pure functions, data classes, constants,
and type definitions. They do not have `__init__` methods with instance state (frozen
dataclasses for configuration objects are the only exception). `Component`,
`InventoryItem`, `value_parsing`, and `component_classification` are common.

This distinction matters because it tells you where to look when something goes wrong.
If you want to know how components are classified, you look in `common/`; the answer
is a pure function. If you want to know how matching decisions are made across an
inventory, you look in `services/`; the answer involves state built from prior calls.

## Dependency Direction

Dependencies flow inward only:

```
cli/ → application/ → services/ → common/
```

A service may call another service, and common utilities may be used anywhere. What
is forbidden is the outward direction: `services/` never imports `application/` or
`cli/`; `common/` never imports anything outside itself. Violating this creates
circular imports that are difficult to debug and make it impossible to test services
in isolation.

The practical enforcement is naming: if you find yourself writing
`from jbom.cli import ...` inside a service, stop—something is wrong with the
design. Either the functionality belongs in the adapter layer, or there is a missing
abstraction in `common/` or `application/`.

## Multi-Source Inventory Architecture

jBOM accepts multiple inventory files on a single command invocation. The design
goal is to give users a primary stocking inventory and one or more fallback or
supplier-specific catalogs, with predictable, Priority-governed selection at
match time.

### How deduplication works

When multiple inventory files are loaded, they are merged through
`aggregate_with_deduplication_validation()`. The deduplication policy follows the
IPN (Internal Part Number) as the unit of identity:

- **Exact duplicates** (same IPN, same electrical spec, same supplier) are silently
  dropped. This is safe: two identical rows carry no additional information.

- **Supplier alternatives** (same IPN, different Manufacturer or MPN) are preserved
  as separate `InventoryItem` entries. An IPN may legitimately source from multiple
  suppliers; the inventory model embraces repeated IPN rows for this purpose.

- **Electrical conflicts** (same IPN, different Value, Package, or Tolerance) produce
  validation warnings. A consistent electrical spec within an IPN group is required;
  conflicting specs indicate a data entry error and are reported before matching
  proceeds.

The `Priority` column (1 = most desirable, higher = less desirable) governs which
supplier alternative is selected during fabricator-aware part filtering. Priority is
**not** a file-ordering concept: a row with Priority 1 in the second file beats a row
with Priority 2 in the first file. The `fabricator_inventory_selector.py` service
applies the priority ordering when narrowing candidates to what a specific fabricator
can source.

This model means the answer to "which item wins when the same part appears in two
files?" is always: the one with the better (lower) Priority, not the one that was
loaded first.

### Data model: pragmatic normalization

The inventory CSV uses a spreadsheet-compatible representation where supplier
alternatives for the same part repeat the IPN row with different Manufacturer and MPN
values:

```
IPN,Type,Value,Package,Manufacturer,MPN,Priority
IPN-10k-0603-R,resistor,10k,0603,Yageo,RC0603FR-0710KL,1
IPN-10k-0603-R,resistor,10k,0603,Vishay,CRCW060310K0FKEA,2
```

Conceptually this is a supplier alternatives table embedded in a flat file: the first
three fields define the component; the last three fields define one sourcing option.
The design deliberately keeps the format CSV-simple while enabling sophisticated
supplier selection. See
[ADR 0001 (Fabricator Inventory Selection)](../architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md)
for the decision that introduced fabricator-aware selection over the earlier
best-first-match-wins approach.

### Validation rules for multi-source inventories

`inventory_validator.py` checks IPN groups after merge:

- **Supplier field differences** (Manufacturer, Distributor, MPN, Priority): expected
  and desired.
- **Source metadata differences** (source, source_file): expected when loading from
  multiple files.
- **Electrical specification differences** (Value, Tolerance, Voltage, Package): a
  warning is required. Same IPN must have consistent electrical characteristics.
- **UUID differences**: expected when the same electrical spec appears from different
  suppliers.

### File safety

Production artifacts are never overwritten without an explicit `--force` flag. When
`--force` is used, `backup_service.py` creates a timestamped backup
(`filename.backup.YYYYMMDD_HHMMSS.ext`) before overwriting. This is a service-layer
concern, not a CLI concern: the safety guarantee applies regardless of which interface
triggered the write.

## Service Implementation Patterns

### Strategy via constructor parameters

Services accept behavior-governing parameters at construction time rather than per-call.
This keeps service instances immutable in their configuration and makes the behavior
contract readable at the call site:

```python
generator = BOMGenerator(aggregation_strategy="value_footprint")
matcher = InventoryMatcher(inventory_file=Path("inventory.xlsx"))
```

jBOM uses parameter-based strategies (a string or enum selecting from known
behaviors) rather than injected strategy objects. This keeps service APIs simple while
still allowing runtime behavior selection.

### Factory methods for internal objects

Services create domain objects through internal factory methods rather than
constructor logic. The factory method is private (prefix `_`) and named after what
it produces. This keeps constructors readable and encapsulates the complexity of
building internal state:

```python
class SomeService:
    def __init__(self, config: SomeConfig):
        self.config = config
        self._state = self._build_state(config)

    def _build_state(self, config: SomeConfig) -> InternalState:
        """Internal factory: build the state this service operates on."""
        ...
```

### Command/Query Separation

Public service methods are either commands (they modify state or produce output) or
queries (they read state without side effects). The distinction is carried in the
method signature: commands return the produced artifact; queries return a value or
analysis. No method should both modify state and return an analysis result.

Commands produce new domain objects rather than mutating their inputs. This enables
functional composition: the output of one service is passed as input to the next
without defensive copying.

## CLI Integration Patterns

### Application layer as orchestrator

The `application/` layer sits between adapters and services. It is responsible for:
translating adapter-specific inputs into typed domain configuration objects,
instantiating and calling services in the right sequence, collecting diagnostics, and
assembling the typed result that the adapter renders. It contains no business logic
of its own.

The workflow class for a command family lives at
`src/jbom/application/<command>_workflow.py` and exposes a single public method:
`.run(request) -> result`. The request is a frozen dataclass; the result carries both
the primary artifact and a `tuple[str, ...]` of diagnostic messages. Adapters consume
the diagnostics tuple and decide what to display.

### Adapter responsibilities

A CLI module in `cli/` has exactly four responsibilities:

1. Parse CLI flags and arguments.
2. Build the typed request and call `.run(request)` on the workflow.
3. Render diagnostics (conditionally, based on `--verbose` or severity).
4. Map the result to an exit code.

No business logic, field resolution, or matching belongs in a CLI module. When a CLI
module grows beyond ~50 lines of argument handling and output rendering, it is a sign
that application-layer logic has leaked into the adapter.

### Input translation

CLI arguments are translated to domain configuration objects before being passed to
any service. The translation typically lives in a `from_args(cls, args)` classmethod
on the configuration dataclass:

```python
@dataclass
class BOMOptions:
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "BOMOptions":
        return cls(
            inventory_sources=[Path(p) for p in args.inventory],
            smd_only=args.smd,
            verbose=args.verbose,
        )
```

This keeps the service interface independent of argparse—services accept typed
domain objects, not `argparse.Namespace` instances.

### Error translation

Domain-specific exceptions are caught at the application layer boundary and
translated to user-readable messages. The adapter receives either a successful result
or a raised exception with a `.user_message` attribute; it never parses exception
text to construct its own message.

Services may also return partial results with diagnostics rather than raising.
`BOMGenerator` includes diagnostics for unmatched components in the result contract
rather than raising an exception, because partial output is more useful than a hard
failure when some components simply have no inventory coverage.

### Diagnostic collection

Services always collect and return the full set of diagnostics in their result
contract (`tuple[str, ...]`). Adapters decide what to display and when. No service
module reads `os.environ` to gate diagnostic output; suppression is an adapter
concern only. Request dataclasses do not carry a `quiet` field for the same reason.

This rule ensures that the KiCad plugin (which surfaces diagnostics in a panel rather
than stderr) can always access the complete diagnostic set, even when the CLI user has
not passed `--verbose`.

## The application-as-orchestrator pattern in practice

A well-structured workflow module coordinates three to five services in a linear or
conditionally branching sequence:

```python
class BOMWorkflow:
    def run(self, request: BOMRequest) -> BOMResult:
        # 1. Resolve inputs
        project = ProjectFileResolver().resolve(request.project_path)
        inventory = self._load_inventory(request.inventory_paths)

        # 2. Extract domain objects
        components = SchematicReader().load_components(project.schematic)

        # 3. Match and generate
        matches = InventoryMatcher().match_all(components, inventory)
        entries, diagnostics = BOMGenerator().generate(matches, request.options)

        # 4. Return typed result (no file I/O here)
        return BOMResult(entries=entries, diagnostics=diagnostics)
```

File writing is delegated to a *friend serializer* service (`BOMWriter`) rather than
happening inside the workflow. This keeps the workflow as a pure orchestrator and
makes serialization independently testable. CLI adapters continue to render console
and stdout output; the friend-serializer pattern applies only when a workflow needs
to write a file artifact as part of its own contract (e.g., `FabricationWorkflow`
producing BOM and POS together).

---

*For the formal commitment to this design, see*
*[ADR 0013 (Domain-Centric Design)](../architecture/adr/0013-domain-centric-design.md).*
*For the fabricator-selection decision that introduced priority-based supplier*
*ranking, see*
*[ADR 0001 (Fabricator Inventory Selection)](../architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md).*
*Extension recipes for adding services, commands, and file format readers live in*
*the [extend-jbom skill](../../.agents/skills/extend-jbom/SKILL.md).*
