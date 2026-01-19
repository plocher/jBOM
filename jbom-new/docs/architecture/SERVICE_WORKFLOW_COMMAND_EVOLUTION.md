# Service/Workflow/Command Architecture Evolution

## Problem Statement

Our initial "plugin" architecture conflated **modularity** with **plugins**, creating monolithic vertical slices that are tightly coupled and difficult to compose:

- **POS plugin**: PCB reader + POS generator + service logic + CLI
- **BOM plugin**: SCH reader + BOM generator + service logic + CLI
- **Inventory plugin**: Wants to enhance both BOM and POS + its own CLI

This creates the "inventory steps all over the other two" problem because we're trying to make monoliths interact through complex plugin extension mechanisms.

## Root Cause Analysis

1. **Conflated Concerns**: Mixed business logic, orchestration, and user interface
2. **Vertical Coupling**: Each "plugin" owns an entire vertical slice
3. **Interaction Complexity**: Needed complex mechanisms for monoliths to interact
4. **Limited Reuse**: Components buried inside monoliths can't be reused
5. **Testing Challenges**: Hard to test individual components in isolation

## Proposed Architecture: Service/Workflow/Command Decomposition

### **Layer 1: Services** (Pure Business Logic)
Focused, single-responsibility services with clear contracts:

```
src/jbom/services/
├── readers/
│   ├── schematic_reader.py      # Loads KiCad .kicad_sch files
│   ├── pcb_reader.py           # Loads KiCad .kicad_pcb files
│   └── inventory_reader.py     # Loads CSV inventory files
├── generators/
│   ├── bom_generator.py        # Creates BOM data structures
│   ├── pos_generator.py        # Creates POS data structures
│   └── inventory_generator.py  # Creates inventory data structures
├── matchers/
│   ├── inventory_matcher.py    # Matches components to inventory
│   └── component_converter.py  # Converts between formats
└── formatters/
    ├── csv_formatter.py        # Outputs CSV files
    ├── console_formatter.py    # Outputs console tables
    └── fabricator_formatter.py # Applies fabricator-specific formatting
```

**Service Characteristics**:
- Pure functions or stateless classes
- No CLI awareness
- No file I/O beyond their specific domain
- Easily testable in isolation
- Reusable across workflows

### **Layer 2: Workflows** (Orchestration)
Compose services to accomplish business goals:

```
src/jbom/workflows/
├── bom_workflows.py
│   ├── generate_basic_bom()
│   └── generate_inventory_enhanced_bom()
├── pos_workflows.py
│   ├── generate_basic_pos()
│   └── generate_inventory_enhanced_pos()
└── inventory_workflows.py
    ├── generate_project_inventory()
    ├── merge_inventories()
    └── search_enhance_inventory()
```

**Workflow Characteristics**:
- Coordinate multiple services
- Handle business logic flow
- No CLI awareness
- Return structured data
- Handle error scenarios

### **Layer 3: Commands** (User Interface)
Handle CLI concerns and user interaction:

```
src/jbom/commands/
├── bom_command.py           # Simple BOM generation
├── inventory_bom_command.py # Inventory-enhanced BOM
├── pos_command.py           # Simple POS generation
├── inventory_command.py     # Inventory management
└── search_command.py        # Part search functionality
```

**Command Characteristics**:
- Handle argument parsing
- Coordinate with workflows
- Handle output formatting
- Manage user feedback
- Error handling and help

## Benefits of This Architecture

### **1. True Modularity**
- Services are independently reusable
- Clear separation of concerns
- Easy to test individual components

### **2. Simple Composition**
```python
# Instead of complex plugin interaction:
def inventory_enhanced_bom(project, inventory_file, output):
    components = SchematicReader().load(project)
    inventory = InventoryReader().load(inventory_file)
    matches = InventoryMatcher().match(components, inventory)
    bom_data = BOMGenerator().generate(matches)
    CSVFormatter().write(bom_data, output)
```

### **3. Natural Evolution**
- Add new commands without touching existing ones
- Enhance workflows by composing additional services
- Replace implementations without changing interfaces

### **4. Clear Testing Strategy**
- **Unit tests**: Test services in isolation
- **Integration tests**: Test workflows with mocked services
- **End-to-end tests**: Test commands with real files

## Migration Strategy

### **Phase 1**: Extract Services (Current → Service Layer)
1. Extract `SchematicReader` from BOM plugin
2. Extract `PCBReader` from POS plugin
3. Extract `InventoryMatcher` from Inventory plugin
4. Create shared `CSVFormatter`, `ConsoleFormatter`

### **Phase 2**: Create Workflows (Service → Workflow Layer)
1. Create `generate_basic_bom` workflow using extracted services
2. Create `generate_inventory_enhanced_bom` workflow
3. Create `generate_basic_pos` workflow
4. Create inventory management workflows

### **Phase 3**: Refactor Commands (Plugin → Command Layer)
1. Replace monolithic plugin CLI handlers with focused commands
2. Commands use workflows, not services directly
3. Maintain backward compatibility during transition

### **Phase 4**: Cleanup (Remove Old Structure)
1. Remove "plugin" directories
2. Update CLI registration to use commands
3. Update documentation and examples

## Impact Analysis

### **TDD & Testing**
- **Simpler Unit Tests**: Pure services are easy to test
- **Focused Integration Tests**: Workflows test business logic flow
- **Clear Test Boundaries**: Each layer has distinct testing concerns
- **Faster Test Execution**: Mock services for workflow tests

### **Filesystem Layout**
- **Clear Organization**: Services/workflows/commands are obvious
- **Reduced Nesting**: No deep plugin directory structures
- **Logical Grouping**: Related functionality lives together
- **Easy Navigation**: Developers know where to find things

### **Development Focus**
- **Service Development**: Focus on pure business logic
- **Workflow Development**: Focus on composition and flow
- **Command Development**: Focus on user experience
- **Parallel Development**: Teams can work on different layers independently

## Example Usage Patterns

### **Simple BOM (unchanged experience)**
```bash
jbom bom project/ -o bom.csv
```
Uses: `SchematicReader` → `BOMGenerator` → `CSVFormatter`

### **Inventory-Enhanced BOM (new capability)**
```bash
jbom bom project/ --inventory parts.csv -o bom.csv
```
Uses: `SchematicReader` → `InventoryReader` → `InventoryMatcher` → `BOMGenerator` → `CSVFormatter`

### **Or New Command**
```bash
jbom inventory-bom project/ parts.csv -o bom.csv
```
Same workflow, different command entry point

## Success Metrics

1. **Reduced Coupling**: Services have no dependencies on CLI or other services
2. **Increased Reuse**: Services used by multiple workflows
3. **Simplified Testing**: Unit tests for services run in milliseconds
4. **Enhanced Composability**: New workflows created by composing existing services
5. **Maintainability**: Changes to one layer don't impact others

## Conclusion

This evolution from monolithic "plugins" to layered service/workflow/command architecture:
- Solves the inventory plugin's need to enhance other functionality
- Eliminates complex plugin interaction mechanisms
- Creates true modularity and reusability
- Simplifies testing and development
- Maintains backward compatibility during migration

The key insight: **The problem wasn't how to make monoliths interact—it was that we built monoliths in the first place.**
