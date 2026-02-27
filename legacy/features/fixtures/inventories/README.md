# Standard Inventory Fixtures

This directory defines reusable inventory fixtures for BDD testing.

## Available Fixtures:

### JLC_Basic
**Purpose**: Common JLC parts matching BasicComponents schematic
**Contents**:
```
| IPN   | Category | Value | Package | Distributor | DPN    | MPN            | Manufacturer | Priority |
| R001  | RES      | 10K   | 0603    | JLC         | C25804 | RC0603FR-0710K | YAGEO        | 1        |
| C001  | CAP      | 100nF | 0603    | JLC         | C14663 | CC0603KRX7R9BB | YAGEO        | 1        |
| U001  | IC       | ESP32 | QFN-32  | JLC         | C82899 | ESP32-WROOM-32 | Espressif    | 1        |
```

**Use cases**: JLC BOM generation, fabricator filtering

### LocalStock
**Purpose**: Same components as JLC_Basic but from local inventory
**Contents**:
```
| IPN   | Category | Value | Package | Distributor | DPN       | MPN            | Manufacturer | Priority |
| R001  | RES      | 10K   | 0603    | LOCAL       | R-10K-603 | RC0603FR-0710K | YAGEO        | 1        |
| C001  | CAP      | 100nF | 0603    | LOCAL       | C-100N603 | CC0603KRX7R9BB | YAGEO        | 1        |
| U001  | IC       | ESP32 | QFN-32  | LOCAL       | ESP32-DEV | ESP32-WROOM-32 | Espressif    | 1        |
```

**Use cases**: Local fabrication, distributor filtering tests

### MixedFabricators
**Purpose**: Same components across multiple fabricators with different priorities
**Contents**:
```
| IPN   | Category | Value | Package | Distributor | DPN        | Priority |
| R001  | RES      | 10K   | 0603    | JLC         | C25804     | 1        |
| R002  | RES      | 10K   | 0603    | SEEED       | SRR-10K603 | 2        |
| R003  | RES      | 10K   | 0603    | LOCAL       | R-10K-603  | 3        |
| C001  | CAP      | 100nF | 0603    | JLC         | C14663     | 1        |
| C002  | CAP      | 100nF | 0603    | MOUSER      | 810-C0603C104K | 2        |
```

**Use cases**: Multi-fabricator priority testing, verbose BOM alternatives

### ConflictingIPNs
**Purpose**: Same IPNs with different specifications to test conflict resolution
**Contents**:
```
| IPN   | Category | Value | Package | Voltage | Tolerance |
| CONF1 | CAP      | 10uF  | 0805    | 16V     | 10%       |
| CONF1 | CAP      | 10uF  | 0805    | 25V     | 20%       |
```

**Use cases**: IPN conflict detection and resolution

### EmptyInventory
**Purpose**: Empty inventory file for error testing
**Contents**: Headers only, no data rows

**Use cases**: Error handling, empty inventory warnings

### PriorityTest
**Purpose**: Multiple parts with same specs but different priorities including edge cases
**Contents**:
```
| IPN    | Category | Value | Package | Distributor | Priority |
| R001   | RES      | 10K   | 0603    | JLC         | 0        |
| R001A  | RES      | 10K   | 0603    | JLC         | 1        |
| R001B  | RES      | 10K   | 0603    | JLC         | 5        |
| R001C  | RES      | 10K   | 0603    | JLC         | 100      |
| C001   | CAP      | 100nF | 0603    | JLC         | 2        |
| C001A  | CAP      | 100nF | 0603    | JLC         | 0        |
| C001B  | CAP      | 100nF | 0603    | JLC         | 50       |
```

**Use cases**: Priority selection logic with edge cases (0, large values), verbose alternatives display

## Usage in Scenarios:

```gherkin
Given the "JLC_Basic" inventory
Given the "LocalStock" inventory
Given the "MixedFabricators" inventory
```
