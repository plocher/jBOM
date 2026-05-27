# Inventory file format reference

The jBOM inventory file is a user-curated database of components available to
a project. **The schema is user-defined**, not a fixed jBOM model: jBOM
expresses *expectations* about what attributes need to be collectable, but
users may extend, rename, or reorder columns in service of their own
inventory-management practice. The relationship between an inventory file,
the active config profile, and the `--fields` CLI argument is what binds a
particular inventory column-spelling to a particular BOM-output column;
jBOM deliberately does not hardcode reliance on the spelling or order of
any attribute. See [Inventory schema, profiles, and `--fields`](#inventory-schema-profiles-and---fields)
below for how the three combine.

Inventory files support three formats: CSV (comma-separated values), Excel
(`.xlsx`, `.xls`), and Apple Numbers (`.numbers`). All formats share the
logical structure described here.

Each row represents either a project requirement (`COMPONENT`) or a stocked
part (`ITEM`). Columns define the row role and matching/search attributes.
For the behavioral semantics that govern how these columns are used during
matching — including the blank-field invariant, tolerance-aware substitution
rules, and IPN multi-row design intent — see
[Inventory matching semantics](../design/inventory-matching-semantics.md).

## Schema model: denormalized database with IPN as primary key

A jBOM inventory is a **denormalized database**. The primary key is the
**IPN** (Internal Part Number), which represents the unique electronic and
mechanical identity of an item — a 1 kΩ 1% 250 mW SMT 0603 resistor is
one IPN; a 1 kΩ 5% 100 mW SMT 0603 resistor is a different IPN.

**Multiple rows may share the same IPN as long as they differ only in their
non-electro-mechanical attributes.** This is the supply-chain dimension:
the same EM-identical part can be available from Mouser as part number
`652-CR0603FX-1002ELF`, from Digi-Key as `311-1.00KHRCT-ND`, and from LCSC
as `C25804`. Each is a separate row sharing the same IPN, the same
electro-mechanical attributes, but a different `Supplier` + `SPN` pair.
Navigating among these candidates at BOM-generation time — by `Priority`,
by fabricator preference, by stock availability — is what jBOM does.

Attributes split into two categories:

- **Electro-mechanical attributes** are **constant within an IPN**. These
  describe what the part *is*: `Category`, `Value`, `Package`, `Tolerance`,
  `Voltage`, `Current`, `Power`, `Type`, `Form`, `Frequency`, `Stability`,
  `Load`, `Family`, `mcd`, `Wavelength`, `Angle`, `Pitch`. Two rows with the
  same IPN must agree on all EM attributes; disagreement is a data error.
- **Supply-chain attributes** **vary across rows of the same IPN**. These
  describe where to buy the part: `Manufacturer`, `MFGPN`, `Supplier`, `SPN`,
  `Datasheet`, `Priority`, and any user-added columns capturing stock
  level, pricing, or sourcing notes.

The schema-required columns enforce just enough structure to make matching
work: `RowType`, `IPN` (for `ITEM` rows), `Category`, `Value`, `Package`,
and `Priority`. Every other column is optional and may be defined by the
user; jBOM exposes them to the BOM-generation pipeline by name.

## Required columns

**RowType**
: Row role discriminator: `COMPONENT` or `ITEM`.

**ComponentID**
: Requirement identifier for `COMPONENT` rows. Leave blank for `ITEM` rows.

**IPN** (Internal Part Number)
: Required for `ITEM` rows. Leave blank for `COMPONENT` rows. See
  [Schema model](#schema-model-denormalized-database-with-ipn-as-primary-key)
  above for the full multi-row design intent.

**Category**
: Component classification (`RES`, `CAP`, `IND`, `LED`, `DIO`, `IC`, `MCU`, `CON`,
  etc.). Matched against the schematic component type detected from lib_id or footprint.
  Used as the first-stage filter.

**Value**
: Component value in appropriate units. Format depends on category:
  - `RES`: ohms (`330`, `330R`, `3R3`, `10k`, `10K0`, `2M2`, `0R22`, etc.)
  - `CAP`: farads (`100nF`, `0.1u`, `1u0`, `220pF`, etc.)
  - `IND`: henrys (`10uH`, `2m2`, `100nH`, etc.)
  - `LED`/`DIO`: part number or color code
  - `IC`/`MCU`: part number

**Package**
: Physical package code (`0603`, `0805`, `1206`, `SOT-23`, `SOIC-8`, `QFN-32`, etc.).
  Extracted from the schematic footprint and matched exactly.
: The BOM `Footprint` output column remains the canonical PCB FPID
  (`pcb:footprint`) taken from the `.kicad_pcb` footprint identifier; this FPID
  policy does not add new required inventory-schema columns.

**Priority**
: Integer ranking (1 = most preferred, higher = less preferred). When multiple
  equivalent candidates are found, the lowest Priority value is selected. This lets the
  inventory author prefer certain parts for stock rotation — set Priority=1 for a
  preferred reel and Priority=2 for a fallback. Defaults to 99 if missing or invalid.

## Optional columns

**Manufacturer**
: Component manufacturer name (`UNI-ROYAL`, `YAGEO`, `WIMA`, etc.).

**MFGPN**
: Manufacturer part number (`0603WAJ0331T5E`, `CC0603KRX7R9BB104`, etc.).

**Supplier**
: Supplier name for this part. Used by `jbom audit --supplier` to identify which parts
  catalog is associated with the supplier SPN for validation, and by
  `jbom inventory --supplier` to record which distributor assigned the PN. Typical
  values: `lcsc`, `mouser`, `generic`.

**SPN** (Supplier Part Number)
: The supplier-assigned part number corresponding to the `Supplier` field. Used as the
  part number identifier in BOM output when present.

**LCSC** *(deprecated)*
: Legacy supplier part number from LCSC Electronics. Equivalent to setting
  `Supplier=lcsc` and `SPN=<value>`. Accepted for backward compatibility; new
  inventories should use `Supplier` + `SPN` instead.

**Datasheet**
: URL to the component datasheet PDF.

**Keywords**
: Comma-separated search keywords. Not currently used in matching but available for
  inventory management.

**SMD**
: Surface mount indicator. Truthy values: `SMD`, `Y`, `YES`, `TRUE`, `1`.
  Through-hole values: `PTH`, `THT`, `TH`, `N`, `NO`, `FALSE`, `0`. If omitted or
  unclear, jBOM infers the mount type from the footprint.

**Tolerance**
: Tolerance rating (`5%`, `1%`, `±10%`, etc.). Used in component matching to widen or
  narrow candidate pools.

**Voltage**
: Working voltage rating (`25V`, `50V`, `75V`, `400V`, etc.).

**Current**
: Current rating (`100mA`, `1A`, `10A`, etc.).

**Power**
: Power dissipation rating (`0.1W`, `0.25W`, `1W`, etc.).

**Type**
: Component type variant (`X7R` for capacitors, `Film` for resistors, etc.).

**Form**
: Physical form factor (`SPDT`, `DPDT` for switches; `Radial`, `Axial` for through-hole
  resistors, etc.).

**Frequency**
: Operating frequency for oscillators and clocks (`12MHz`, `32.768kHz`, etc.).

**Stability**
: Frequency stability rating for oscillators (`±100ppm`, `±50ppm`, etc.).

**Load**
: Load capacitance for oscillators (`20pF`, `10pF`, etc.).

**Family**
: IC family for microcontrollers (`ESP32`, `STM32F4`, etc.).

**mcd** (Millicandela)
: Brightness rating for LEDs (`100mcd`, `500mcd`, etc.).

**Wavelength**
: LED color or wavelength (`Red`, `Green`, `Blue`, `620nm`, etc.).

**Angle**
: LED viewing angle (`30°`, `120°`, etc.).

**Pitch**
: Connector pin pitch (`2.54mm`, `1.27mm`, `0.5mm`, etc.).

**Description**
: Human-readable description (`330Ω 5% 0603 resistor`, `100nF X7R ceramic capacitor`,
  etc.).

## Field naming conventions

Column names are case-insensitive and spacing-flexible: `"Mfg PN"` and `"MFGPN"` both
resolve to the same field. Title Case is preferred for readability, but `"Manufacturer"`
and `"MANUFACTURER"` are equivalent. jBOM normalizes all field names internally to
snake\_case and back to CamelCase or Title Case as needed.

Legacy unit-column aliases are accepted at intake:

- `V` / `Volts` → `Voltage`
- `A` / `Amperage` → `Current`
- `W` / `Wattage` → `Power`
- `mcd` → millicandela (standard; no alias)

The canonical electrical column names are `Voltage`, `Current`, and `Power`. The alias
mapping is applied both at inventory intake and during `annotate --normalize`; see
[Inventory field semantics](../design/inventory-field-semantics.md) for the full
annotate write-back treatment.

## Example CSV

The example below uses the legacy `LCSC` column for illustration of the format. New
inventories should replace `LCSC` with the `Supplier` + `SPN` pair.

```csv
RowType,ComponentID,IPN,Category,Package,Value,Tolerance,LCSC,Manufacturer,MFGPN,Description,Datasheet,SMD,Priority
COMPONENT,REQ1|CAT=RES|VAL=10K|PKG=0603|TOL=5%|V=|A=|W=|TYPE=,,RES,0603,10K,5%,,,,,,,,99
ITEM,,R001,RES,0603,330R,5%,C25231,UNI-ROYAL,0603WAJ0331T5E,330Ω 5% 0603,,SMD,1
ITEM,,R002,RES,0603,10K,1%,C25232,YAGEO,RC0603FR-0710KL,10kΩ 1% 0603,,SMD,1
```

Equivalent modern form using `Supplier` and `SPN`:

```csv
RowType,ComponentID,IPN,Category,Package,Value,Tolerance,Supplier,SPN,Manufacturer,MFGPN,Description,Datasheet,SMD,Priority
ITEM,,R001,RES,0603,330R,5%,lcsc,C25231,UNI-ROYAL,0603WAJ0331T5E,330Ω 5% 0603,,SMD,1
```

## Field disambiguation (I: and C: prefixes)

When building custom BOM output with the `-f` option, field names can be prefixed to
resolve ambiguity between schematic component attributes and inventory item fields.

`I:fieldname` forces use of the inventory field (e.g., `I:Tolerance` → inventory
tolerance). `C:fieldname` forces use of the schematic component attribute (e.g.,
`C:Tolerance` → schematic tolerance). An unprefixed name is ambiguous: if both exist,
the BOM includes both as separate columns.

## Inventory schema, profiles, and `--fields`

The inventory's column set, the active fabricator/supplier profile, and the
`--fields` (a.k.a. `-f`) CLI argument are three independent surfaces that
combine to produce a specific BOM:

- **The inventory** declares what attributes exist (by column name) for the
  rows the user has curated.
- **The active profile** (a `*.jbom.yaml` file with a `fab:` and/or
  `supplier:` stanza) declares the *default* column-to-BOM-output mapping
  for that fabricator. JLCPCB's profile, for example, maps the resolved
  fabricator part number into a column named `LCSC` because that is the
  header JLCPCB's upload portal expects.
- **`--fields`** (or `-f`) overrides the profile's default mapping at
  invocation time: a comma-separated list of field names selects a subset
  of inventory columns to surface in the BOM, and a preset name
  (`+standard`, `+jlc`, `+minimal`, `+all`) selects a named bundle.

Field references inside profiles use the namespace prefixes documented in
[ADR 0009](../architecture/adr/0009-field-reference-system-and-value-expressions.md)
(`sch:`, `pcb:`, `inv:`, `a:`, `jbom:`) so a profile can compose values
from multiple sources. The `field_synonyms` mechanism (see
[Configuration semantics](../design/configuration-semantics.md)) lets a
profile accept several spellings of the same logical column (`Mouser PN`,
`Mouser_PN`, `mouser-pn`, etc.) without burdening the inventory author.

The practical consequence: a single inventory works with any fabricator;
the profile decides how its columns appear in the BOM. Users who want to
define their own inventory schema can do so as long as the required
attributes (above) are present and any custom column the profile or CLI
references exists in the file under one of its accepted synonyms.

## Inventory file size limits

There are no hard limits, but practical sizing guidelines apply:

- Typical inventory: 100–1,000 items
- Large inventory: 1,000–10,000 items
- Very large: 10,000+ items (may slow matching noticeably)

Excel and Numbers files are more memory-intensive than CSV for the same row count.

## Encoding and special characters

All inventory files should use **UTF-8 encoding**. UTF-8 allows Unicode symbols (Ω for
ohm, µ for micro, °C for Celsius) and international characters in descriptions and
manufacturer names. CSV files are auto-detected as UTF-8 with or without a BOM prefix.

## Spreadsheet-specific notes

### CSV files

Standard comma-separated format. The first row must be the header row. Empty rows are
skipped. Quoted fields and embedded newlines are handled per RFC 4180.

### Excel files (.xlsx, .xls)

jBOM searches the first 10 rows for the `IPN` column to detect the header row, then
extracts data starting from the row after the header. Arbitrary row and column offsets
within the spreadsheet are handled; empty cells are treated as missing values. Requires
the `openpyxl` package.

### Apple Numbers files (.numbers)

Data is extracted from the first table in the first sheet. Header detection follows the
same IPN-search logic as Excel. Requires the `numbers-parser` package.

## Validation

jBOM validates the inventory on load. The `Category` column is required and is
auto-uppercased for matching. `ITEM` rows require a non-blank `IPN`; `COMPONENT` rows
require a non-blank `ComponentID`. The `Value` field is parsed numerically for `RES`,
`CAP`, and `IND` categories. Package values are whitespace-normalized. A missing or
non-integer `Priority` defaults to 99.

Invalid or missing optional columns are tolerated: matching simply skips any properties
whose column is absent or blank.
