# KiCad Best Practices for jBOM Search Quality

jBOM's Phase 4 parametric search uses KiCad schematic data — symbol names,
footprints, and component properties — to build targeted JLCPCB/LCSC queries.
This guide explains which KiCad choices improve search hit rates and which ones
cause fallbacks to generic keyword searches.

## General Principles

### Use Fully-Qualified Library References

jBOM reads `NICKNAME:ENTRY_NAME` for both symbols and footprints. The entry
name (after `:`) is the primary search signal. Library nicknames follow KLC
conventions for standard libraries but may be user-defined for private
libraries; jBOM treats matching nicknames as a positive signal but never
penalises non-KLC nicknames.

### Populate Category-Specific Properties

jBOM maps KiCad schematic properties (`Value`, `Voltage`, `Tolerance`, etc.)
directly to parametric search attributes. Leaving properties blank causes jBOM
to fall back to defaults (configured in `.jbom/generic.defaults.yaml`).

Use `~` (tilde) in a property value to explicitly indicate "don't care" for a
field that would otherwise default to a non-trivial value. This prevents jBOM
from adding an unwanted constraint to the search query.

---

## Capacitors

### Technology Detection: MLCC vs Electrolytic/Tantalum

jBOM routes capacitors to either the JLCPCB **Multilayer Ceramic Capacitors
(MLCC)** or **Aluminum Electrolytic Capacitors** sub-category based on:

| Signal | Effect |
|--------|--------|
| Symbol entry name contains `Polarized` (e.g. `Device:C_Polarized`) | → Electrolytic |
| Footprint entry name starts with `CP_` (e.g. `Capacitor_SMD:CP_Elec_4x5.4mm`) | → Electrolytic |
| Library nickname contains `Elec`, `Tantalum`, or `Polarized` | → Electrolytic (additive) |
| None of the above | → MLCC (default) |

**Recommended symbols:**

- MLCC: `Device:C` with a standard SMD footprint (`Capacitor_SMD:C_0603_…`)
- Electrolytic/Tantalum: `Device:C_Polarized` with a polarised footprint (`Capacitor_SMD:CP_Elec_…`)

### Voltage Rating

Populate the `Voltage` property for all capacitors. Without it, jBOM falls back
to the package-level default (e.g. `0603` → `25V`). For high-voltage or
precision applications, set it explicitly.

### Dielectric

For MLCC, populate the `Type` property with the dielectric code (`X7R`, `C0G`,
`X5R`, etc.). Without it, jBOM uses the profile default (`X7R`). For timing or
precision circuits where dielectric matters, always specify it.

---

## Inductors

### Subtype Routing

jBOM routes inductors to one of three JLCPCB sub-categories:

| Condition | Route |
|-----------|-------|
| `FERRITE` in `Description` property | → Ferrite Beads |
| `_Core` in symbol entry name (e.g. `Device:L_Core`) | → Power Inductors |
| Package is `1210`, `1812`, `2520`, or `4532` | → Power Inductors |
| None of the above | → Inductors (SMD) |

**Recommended practices:**

- Ferrite beads: use `Device:L` or `Device:Ferrite_Bead` and write `Ferrite Bead`
  in the `Description` property. The `Value` field typically carries the
  impedance spec (e.g. `600R@100MHz`).
- Power inductors: use `Device:L_Core` or a large SMD package (`1210` or
  larger).
- Signal/RF inductors: any small SMD package without the above signals.

### Current Rating

Populate the `Current` property for power inductors. jBOM includes it in the
keyword query to help filter for appropriately-rated parts.

### Inductance Value

Always populate `Value` with a parseable inductance string (e.g. `10uH`,
`4.7uH`, `2m2`). The `Inductance` column in the inventory CSV stores the
decoded float for precise parametric matching; jBOM populates this automatically
at harvest time.

---

## Connectors

### Structured Data Priority

jBOM builds the JLCPCB connector query from the most specific data available,
in this priority order:

1. `Pins` and `Pitch` schematic properties (set on the component in KiCad)
2. Footprint entry name (after `:`), parsed for pitch (`P2.54mm`), pin count
   (`1x04`), and series (`PinHeader`, `JST_PH`, etc.)
3. Keyword-only fallback (if none of the above are present)

**Best practice:** populate `Pins` and `Pitch` properties directly on
connectors in the schematic. This ensures correct search data even if the
footprint library is not KLC-standard.

### Footprint Naming

KLC-compliant footprints encode pitch and pin count in their entry names and
are automatically parsed by jBOM:

| Entry name pattern | Parsed as |
|-------------------|-----------|
| `PinHeader_1x04_P2.54mm_Vertical` | series=PinHeader, 4 pins, 2.54mm pitch |
| `JST_PH_S4B-PH-K_1x04-1MP_P2.00mm_Vertical` | series=JST_PH, 4 pins, 2.00mm pitch |
| `JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical` | series=JST_XH, 4 pins, 2.50mm pitch |

Use KLC-compliant footprints from the standard `Connector_PinHeader_*` and
`Connector_JST` libraries wherever possible. For custom footprints, ensure the
entry name follows the `Series_RowxCols_Ppitch_Mounting` pattern.

### Mounting Orientation

While jBOM does not currently route on vertical vs horizontal mounting, using
the standard `_Vertical` / `_Horizontal` suffix in footprint names is good
practice for future improvements.

---

## Resistors

jBOM handles resistors well automatically. For best results:

- Populate `Tolerance` (e.g. `1%`, `5%`).
- Populate `Power` / `Wattage` for high-power applications.
- Set `Type` to `Metal Film`, `Carbon Film`, or `Wirewound` for through-hole
  resistors to get correct JLCPCB sub-category routing.

---

## The `~` (Don't-Care) Convention

Use a tilde `~` as a property value to explicitly suppress a field that jBOM
would otherwise default. This is useful when:

- You genuinely don't care about a parameter and want the widest possible
  search (e.g. `Tolerance: ~` for a non-critical resistor).
- A default would be wrong for your application.

```
Voltage: ~       # any voltage rating is acceptable
Tolerance: ~     # tolerance is not a selection criterion here
```

---

## Summary Table

| Category | Key properties to populate | Critical footprint signals |
|----------|---------------------------|---------------------------|
| CAP (MLCC) | `Value`, `Voltage`, `Tolerance`, `Type` (dielectric) | `C_` prefix in entry name |
| CAP (electrolytic) | `Value`, `Voltage`, `Tolerance` | `CP_` prefix in entry name; `C_Polarized` symbol |
| IND (signal) | `Value` (inductance) | Small SMD package |
| IND (power) | `Value`, `Current` | `L_Core` symbol or `1210`/`1812` package |
| IND (ferrite) | `Value` (impedance), `Description` | `FERRITE` in description |
| CON | `Pins`, `Pitch` | KLC footprint entry name with pitch/count tokens |
| RES | `Value`, `Tolerance`, `Power` | Package size |
