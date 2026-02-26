# Workflow Architecture: BOM Generation Pipeline

This document captures the architectural intent of jBOM's core BOM generation workflow — the sequence of component gathering, inventory gathering, fabricator filtering, matching, and output generation.

## The Core Problem

KiCad projects describe circuits in terms of electrical and mechanical requirements: "R1 is a 330Ω resistor in an 0603 package." They do not — and should not — encode supply chain decisions like "R1 is YAGEO RC0603JR-07330RL from Mouser."

jBOM bridges that gap. It matches a project's electro-mechanical requirements against a separate inventory of real, orderable parts, producing fabricator-ready BOMs without embedding supply chain data into KiCad project files.

## Key Concepts

### Components

A **component** is a placed part in a KiCad schematic, identified by a reference designator (R1, C2, U3). Each component has attributes set by the designer:

- **Reference**: R1, R2, C1, LED3, U1, ...
- **Value**: 330R, 100nF, LM358, ...
- **Footprint**: R_0603_1608Metric, SOIC-8_3.9x4.9mm, ...
- **lib_id**: Device:R, Device:C, Device:LED, ...
- **Properties**: Tolerance=5%, Voltage=50V, ... (arbitrary key=value pairs)

Components are the design-side input to jBOM. Their attributes express electro-mechanical requirements, not supply chain choices.

### Aggregation

A KiCad project typically has many components but fewer unique parts. R1, R2, and R9 might all be `{value=330R, package=0603, tolerance=5%, category=resistor}` — they have identical electro-mechanical requirements.

**Aggregation** groups components with identical electro-mechanical specs into a single unit. This is purely a schematic-side operation — no inventory is consulted. Each aggregated group represents one "kind of part" the project needs, with a quantity equal to the number of components in the group.

A BOM is organized by these aggregations:

```
Designator          | Quantity | Value  | Package
"R1, R2, R9"        | 3        | 330R   | 0603
R3                   | 1        | 10K    | 0603
C1                   | 1        | 1.0uF  | 0603
"U1, U2"             | 2        | 4N28SM | SMDIP-6
```

The aggregation key is the complete set of electro-mechanical attributes — primarily value and footprint, but generalizing to include any attributes that would cause two components to require different physical parts (tolerance, voltage rating, etc.).

### Inventory

An **inventory** is an external data source (CSV, Excel, Numbers) that maps electro-mechanical specifications to real, orderable parts with supply chain details:

- **IPN**: Internal Part Number — unique identifier for the inventory item
- **Category, Value, Package**: Electro-mechanical attributes (matched against components)
- **Manufacturer, MFGPN**: Who makes it and their part number
- **Supplier, SPN**: Where to buy it and the order code
- **Priority**: User-managed ranking (1 = most preferred, higher = less preferred)
- **Tolerances, ratings, etc.**: Additional electro-mechanical attributes for scoring

An inventory commonly has multiple items that satisfy the same electro-mechanical spec but differ in supply chain details (different manufacturers, different suppliers, different prices). This is by design — it provides sourcing flexibility.

### Fabricator Profiles

A **fabricator profile** (e.g., `jlc.fab.yaml`, `generic.fab.yaml`) captures supply chain context for a specific PCB fabricator/assembler:

- **Field synonyms**: Maps evolving inventory column names to canonical names (e.g., "LCSC Part #" → `fab_pn`)
- **Tier rules**: Policy-based preference ranking (consigned items → tier 0, catalog items → tier 2, MPN-only → tier 4)
- **Column mappings**: How BOM/CPL output columns should be named for this fabricator

Fabricator profiles enable the same inventory to serve multiple fabricators with different supply chain models.

## The BOM Generation Pipeline

The pipeline follows this sequence, defined by the `[Generate.BOM]` user scenario in `requirements/0-User-Scenarios.md`:

```
1. Extract.Components  →  Load components from KiCad schematic
2. Aggregate           →  Group components by electro-mechanical equivalence
3. Extract.Items       →  Load inventory from file(s)
4. Filter.Items        →  Filter/rank inventory by fabricator profile
5. Match.Components    →  Match each aggregated group to filtered inventory
6. Resolve.Conflicts   →  Handle orphans and ambiguous matches
7. Create.BOM          →  Format and output the BOM
```

### Step 1: Extract Components

Parse KiCad schematic files (including hierarchical sheets) to extract all components with their attributes. This produces a flat list of `Component` objects.

### Step 2: Aggregate

Group components by electro-mechanical equivalence. All components with identical design requirements become one group with a combined reference list and a quantity.

This step is **independent of inventory**. It operates solely on schematic data.

### Step 3: Extract Items

Load inventory data from one or more files (CSV, Excel, Numbers). Each file contributes `InventoryItem` objects with full `raw_data` preserved for fabricator field-synonym resolution.

### Step 4: Filter Items (Fabricator Selection)

Apply the fabricator profile to the inventory:

1. **Fabricator affinity filter**: Keep items dedicated to this fabricator or generic items; prune items dedicated to other fabricators.
2. **Project restriction filter**: Honor optional per-item project restrictions.
3. **Field synonym normalization**: Resolve inventory column-name variants to canonical names.
4. **Tier assignment**: Evaluate tier rules to assign a preference tier to each surviving item.

Items that match no tier rule are **not eligible** for this fabricator profile — they lack an actionable identifier.

This step is implemented by `FabricatorInventorySelector` (Phase 2).

### Step 5: Match Components

For each aggregated group, find inventory items that satisfy its electro-mechanical requirements within the fabricator-filtered candidate set.

**The matching model** finds the intersection of two logical sets:

- **Electro-mechanical candidates**: Inventory items whose category, value, package, tolerance, voltage, etc. are compatible with the group's requirements.
- **Supply chain candidates**: The fabricator-filtered inventory from Step 4.

The intersection is scored and ordered by `(preference_tier, item.priority, -match_score)`:

1. **Fabricator preference** first (lower tier = better)
2. **User stock-management priority** second (lower priority number = more preferred)
3. **Match quality** third (higher score = better electro-mechanical fit)

This step is implemented by `SophisticatedInventoryMatcher` (Phase 1), operating on `EligibleInventoryItem` objects from Step 4.

**Ideal outcome**: Each group resolves to exactly one best-match inventory item. The BOM line is complete.

**Orphan**: A group with zero matches. The project uses a component not (yet) in the consulted inventory. Other jBOM capabilities (supplier catalog search) can address this.

**Ambiguous**: A group with multiple equally-ranked matches. May require user intervention or priority adjustment.

### Step 6: Resolve Conflicts

Collect and report:

- **Matched groups**: BOM lines with a clear best inventory item
- **Orphans**: Groups with no inventory match — need inventory expansion
- **Ambiguous matches**: Groups with tied candidates — need priority refinement

### Step 7: Create BOM

Generate output (CSV, console table, etc.) combining:

- Aggregated component data (references, quantity, value, footprint)
- Matched inventory data (manufacturer, part numbers, supplier details)
- Fabricator-specific column naming and formatting

## Policy: IPN as Component Attribute

KiCad component attributes are arbitrary key=value pairs chosen by the designer. A designer *could* set an IPN attribute on a component (e.g., R1 has `IPN=RES_330R_0603`).

**Current policy**: IPN is treated as supply chain data, not an electro-mechanical constraint.

- **Aggregation**: IPN does not affect grouping. R1 (with IPN) and R2 (without IPN) are in the same group if their electro-mechanical specs match.
- **Matching**: If a group carries an IPN (from any member), and that IPN exists in the filtered candidate list, it acts as a direct-lookup hint that short-circuits heuristic scoring.
- **Conflicts**: If components within a group carry different IPNs, this is a data inconsistency that should generate a warning. (Not yet implemented — deferred to Phase 8.)
- **Missing IPN**: If the IPN is not found in inventory, fall back to normal heuristic matching.

This approach is pragmatic: it respects explicit designer intent when present, without requiring IPN on every component.

## No-Inventory Case

When no inventory file is provided (`jbom bom project.kicad_sch` without `--inventory`):

- Steps 1-2 execute normally (extract and aggregate)
- Steps 3-6 are skipped (no inventory to match against)
- Step 7 produces a basic BOM from schematic data only (no supplier details)

This produces the same minimal BOM that KiCad itself would generate — useful for review, but insufficient for fabrication.

## Service Mapping

| Pipeline Step | Service | Status |
|---|---|---|
| Extract.Components | `SchematicReader` | ✅ Implemented |
| Aggregate | `BOMGenerator` | ✅ Implemented (value+footprint grouping) |
| Extract.Items | `InventoryReader` | ✅ Implemented |
| Filter.Items | `FabricatorInventorySelector` | ✅ Implemented (Phase 2) |
| Match.Components | `SophisticatedInventoryMatcher` | ✅ Implemented (Phase 1) |
| Resolve.Conflicts | — | ⏳ Phase 3 |
| Create.BOM | `BOMGenerator` + CLI formatting | ✅ Partially implemented |

**Phase 3 integration goal**: Wire the implemented services together in the correct pipeline sequence within the CLI's `handle_bom()` function.

## See Also

- `requirements/0-User-Scenarios.md` — User scenarios defining the pipeline steps
- `requirements/1-Functional-Scenarios.md` — Functional scenario details
- `docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md` — ADR on fabricator selection design
- `docs/workflow/NEXT.md` — Current development status and next steps
