# Fixture Component Standards for jBOM-New

This document defines the standardized component patterns used across all jbom-new test fixtures and scenarios.

## Standard Test Components

Based on analysis of existing jbom-new feature files and tests, these components are used consistently across all scenarios:

### Basic Components
1. **R1** - Standard test resistor
   - **Value**: 10kΩ
   - **Package**: 0603 (1608 metric)
   - **Footprint**: `Resistor_SMD:R_0603_1608Metric`
   - **Symbol**: `Device:R`

2. **C1** - Standard test capacitor
   - **Value**: 100nF
   - **Package**: 0603 (1608 metric)
   - **Footprint**: `Capacitor_SMD:C_0603_1608Metric`
   - **Symbol**: `Device:C`

3. **U1** - Generic IC (when needed)
   - **Value**: Generic IC
   - **Package**: Variable based on scenario
   - **Footprint**: Context-dependent
   - **Symbol**: `Device:Generic_IC` or similar

### Alternative Components (Used in specific scenarios)
- **R2, R3**: Additional resistors (typically same specs as R1)
- **C2, C3**: Additional capacitors (typically same specs as C1)
- **Alternative values**: 1kΩ, 22kΩ resistors; 10µF capacitors

### PCB Placement Standards
- **R1 Position**: (76.2, 104.14) mm, 0° rotation, TOP side
- **C1 Position**: (90.2, 104.14) mm, 0° rotation, TOP side
- **Standard spacing**: 14mm between components

## KiCad File Structure Requirements

All fixture components must follow authentic KiCad patterns:

### Schematic File (.kicad_sch)
```lisp
(symbol
    (lib_id "Device:R")
    (at 50 50 0)
    (unit 1)
    (property "Reference" "R1"
        (at 52 48 0)
    )
    (property "Value" "10k"
        (at 52 52 0)
    )
    (property "Footprint" "Resistor_SMD:R_0603_1608Metric"
        (at 52 54 0)
    )
)
```

### PCB File (.kicad_pcb)
```lisp
(footprint "Resistor_SMD:R_0603_1608Metric"
    (at 76.2 104.14 0)
    (layer "F.Cu")
    (uuid "r1-uuid-12345")
    (property "Reference" "R1"
        (at 0 -1.43 0)
        (layer "F.SilkS")
    )
    (property "Value" "10k"
        (at 0 1.43 0)
        (layer "F.Fab")
    )
    (property "Footprint" "Resistor_SMD:R_0603_1608Metric")
    (attr smd)
)
```

### Project File (.kicad_pro)
Must include references to symbol and footprint libraries used.

## Fixture Creation Guidelines

1. **Use KiCad Application**: Create master project using real KiCad software
2. **Maintain Consistency**: All fixtures should derive from single master project
3. **Authentic Structure**: Preserve KiCad-generated UUIDs, layer definitions, design rules
4. **Component Placement**: Follow standard positions for predictable test behavior

## Fixture Variants

From the standardized master project, create these variants:

- **empty_project**: No components (authentic empty project)
- **simple_project**: R1 + C1 only
- **test_project**: R1 + C1 with standard test data
- **project_only**: Just .kicad_pro file
- **schematic_only**: .kicad_pro + .kicad_sch (no PCB)
- **pcb_only**: .kicad_pro + .kicad_pcb (no schematic)

## Benefits

- ✅ **Consistency**: All tests use identical component definitions
- ✅ **Authenticity**: Real KiCad structure ensures compatibility
- ✅ **Maintainability**: Single source of truth for all fixtures
- ✅ **Predictability**: Standardized values enable reliable test assertions

## Related Files

- `jbom-new/features/fixtures/kicad_templates/` - Fixture storage location
- `jbom-new/features/steps/project_centric_steps.py` - Fixture-based step definitions
- This document replaces fake component generation with authentic KiCad fixtures
