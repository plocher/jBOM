# Standard PCB Fixtures

This directory defines reusable PCB fixtures for POS/CPL testing.

## Available Fixtures:

### BasicPCB
**Purpose**: Simple PCB matching BasicComponents schematic
**Components**:
```
| Reference | X_mm | Y_mm | Rotation | Side | Footprint     | Type |
| R1        | 10.0 | 20.0 | 0        | Top  | R_0603_1608   | SMD  |
| C1        | 15.0 | 25.0 | 90       | Top  | C_0603_1608   | SMD  |
| U1        | 30.0 | 40.0 | 0        | Top  | QFN-32        | SMD  |
```

**Use cases**: Basic POS generation, coordinate extraction

### MixedSMDTHT_PCB
**Purpose**: PCB with mixed SMD and through-hole components
**Components**:
```
| Reference | X_mm | Y_mm | Rotation | Side | Footprint         | Type |
| R1        | 10.0 | 20.0 | 0        | Top  | R_0603_1608       | SMD  |
| R2        | 12.0 | 22.0 | 180      | Top  | R_0603_1608       | SMD  |
| C1        | 15.0 | 25.0 | 90       | Top  | C_0603_1608       | SMD  |
| J1        | 5.0  | 5.0  | 0        | Top  | PinHeader_2x5     | THT  |
| SW1       | 35.0 | 10.0 | 0        | Top  | SW_SPST_SKQG      | THT  |
```

**Use cases**: SMD filtering, component type classification

### DoubleSided_PCB
**Purpose**: PCB with components on both top and bottom sides
**Components**:
```
| Reference | X_mm | Y_mm | Rotation | Side   | Footprint   | Type |
| R1        | 10.0 | 20.0 | 0        | Top    | R_0603_1608 | SMD  |
| R2        | 15.0 | 25.0 | 180      | Bottom | R_0603_1608 | SMD  |
| C1        | 20.0 | 30.0 | 90       | Top    | C_0603_1608 | SMD  |
| C2        | 25.0 | 35.0 | 270      | Bottom | C_0603_1608 | SMD  |
```

**Use cases**: Layer filtering, side-specific POS generation

### AuxiliaryOrigin_PCB
**Purpose**: PCB with auxiliary origin defined for coordinate reference
**Auxiliary Origin**: (10.0, 10.0) mm
**Components**:
```
| Reference | X_mm | Y_mm | Rotation | Side | Footprint   | Type | Relative_X | Relative_Y |
| R1        | 20.0 | 30.0 | 0        | Top  | R_0603_1608 | SMD  | 10.0       | 20.0       |
| C1        | 25.0 | 35.0 | 90       | Top  | C_0603_1608 | SMD  | 15.0       | 25.0       |
```

**Use cases**: Auxiliary origin coordinate calculations

### EmptyPCB
**Purpose**: PCB with no placed components
**Components**: None

**Use cases**: Error handling, empty POS file generation

### PrecisionCoordinates_PCB
**Purpose**: PCB with precise coordinates for units conversion testing
**Components**:
```
| Reference | X_mm  | Y_mm  | X_inch | Y_inch | Rotation | Side | Footprint   | Type |
| R1        | 25.4  | 50.8  | 1.000  | 2.000  | 0        | Top  | R_0603_1608 | SMD  |
| C1        | 12.7  | 38.1  | 0.500  | 1.500  | 90       | Top  | C_0603_1608 | SMD  |
```

**Use cases**: Units conversion (mm to inches), precision testing

## Usage in Scenarios:

```gherkin
Given the "BasicPCB" PCB layout
Given the "MixedSMDTHT_PCB" PCB layout
Given the "DoubleSided_PCB" PCB layout
```
