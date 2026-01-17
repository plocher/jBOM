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

**Responsibility:** Find installed plugins, load their service modules

**Startup sequence:**
1. Scan for plugins (pip packages with `jbom.plugins` entry point)
2. Load each plugin's module registry
3. Build service catalog: `{plugin.module.service: function}`
4. Build workflow catalog: `{workflow_name: composition}`

**Result:**
- Service registry: All available service functions
- Workflow registry: All available commands

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

## Architectural Decisions Needed

### 1. Workflow Definition Format

**Question:** How are workflows defined and stored?

**Options:**
- Python functions (current) - Flexible but not composable
- YAML/JSON DSL - Composable but limited expressiveness
- Hybrid - Common workflows in DSL, complex ones in Python

**Recommendation:** Start with Python functions (lower risk), evolve to DSL as patterns emerge.

### 2. Service Discovery Mechanism

**Question:** How do workflows find and call services?

**Options:**
- Direct imports - `from plugin.module import service`
- Service registry - `registry.get("plugin.module.service")`
- Dependency injection - Services injected into workflow context

**Recommendation:** Service registry for discoverability and late binding.

### 3. Argument Mapping

**Question:** How do CLI arguments map to service parameters?

**Options:**
- Manual mapping in workflow code
- Automatic mapping via naming convention (args.project → project parameter)
- Explicit schema in workflow definition

**Recommendation:** Hybrid - naming conventions with explicit overrides in workflow definition.

### 4. Error Handling Strategy

**Question:** How do workflows handle service failures?

**Options:**
- Exception propagation - Services throw, workflow catches
- Result objects - Services return Result[value | error]
- Continuation passing - Services take success/failure callbacks

**Recommendation:** Exception propagation with workflow-level error handlers.

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

## Evolution Path

### Phase 1: Extract Service Modules
- Identify current jBOM functions that are services
- Group into logical modules (KiCadReader, InventoryService, etc.)
- Define clean interfaces

### Phase 2: Explicit Workflow Definitions
- Extract current command logic into explicit workflows
- Document service dependencies for each workflow
- Create workflow registry

### Phase 3: Plugin Architecture
- Package service modules as plugins
- Implement plugin discovery and loading
- Build service registry

### Phase 4: Workflow Composition
- Enable users to define custom workflows
- Provide workflow DSL (if needed)
- Support third-party workflow contributions

## Open Questions

1. **Service granularity:** How fine-grained should services be? (e.g., one service per file format, or one generic readInventory?)

2. **State management:** Are services stateless functions, or can they maintain state?

3. **Service versioning:** How do workflows specify required service versions?

4. **Workflow testing:** How do we test workflow compositions without executing full pipeline?

5. **Configuration:** Where does configuration live - in workflows, services, or both?

6. **Data contracts:** What are the types of KICAD_PROJECT, INVENTORY, BOM, etc.? How are they validated?

7. **Execution context:** How do workflows share data between steps (context object, return values, global state)?

## Conclusion

jBOM architecture centers on **workflows composing plugin services**:

- **Plugins provide services** - Reusable functions grouped by domain (KiCad access, inventory, BOM generation)
- **Workflows compose services** - Named command definitions that chain service calls
- **CLI maps to workflows** - User commands execute workflow compositions

The key challenge is **workflow execution** - how to practically turn workflow definitions into executable code. This requires resolving services from registry, mapping arguments, handling errors, and managing execution context.

Start with explicit Python workflows, evolve to more declarative/composable patterns as understanding deepens.
