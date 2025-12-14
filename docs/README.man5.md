# inventory(5) — jBOM Inventory File Format

## NAME

inventory — bill of materials inventory file format for jBOM

## DESCRIPTION

The jBOM inventory file is a structured database of available components. It supports three formats: CSV (comma-separated values), Excel (.xlsx, .xls), and Apple Numbers (.numbers). All formats use the same logical column structure.

Each row represents one stocked component. Columns define the component's attributes and how it relates to schematic components during matching.

## REQUIRED COLUMNS

**IPN** (Internal Part Number)
: Unique identifier for this inventory item. jBOM uses IPN to group components in the BOM.

**Category**
: Component classification (RES, CAP, IND, LED, DIO, IC, MCU, CON, etc.). Must match the schematic component type detected from lib_id or footprint. Used as first-stage filter.

**Value**
: Component value in appropriate units. Format depends on category:
  - RES: ohms (330, 330R, 3R3, 10k, 10K0, 2M2, 0R22, etc.)
  - CAP: farads (100nF, 0.1u, 1u0, 220pF, etc.)
  - IND: henrys (10uH, 2m2, 100nH, etc.)
  - LED/DIO: part number or color code
  - IC/MCU: part number

**Package**
: Physical package code (0603, 0805, 1206, SOT-23, SOIC-8, QFN-32, etc.). Extracted from schematic footprint and matched exactly.

**LCSC**
: Supplier part number from LCSC Electronics. Used as the primary identifier in the BOM output.

**Priority**
: Integer ranking (1 = most preferred, higher = less preferred). When multiple parts match equally, the lowest Priority is selected. Allows you to prefer stocked parts (Priority=1) over others (Priority=2+).

## OPTIONAL COLUMNS

**Manufacturer**
: Component manufacturer name (UNI-ROYAL, YAGEO, WIMA, etc.).

**MFGPN**
: Manufacturer part number (0603WAJ0331T5E, CC0603KRX7R9BB104, etc.).

**Datasheet**
: URL to component datasheet PDF.

**Keywords**
: Comma-separated search keywords for components. Not currently used in matching but available for inventory management.

**SMD**
: Surface mount indicator (SMD, Y, YES, TRUE, 1 for SMD; PTH, THT, TH, N, NO, FALSE, 0 for through-hole). If omitted or unclear, jBOM infers from footprint.

**Tolerance**
: Tolerance rating (5%, 1%, ±10%, etc.). Used in scoring to prefer tighter tolerances when available.

**V (Voltage)**
: Working voltage rating (25V, 50V, 75V, 400V, etc.).

**A (Amperage)**
: Current rating (100mA, 1A, 10A, etc.).

**W (Wattage)**
: Power dissipation rating (0.1W, 0.25W, 1W, etc.).

**Type**
: Component type variant (X7R for capacitors, Film for resistors, etc.).

**Form**
: Physical form factor (SPDT, DPDT for switches; Radial, Axial for through-hole resistors, etc.).

**Frequency**
: Operating frequency for oscillators and clocks (12MHz, 32.768kHz, etc.).

**Stability**
: Frequency stability rating for oscillators (±100ppm, ±50ppm, etc.).

**Load**
: Load capacitance for oscillators (20pF, 10pF, etc.).

**Family**
: IC family for microcontrollers (ESP32, STM32F4, etc.).

**mcd (Millicandela)**
: Brightness rating for LEDs (100mcd, 500mcd, etc.).

**Wavelength**
: LED color or wavelength (Red, Green, Blue, 620nm, etc.).

**Angle**
: LED viewing angle (30°, 120°, etc.).

**Pitch**
: Connector pin pitch (2.54mm, 1.27mm, 0.5mm, etc.).

**Description**
: Human-readable description (330Ω 5% 0603 resistor, 100nF X7R ceramic capacitor, etc.).

## FIELD NAMING CONVENTIONS

Column names are case-insensitive and flexible:
- Spaces accepted: "Mfg PN" or "MFGPN" both work
- Title Case preferred for readability: "Manufacturer" not "MANUFACTURER"
- Abbreviations: "V" for voltage, "A" for amperage, "W" for wattage
- Standard notation: "mcd" for millicandela (lowercase)

jBOM normalizes all field names internally to snake_case (mfg_pn, mcd, etc.), so naming variations are handled automatically.

## EXAMPLE CSV

```csv
IPN,Category,Package,Value,Tolerance,LCSC,Manufacturer,MFGPN,Description,Datasheet,SMD,Priority
R001,RES,0603,330R,5%,C25231,UNI-ROYAL,0603WAJ0331T5E,330Ω 5% 0603,,SMD,1
R002,RES,0603,10K,1%,C25232,YAGEO,RC0603FR-0710KL,10kΩ 1% 0603,,SMD,1
R003,RES,0603,47K,5%,C25233,VISHAY,CRCW060347KJNEA,47kΩ 5% 0603,,SMD,2
C001,CAP,0603,100nF,10%,C14663,YAGEO,CC0603KRX7R9BB104,100nF X7R 0603,,SMD,1
C002,CAP,0603,1uF,10%,C14664,MURATA,GRM31CR61A105KA19L,1uF X5R 0603,,SMD,1
L001,IND,0603,10uH,20%,C1608,SUNLORD,SWPA3012S100MT,10µH 0603,,SMD,1
LED001,LED,0603,Red,,,EVERLIGHT,19-217-GHC-YR1S2-3T,Red LED 0603,,SMD,1
```

## FIELD DISAMBIGUATION (I: and C: PREFIXES)

When using custom BOM output (`-f` option), field names can be prefixed to disambiguate:

**I:fieldname**
: Force use of inventory field (e.g., `I:Tolerance` → inventory tolerance)

**C:fieldname**
: Force use of component property (e.g., `C:Tolerance` → schematic component tolerance)

**fieldname** (no prefix)
: Ambiguous: if both exist, BOM includes both as separate columns

Example:
```bash
python jbom.py project -i inventory.csv -f "Reference,Value,I:Package,C:Tolerance"
```

## MATCHING BEHAVIOR

jBOM matches schematic components to inventory items through:

1. **Primary filtering** (must match all):
   - Category must match component type
   - Package must match footprint extraction
   - Value must match numerically (for RES/CAP/IND)

2. **Scoring** (selection when multiple match):
   - Priority ranking (1 preferred over 2, etc.)
   - Technical score from property matches (Tolerance, V, A, W, etc.)
   - Tolerance-aware substitution: exact tolerance matches are preferred; tighter tolerances substitute only when exact match is unavailable
     - Exact match preferred: Schematic requires 10kΩ 10% and 10% is available → 10% part is selected (full scoring bonus)
     - Next-tighter preferred over tightest: Schematic requires 10kΩ 10%, inventory has only 5% and 1% → 5% is ranked higher (tolerance gap 5% vs 9%, closer to requirement gets higher score)
     - Scoring penalizes over-specification: Substitution within 1% of requirement gets full bonus; more than 1% tighter gets reduced bonus to encourage sensible substitutions
     - No looser substitution: Schematic requires 10kΩ 1% but inventory has only 5% or 10% → no match (looser tolerances cannot substitute)
     - Example ranking when no exact match: 5% substitution scores higher than 1% substitution because it's closer to the required 10% tolerance

3. **Tie-breaking**:
   - Uses Priority column as primary sort
   - Uses technical score as secondary sort

## INVENTORY FILE SIZE LIMITS

No hard limits, but reasonable sizing:
- Typical inventory: 100–1000 items
- Large inventory: 1000–10000 items
- Very large: 10000+ items (may slow matching slightly)

Excel and Numbers files are more memory-intensive than CSV.

## ENCODING AND SPECIAL CHARACTERS

All files should use **UTF-8 encoding**. This allows:
- Unicode symbols (Ω for ohm, µ for micro, °C for celsius)
- International characters in descriptions and manufacturer names
- Proper rendering in all systems

CSV files are auto-detected as UTF-8 with BOM or without.

## SPREADSHEET-SPECIFIC NOTES

### CSV Files
- Standard comma-separated format
- First row must be headers
- Empty rows are skipped
- Handles newlines and quoted fields per RFC 4180

### Excel Files (.xlsx, .xls)
- Header detection: jBOM searches first 10 rows for "IPN" column
- Data extraction: starts from row after headers
- Handles arbitrary row/column offsets in spreadsheet
- Empty cells treated as missing values
- Requires: `pip install openpyxl`

### Apple Numbers Files (.numbers)
- Extracts data from first table in first sheet
- Header detection: same as Excel (searches for "IPN")
- Proper cell access through Numbers API
- Requires: `pip install numbers-parser`

## VALIDATION

jBOM validates inventory on load:
- IPN column required (skips rows without IPN)
- Category auto-uppercased for matching
- Value parsed for numeric types (RES, CAP, IND)
- Package normalized (whitespace cleaned)
- Priority defaulted to 99 if missing or invalid

Invalid or missing optional columns are tolerated; matching simply skips those properties.

## SEE ALSO

- [**README.md**](README.md) — Quick start guide
- [**README.man1.md**](README.man1.md) — CLI reference with field list
- [**README.developer.md**](README.developer.md) — Matching algorithm details
