# Standard Schematic Fixtures

This directory defines reusable schematic fixtures for BDD testing.

## Available Fixtures:

### BasicComponents
**Purpose**: Simple schematic with common passive and active components
**Components**:
- R1: 10K resistor, R_0603_1608 footprint
- C1: 100nF capacitor, C_0603_1608 footprint
- U1: ESP32 microcontroller, QFN-32 footprint

**Use cases**: Basic BOM generation, component matching, fabricator filtering

### MixedSMDTHT
**Purpose**: Mixed surface-mount and through-hole components
**Components**:
- R1, R2: 10K resistors, R_0603_1608 (SMD)
- C1: 100nF capacitor, C_0603_1608 (SMD)
- J1: 2x5 pin header, PinHeader_2x05_P2.54mm (THT)
- SW1: Tactile switch, SW_SPST_SKQG (THT)

**Use cases**: POS generation with SMD filtering, component type classification

### HierarchicalDesign
**Purpose**: Multi-sheet hierarchical design
**Main Sheet**:
- U1: ESP32 microcontroller
- J1: Power connector
**Power Sub-sheet** (power.kicad_sch):
- R1: 10K pullup resistor
- C1, C2: Decoupling capacitors

**Use cases**: Hierarchical schematic processing, quantity merging

### EmptySchematic
**Purpose**: Schematic with no components
**Components**: None

**Use cases**: Error handling, edge case testing

### ComponentProperties
**Purpose**: Components with detailed properties/fields
**Components**:
- R1: 10K resistor with Manufacturer="YAGEO", MPN="RC0603FR-0710K", Tolerance="1%"
- C1: 100nF capacitor with Voltage="50V", Dielectric="X7R"

**Use cases**: Custom field extraction, property-based matching

## Usage in Scenarios:

```gherkin
Given the "BasicComponents" schematic
Given the "MixedSMDTHT" schematic
Given the "HierarchicalDesign" schematic
```
