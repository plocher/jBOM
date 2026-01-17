# jBOM Workflow Architecture

## Domain Context

**jBOM exists to transform KiCad projects into fabrication outputs.** Users have KiCad schematics/PCBs and need BOMs, placement files, inventory reports, etc. for manufacturing.

The workflow pattern:
1. **Ingest** - Read KiCad projects, inventory spreadsheets
2. **Process** - Match components, group, filter, enrich with data
3. **Output** - Generate fabricator-specific files (CSV, reports)

## Core Architectural Concept

**Plugins provide reusable service modules (APIs).**
**Workflows compose those services into named commands.**

```
Plugin Modules (Services)        Workflows (Command Compositions)
├─ KiCadReader                  ├─ bom: compose(readProject, createBOM, print)
├─ InventoryService             ├─ pos: compose(readPCB, extractPlacement, print)
├─ BOMGenerator                 └─ inventory: compose(scanProject, buildInventory, print)
├─ PlacementExtractor
└─ OutputFormatters
```

A workflow is **executable command definition** that chains service calls.

## Plugin Service Modules

Plugins provide **cohesive sets of related services**:

### Example: Inventory-Aware BOM Plugin

**Plugin Identity:**
- Name: `inventory_aware_bom`
- Version: `2.0.0`
- Provides: Services for BOM generation with inventory matching

**Module: KiCadReader**
Services for reading KiCad project data:
```python
KICAD_PROJECT = readProject(path)                    # Load project metadata
COMPONENT_LIST = readSchematic(project)              # Extract component list
PCB_DATA = readPCB(project)                         # Load PCB for placement
HIERARCHY = readHierarchy(project)                  # Get hierarchical structure
```

**Module: InventoryService**
Services for inventory data access:
```python
INVENTORY = readInventoryCSV(path)                   # CSV format
INVENTORY = readInventoryExcel(path)                 # Excel format
INVENTORY = readInventoryNumbers(path)               # Apple Numbers
INVENTORY = readInventoryAirtable(url, key)          # Airtable API
INVENTORY = combineInventories([inv1, inv2, ...])    # Federate multiple sources
INVENTORY = createInventoryFromProject(components)   # Generate from schematic
```

**Module: BOMGenerator**
Services for BOM generation and manipulation:
```python
BOM = createBOM(components, inventory, options)      # Generate BOM with matching
BOM = filterBOM(bom, filters)                       # Apply filters (SMD-only, etc.)
BOM = enrichBOM(bom, fabricator)                    # Add fabricator-specific fields
MATCHES = matchComponent(component, inventory)       # Find matches for one component
```

**Module: OutputFormatter**
Services for output generation:
```python
printBOMcsv(bom, path, fields)                      # CSV output
printBOMtable(bom, fields)                          # Console table
printBOMjson(bom, path)                             # JSON output
```

## Workflow Definitions

Workflows are **named compositions of service calls**. They define the command the user invokes.

### Workflow: `bom`

**Description:** Generate Bill of Materials for fabrication

**Composition:**
```python
workflow "bom":
    # Input phase
    project = KiCadReader.readProject(args.project)
    components = KiCadReader.readSchematic(project)

    # Optional inventory
    if args.inventory:
        inventory = InventoryService.combineInventories([
            InventoryService.readInventory(path) for path in args.inventory
        ])
    else:
        inventory = InventoryService.createInventoryFromProject(components)

    # Processing phase
    options = BOMOptions(
        fabricator=args.fabricator,
        smd_only=args.smd_only,
        verbose=args.verbose
    )
    bom = BOMGenerator.createBOM(components, inventory, options)

    if args.fabricator:
        bom = BOMGenerator.enrichBOM(bom, args.fabricator)

    # Output phase
    if args.output == "console":
        OutputFormatter.printBOMtable(bom, args.fields)
    else:
        OutputFormatter.printBOMcsv(bom, args.output, args.fields)
```

**CLI Mapping:**
```bash
jbom bom project/ -i inv.csv --jlc -o bom.csv
```

### Workflow: `inventory`

**Description:** Generate or update inventory from projects

**Composition:**
```python
workflow "inventory":
    # Scan multiple projects
    all_components = []
    for project_path in args.projects:
        project = KiCadReader.readProject(project_path)
        components = KiCadReader.readSchematic(project)
        all_components.extend(components)

    # Create inventory
    inventory = InventoryService.createInventoryFromProject(
        all_components,
        merge_existing=args.update
    )

    # Output
    OutputFormatter.printInventorycsv(inventory, args.output)
```

### Workflow: `pos`

**Description:** Generate placement file for fabrication

**Composition:**
```python
workflow "pos":
    project = KiCadReader.readProject(args.project)
    pcb_data = KiCadReader.readPCB(project)

    placement = PlacementExtractor.extractPlacement(pcb_data)

    if args.fabricator:
        placement = PlacementExtractor.transformForFabricator(
            placement,
            args.fabricator
        )

    OutputFormatter.printPOScsv(placement, args.output)
```

## Architectural Components

### 1. Plugin Discovery & Loading

**Responsibility:** Find and load plugin service modules

**Two-tier approach:**

#### Core Plugins (Bundled)
Built into jBOM, always available:
```
src/jbom/plugins/
├── inventory_aware_bom/
│   ├── __init__.py          # Plugin metadata
│   ├── kicad_reader.py      # Service module
│   ├── inventory_service.py # Service module
│   ├── bom_generator.py     # Service module
│   └── workflows.yaml       # Workflow definitions
└── placement/
    ├── __init__.py
    ├── pcb_reader.py
    └── workflows.yaml
```

**Discovery:** Static filesystem scan at startup
- Scan `src/jbom/plugins/` directory
- Load each plugin's `__init__.py` for metadata
- Import service modules
- Load workflow definitions from `workflows.yaml`

#### Extended Plugins (User-installed)
Installed via `jbom install <plugin>`, stored locally:
```
~/.jbom/plugins/
├── validation/
│   ├── plugin.yaml         # Plugin metadata
│   ├── rules_engine.py     # Service module
│   └── workflows.yaml      # Workflow definitions
└── cost_analysis/
    ├── plugin.yaml
    ├── pricing_service.py
    └── workflows.yaml
```

**Installation mechanism:**
```bash
# Install plugin from git repo
$ jbom install github:user/jbom-validation-plugin

# Or from local directory
$ jbom install /path/to/plugin/

# List installed plugins
$ jbom plugins list

# Uninstall
$ jbom uninstall validation
```

**What `jbom install` does:**
1. Downloads/copies plugin to `~/.jbom/plugins/<name>/`
2. Validates plugin structure (required files, metadata)
3. Registers in `~/.jbom/plugins/registry.json`
4. Available on next jBOM invocation

**Discovery:** Static filesystem scan at startup
- Scan `~/.jbom/plugins/` directory
- Load each plugin's `plugin.yaml` for metadata
- Import service modules (Python modules in plugin directory)
- Load workflow definitions

**Combined registry:**
```python
# At startup, jBOM builds:
service_registry = {
    'inventory_aware_bom.KiCadReader.readProject': <function>,
    'inventory_aware_bom.BOMGenerator.createBOM': <function>,
    'validation.RulesEngine.validateDesign': <function>,  # User plugin
    # ...
}

workflow_registry = {
    'bom': <workflow_definition>,
    'pos': <workflow_definition>,
    'validate': <workflow_definition>,  # From user plugin
    # ...
}
```

**No runtime pip dependency.** All discovery is filesystem-based, explicit installation.

**Result:**
- Service registry: All available service functions (core + installed)
- Workflow registry: All available commands (core + installed)

### 2. CLI Parser & Validator

**Responsibility:** Parse command line, validate against workflow schema

**Process:**
1. User invokes: `jbom <workflow> <args>`
2. Lookup workflow definition from registry
3. Extract required arguments from workflow composition
4. Parse and validate CLI arguments
5. Return validated argument object

**Example for `bom` workflow:**
```
Required: project (from readProject)
Optional: inventory (from readInventory), output, fabricator, smd_only
```

### 3. Workflow Executor

**Responsibility:** Execute workflow composition with validated arguments

**Challenge:** Turn workflow definition into executable code

**Options for workflow execution:**

#### Option A: Python Functions (Current Pattern)
Workflows are Python functions that call services:
```python
# Plugin provides
def execute_bom_workflow(args):
    project = readProject(args.project)
    components = readSchematic(project)
    # ... rest of workflow
```

**Problem:** Requires writing Python code for each workflow. Not composable.

#### Option B: Declarative Workflow DSL
Workflows defined in data (YAML/JSON), interpreted at runtime:
```yaml
workflow:
  name: bom
  steps:
    - service: KiCadReader.readProject
      input: args.project
      output: project

    - service: KiCadReader.readSchematic
      input: project
      output: components

    - service: InventoryService.readInventory
      input: args.inventory
      output: inventory
      optional: true

    - service: BOMGenerator.createBOM
      inputs: [components, inventory, options]
      output: bom

    - service: OutputFormatter.printBOMcsv
      inputs: [bom, args.output, args.fields]
```

**Executor interprets steps:**
```python
def execute_workflow(workflow_def, args):
    context = {'args': args}  # Execution context

    for step in workflow_def.steps:
        service = resolve_service(step.service)
        inputs = [context[inp] for inp in step.inputs]
        result = service(*inputs)
        context[step.output] = result

    return context
```

**Benefits:**
- Workflows are data, not code
- Can be extended/modified without Python
- Easy to validate, visualize, test
- Plugins provide services, users compose workflows

#### Option C: Pipeline/Chain Pattern
Workflows are chains of transformations:
```python
workflow = (
    Pipeline()
    .then(readProject)
    .then(readSchematic)
    .then(lambda comps: createBOM(comps, inventory, options))
    .then(lambda bom: printBOMcsv(bom, output, fields))
)

result = workflow.execute(args.project)
```

**Compromise:** Balance between flexibility and simplicity.

## Architectural Decisions

### 1. Workflow Definition Format

**Decision:** Pipeline/Chain pattern (Option C)

**Rationale:** Maps well to Gherkin BDD methodology. Workflows are readable sequences of transformations that mirror test scenarios.

```python
workflow_bom = (
    Pipeline()
    .then(readProject)                    # GIVEN a KiCad project
    .then(readSchematic)                  # WHEN I read the schematic
    .then(lambda c: createBOM(c, []))     # AND generate a BOM
    .then(lambda b: printBOMcsv(b, out))  # THEN output CSV
)
```

Gherkin scenario structure directly informs workflow steps.

### 2. Service Discovery Mechanism

**Decision:** Service registry with late binding

**Rationale:** Enables plugin discoverability, testing with mocks, and flexibility in service resolution.

```python
# Registry built at startup from filesystem scan
service_registry = ServiceRegistry()
service_registry.scan("src/jbom/plugins/")      # Core plugins
service_registry.scan("~/.jbom/plugins/")       # User plugins

# Workflows resolve services from registry
readProject = service_registry.get("kicad.readProject")
```

No runtime pip dependency - purely filesystem-based discovery.

### 3. Argument Mapping

**Decision:** Start simple, evolve to hybrid

**Bootstrap:** Manual mapping in workflow code
```python
def execute_bom(args):
    project = readProject(args.project)
    # Explicit, clear, no magic
```

**Future evolution:** Naming conventions with overrides (once patterns emerge)
```python
# Automatic: args.project → project parameter
# Override: @arg("inventory", source="args.inventory_files")
```

**Rationale:** Don't get stuck in fiddly details during bootstrap. Encapsulate mapping logic for future evolution.

### 4. Error Handling Strategy

**Decision:** Exception propagation with workflow-level handlers

**Rationale:** Python-idiomatic, familiar, sufficient for needs.

```python
try:
    result = workflow.execute(args)
except FileNotFoundError as e:
    print(f"Error: {e}")
    return 1
except ValidationError as e:
    print(f"Invalid input: {e}")
    return 1
```

Workflows can add specific error handling for their domain.

## Key Architectural Relationships

**User ↔ CLI Parser**
- User invokes workflow command with arguments
- Parser validates against workflow schema

**CLI Parser ↔ Workflow Registry**
- Parser queries: "What arguments does workflow X need?"
- Registry provides workflow definition

**Workflow Executor ↔ Service Registry**
- Executor queries: "Get me service plugin.module.service"
- Registry provides callable service function

**Workflow ↔ Plugin Services**
- Workflow orchestrates multiple service calls
- Services are stateless, composable functions

**Plugin ↔ Service Modules**
- Plugin groups related services into modules
- Modules provide cohesive service sets

## Bootstrap Plan: Build New System in Parallel

**Strategy:** Don't evolve existing jBOM - build new system from scratch using BDD/TDD.

**Approach:**
1. **Gherkin features** define expected behavior
2. **Functional tests** (step definitions) validate behavior
3. **Implementation** makes tests pass
4. **Unit tests** for core abstractions (after patterns emerge)

**Parallel development:** Existing jBOM continues working while new system is built.

### Step 1: Minimal Viable Core (Week 1-2)

**Goal:** Prove the pattern with simplest possible implementation

**Features to implement:**
```gherkin
Feature: Read KiCad Project
  Scenario: Read schematic components
    Given a KiCad project at "test_project/"
    When I read the schematic
    Then I should get a list of components
    And each component should have reference, value, footprint

Feature: Simple BOM Generation
  Scenario: Generate BOM without inventory
    Given a KiCad project with components
    When I generate a BOM
    Then components should be grouped by value and footprint
    And output should include reference, quantity, value, footprint
```

**Services to implement:**
- `KiCadReader.readProject(path)` - Read .kicad_sch
- `KiCadReader.readSchematic(project)` - Extract components
- `BOMGenerator.createBOM(components)` - Group components
- `OutputFormatter.printBOMcsv(bom, path)` - Write CSV
- `OutputFormatter.printBOMtable(bom)` - Console table

**Workflow to implement:**
```python
workflow_bom = (
    Pipeline()
    .then(KiCadReader.readProject)
    .then(KiCadReader.readSchematic)
    .then(BOMGenerator.createBOM)
    .then(OutputFormatter.printBOMcsv)
)
```

**Infrastructure:**
- Basic plugin discovery (scan `src/jbom/plugins/`)
- Service registry (dict of name → function)
- Workflow registry (dict of name → Pipeline)
- CLI parser (argparse, just `jbom bom <project>`)

**Success criteria:**
```bash
$ jbom-new bom test_project/ -o bom.csv
# Works! Generated minimal BOM
```

### Step 2: Add POS Workflow (Week 3)

**Goal:** Prove plugin system works for second workflow

**New features:**
```gherkin
Feature: Generate Placement File
  Scenario: Extract component placement from PCB
    Given a KiCad PCB file
    When I generate placement data
    Then output should include designator, x, y, rotation, side
```

**New services:**
- `KiCadReader.readPCB(project)` - Read .kicad_pcb
- `PlacementExtractor.extractPlacement(pcb)` - Get coordinates
- `OutputFormatter.printPOScsv(placement, path)` - Write POS

**New workflow:**
```python
workflow_pos = (
    Pipeline()
    .then(KiCadReader.readProject)
    .then(KiCadReader.readPCB)
    .then(PlacementExtractor.extractPlacement)
    .then(OutputFormatter.printPOScsv)
)
```

**Success criteria:**
- Two workflows work independently
- Share `KiCadReader` services (reusability proven)
- Both discoverable via `jbom-new --help`

### Step 3: Configuration System (Week 4)

**Goal:** Prove configuration mechanism

**Features:**
```gherkin
Feature: Configuration
  Scenario: Load user configuration
    Given a config file at "~/.jbom/config.yaml"
    When jBOM starts
    Then services should use configured defaults
```

**Config structure:**
```yaml
core:
  default_output_format: csv

plugins:
  bom:
    group_by: [value, footprint]
```

**Config access:**
```python
config = Config.load()  # Discovers and merges files
plugin_config = config.plugins.bom
```

### Step 4: User Plugin Installation (Week 5)

**Goal:** Prove extensibility with user plugins

**Implement:**
- `jbom-new install /path/to/plugin/` command
- Copy plugin to `~/.jbom/plugins/`
- Scan both core and user plugins at startup
- Simple validation (required files exist)

**Test with sample plugin:**
```bash
$ jbom-new install ./sample-validation-plugin/
Installed validation v1.0.0

$ jbom-new plugins list
Core plugins:
  bom v1.0.0
  pos v1.0.0

User plugins:
  validation v1.0.0

$ jbom-new validate project/
# User plugin workflow executes!
```

### Step 5: Inventory Integration (Week 6+)

**Goal:** Add back real-world complexity incrementally

**Add services:**
- `InventoryService.readInventoryCSV(path)`
- `BOMGenerator.matchInventory(component, inventory)`
- Enhanced `createBOM(components, inventory)`

**Extend BOM workflow:**
```python
workflow_bom_with_inventory = (
    Pipeline()
    .then(KiCadReader.readProject)
    .then(KiCadReader.readSchematic)
    .then(lambda c: (c, InventoryService.readInventoryCSV(args.inventory)))
    .then(lambda data: BOMGenerator.createBOM(*data))
    .then(OutputFormatter.printBOMcsv)
)
```

**Continue adding:**
- Excel/Numbers inventory formats
- Fabricator enrichment
- Advanced filtering
- Field customization

**Each addition:**
1. Write Gherkin scenario
2. Implement step definitions
3. Make tests pass
4. Refine based on learnings

### Success Metrics

**After Step 4, we have:**
- ✅ Proven pattern (services + workflows + plugins)
- ✅ BDD/TDD foundation
- ✅ Working CLI
- ✅ Configuration system
- ✅ Plugin extensibility
- ✅ Clean, testable code
- ✅ Foundation for expansion

**Open questions answered by implementation:**
- Service granularity → Emerges from use
- Data contracts → Defined by what tests need
- Execution context → Becomes clear in pipeline implementation
- Many others → Solved when encountered, not prematurely

## Open Questions

1. **Service granularity:** How fine-grained should services be? (e.g., one service per file format, or one generic readInventory?)

2. **State management:** Are services stateless functions, or can they maintain state?

3. **Plugin compatibility:** How do we handle core vs. user plugins depending on each other?

4. **Workflow testing:** How do we test workflow compositions without executing full pipeline?

5. **Configuration:** Where does configuration live - in workflows, services, or both?

6. **Data contracts:** What are the types of KICAD_PROJECT, INVENTORY, BOM, etc.? How are they validated?

7. **Execution context:** How do workflows share data between steps (context object, return values, global state)?

8. **Plugin sandboxing:** Should user plugins run in restricted environment? Security model?

9. **Plugin updates:** How does `jbom install` handle updates? Version pinning?

## Conclusion

jBOM architecture centers on **workflows composing plugin services**:

- **Plugins provide services** - Reusable functions grouped by domain (KiCad access, inventory, BOM generation)
- **Workflows compose services** - Named command definitions that chain service calls
- **CLI maps to workflows** - User commands execute workflow compositions

The key challenge is **workflow execution** - how to practically turn workflow definitions into executable code. This requires resolving services from registry, mapping arguments, handling errors, and managing execution context.

Start with explicit Python workflows, evolve to more declarative/composable patterns as understanding deepens.
