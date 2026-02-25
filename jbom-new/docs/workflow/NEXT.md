# What to Do Next

## Current Task
**Task 1.6: Integration Tests for Matcher** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (commit a4db0eb)
- ✅ Task 1.2: Value Parsing (commit aaf79ec, 76 tests)
- ✅ Task 1.3: Package Matching (commit 7fab2d2)
- ✅ Task 1.3b: Package Matching Tests (commit ceaf62a, 20 tests)
- ✅ Task 1.4: Component Classification (pending commit)
- ✅ Task 1.4b: Component Classification Tests (pending commit)
- ✅ Task 1.5: Matcher Service Interface (commit 40b7106)
- ✅ Task 1.5b: Primary Filtering (commits 3a63bad, 66bed7a)
- ✅ Task 1.5c: Scoring + Ordering (commits ca5bb30, 099ead2)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Phase 1: Extract sophisticated matcher utilities.
Utilities extraction in progress:
- ✅ Task 1.2: value_parsing (complete)
- ✅ Task 1.3: package_matching (complete)
- ✅ Task 1.3b: package_matching tests (complete)
- ✅ Task 1.4: component_classification (complete)
- ✅ Task 1.5: matcher service interface (complete)
- ✅ Task 1.5b: primary filtering (complete)
- ✅ Task 1.5c: scoring + ordering (complete)
- → Task 1.6: integration tests (current)

## Target
**File**: `src/jbom/services/sophisticated_inventory_matcher.py`

## What to Do
Create integration tests validating the Phase 1 sophisticated matcher behavior:
- Use representative components + inventory items
- Confirm primary filtering + scoring results are equivalent to legacy for key cases
- Confirm ordering is exactly: (item.priority asc, score desc)

## Test Data Available

### Real Inventory Files
**Location**: `/Users/jplocher/Dropbox/KiCad/jBOM/examples/`
- `SPCoast-INVENTORY.csv` - 100+ items (RES, CAP, LED, IC, MCU, etc.)
- `JLCPCB-INVENTORY.csv` - JLCPCB-specific parts
- Also: `.xlsx`, `.numbers` versions

**Sample inventory rows**:
```csv
IPN,Category,Value,Package,Priority,Distributor,DPN,Manufacturer,MPN
CAP_0.1uF_X7R_0603,CAP,0.1uF,0603,2,JLC,C14663,YAGEO,CC0603KRX7R9BB104
CAP_1uF_X5R_0603,CAP,1uF,0603,2,JLC,C15849,Samsung,CL10A105KB8NNNC
RES_5%_100mW_0603_10k,RES,10k,0603,3,JLC,C15401,UNI-ROYAL,0603WAJ0103T5E
LED_Red_0603,LED,Red,0603,3,JLC,C965798,XINGLIGHT,XL-1608SURC-04
```

### Real KiCad Projects
**Location**: `/Users/jplocher/Dropbox/KiCad/projects/`
- `LEDStripDriver/` - LED driver with resistors, capacitors, transistors
- `Core-wt32-eth0/` - ESP32 Ethernet board with regulators, passives
- `AltmillSwitchController/` - Complex board with MCU, power, I/O
- `I2C-12v-GPIO/` - I2C expander with mixed components

## Test Scenarios to Cover

### 1. **Resistor Matching**
Component: `Device:R` with value="10k", footprint="0603"
Expected matches:
- IPN `RES_5%_100mW_0603_10k` (multiple priorities 1-3)
- Should prefer Priority=1 over Priority=3 (stock management)
- Score: Type(+50) + Value(+40) + Package(+30) = 120

### 2. **Capacitor Matching**
Component: `Device:C` with value="0.1uF", footprint="0603"
Expected matches:
- IPN `CAP_0.1uF_X7R_0603` with different priorities/distributors
- Numeric value matching (100nF = 0.1uF)
- Package extraction from "0603_1608Metric"

### 3. **LED Matching**
Component: `Device:LED` with value="Red", footprint="0603"
Expected matches:
- IPN `LED_Red_0603` (multiple color variants)
- Type detection from lib_id
- String value matching (not numeric)

### 4. **Priority Ordering**
Same IPN with different priorities:
- Priority=1 (expensive stock) should rank before Priority=3
- Same priority sorted by score descending
- Verifies ADR 0001 constraint: matcher reads but doesn't modify priority

### 5. **Primary Filtering**
Component: `Device:C` value="1uF" should NOT match:
- Resistors (type filter)
- 0.1uF capacitors (value filter)
- 1206 capacitors (package filter)

## Success Criteria
- [ ] Real components match correctly against SPCoast inventory
- [ ] Results equivalent to old-jbom for same inputs
- [ ] Priority ordering verified: (priority asc, score desc)
- [ ] Primary filtering prevents bad matches
- [ ] Integration tests pass

## Implementation Notes
- Load inventory from `examples/SPCoast-INVENTORY.csv`
- Create test components matching inventory items
- Compare results to expected matches
- Document any behavior differences from legacy

## Estimated Time
60-90 minutes

## Notes
This is the first end-to-end verification of the Phase 1 matcher port. Keep it focused on equivalence testing with real-world data.
