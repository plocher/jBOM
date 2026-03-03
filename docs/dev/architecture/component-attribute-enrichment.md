# Component Attribute Enrichment Model

This document defines jBOM's authoritative model for how component attributes are classified,
surfaced, confirmed, and written back during the inventory enrichment workflow. It captures
design decisions reached while implementing issues #98 (enrichment output structure) and #99
(Mode A interactive loop).

## Why This Model Exists: The Legacy Failure

Legacy jBOM automatically backfilled attributes — if a resistor had no `Tolerance` field, it
would silently write `Tolerance=5%` based on a domain default. This was wrong.

**"No tolerance specified" is a deliberate design decision**, not an oversight. When a designer
leaves a field blank, they are saying "the default is fine; I don't need this constraint in the
schematic." Automatically backfilling that value changes the meaning of the schematic without
designer consent, and creates false precision in the design record.

Mode A's explicit confirmation loop is the fix to this failure.

## The Three-Camp Attribute Model

Component attributes are classified into three camps based on their origin, meaning, and
handling rules.

### Camp 1: KiCad-specified attributes (must match)

Attributes the designer explicitly set in the KiCad schematic. These express deliberate
electro-mechanical constraints.

**Examples**: Value (10K), Package (0603), Footprint, lib_id, Tolerance=1% (if set),
Voltage=50V (if set)

**Rules**:
- Used as matching constraints — inventory items must satisfy these
- A conflict between a Camp 1 attribute and an inventory item means **wrong part**, not a
  missing annotation
- jBOM **never modifies** Camp 1 attributes; information flows KiCad → jBOM, never reverse
- If two components in the same aggregation group have different Camp 1 values, that is a
  schematic data inconsistency (warning, not silent resolution)

### Camp 2: "Should have been specified" attributes (explicit confirmation required)

Attributes that have clear domain meaning but the designer left blank, either because the
default is acceptable or because the parameter didn't feel worth specifying at design time.

**Examples**: Tolerance (when not set — "5% default is fine"), Power rating (when not set —
"package default is fine"), Voltage rating (when not set — "50V default is fine")

**Rules**:
- **Never auto-filled** without explicit designer confirmation
- Mode A surfaces these with domain defaults as pre-selections
- The designer **confirms or overrides** each one; confirmed values are written as deliberate
  constraints
- Written to inventory only after explicit acceptance — not on skip or flag
- If the project is in PM/fabrication phase (see Lifecycle below), Camp 2 is frozen: Mode A
  must not be run; no attribute changes are permitted

**Why the distinction matters**: Automatic backfill (Camp 2 treated as Camp 1) was legacy
jBOM's primary architectural failure. The 3-camp model exists to prevent this from recurring.

### Camp 3: Catalog-only attributes (silently filtered)

Attributes that appear in supplier catalogs or search results but have no design or inventory
meaning for jBOM's purposes. Showing these to the designer during Mode A creates noise and
dilutes actionable signal.

**Examples**: Supplier pricing, stock levels, lead times, RoHS/REACH status, package markings,
EIA land pattern codes, series/product family names (supplier-internal)

**Rules**:
- Silently excluded from Mode A candidate display and from inventory write-back
- Controlled by an `enrichment_attributes` YAML list per component category (see below)
- Not errors — just not relevant to jBOM's electro-mechanical matching domain

## Information Flow Direction

```
KiCad Schematic ──→ jBOM matching ──→ Inventory (write-back on confirmation)
                                              │
                          Supplier catalog ───┘  (enrichment source, read-only)
```

**The invariant**: Information flows from KiCad into jBOM, and from supplier catalogs into
inventory. Information **never flows back from jBOM into KiCad**. jBOM is a read-only consumer
of KiCad data.

## Lifecycle Phases

The 3-camp model has two distinct operating modes depending on project lifecycle phase:

### Designer phase (specification refinement)

Camp 2 is **active**. This is when Mode A provides value.

- The designer is still refining component specifications
- Mode A surfaces Camp 2 attributes with domain defaults as pre-selections
- Confirmed Camp 2 values become Camp 1 constraints going forward (they are now explicit)
- Rejected/skipped Camp 2 values remain blank (default is still acceptable)

**Mode A is the specification refinement tool for Camp 2.** Its primary job is not just finding
supplier part numbers — it is prompting the designer to confirm (or consciously defer)
electrical constraints that have domain significance but weren't worth specifying at schematic
time.

### PM/fabrication phase (frozen)

Camp 2 is **frozen**. Mode A should not be run.

- The project is in production or procurement; design is locked
- No attribute changes are permitted, even with explicit confirmation
- Mode B (bulk search, no interactive prompts) may still be used to update supply chain fields
  (C-numbers, prices, stock) — these are Camp 3 fields from the design perspective

## Write-back Rules

When an inventory enrichment operation writes data:

| Attribute type | Write-back rule |
|---|---|
| Camp 1 (KiCad-specified) | **Never written** — already in schematic; reverse flow forbidden |
| Camp 2 (confirmed by designer) | **Written only after explicit acceptance** in Mode A |
| Camp 2 (skipped or flagged) | **Not written** — absence of decision preserved |
| Sourcing fields (C-number, SPN, price, stock) | **Always written** on candidate acceptance |
| Camp 3 (catalog-only) | **Not written** — excluded by `enrichment_attributes` filter |

## enrichment_attributes YAML (Camp 3 Filter)

The list of Camp 3 attributes to exclude is controlled by a per-category YAML configuration.
This allows the org to tune what "noise" means for their workflow without code changes.

Conceptual schema (exact implementation in #98):

```yaml
enrichment_attributes:
  resistor:
    show_in_mode_a: [tolerance, power_rating, voltage_rating]
    suppress: [pricing, stock, lead_time, eia_land_pattern, series]
  capacitor:
    show_in_mode_a: [tolerance, voltage_rating, dielectric]
    suppress: [pricing, stock, lead_time, eia_land_pattern, series]
  # ... per category
```

The `show_in_mode_a` list defines which Camp 2 attributes are surfaced for confirmation. The
`suppress` list defines Camp 3 attributes that are silently filtered.

## Domain Defaults Table

When Mode A surfaces a Camp 2 attribute for confirmation, it needs a sensible pre-selection.
These defaults belong **in jBOM** (not in supplier profiles) and must be org-overridable.

The logic: defaults reflect design culture, not supplier taxonomy. An aerospace org defaults to
1% tolerance; a consumer electronics org defaults to 5%. A supplier profile has nothing to do
with that decision.

Conceptual schema (exact implementation in #98):

```yaml
domain_defaults:
  package_power:          # SMD resistor default power ratings by package
    "0402": "63mW"
    "0603": "100mW"
    "0805": "125mW"
    "1206": "250mW"
    "2512": "1W"
  tolerance_tiers:        # by application tier
    commodity: "5%"       # consumer electronics, non-critical signals
    standard: "1%"        # general precision
    precision: "0.1%"     # metrology, reference, audio
  voltage_defaults:       # default voltage rating by capacitor package/dielectric
    "0402_X5R": "10V"
    "0603_X7R": "25V"
    "0805_X7R": "50V"
```

Org-level override via project YAML allows aerospace teams to set `tolerance_tiers.commodity:
"1%"` or automotive teams to annotate AEC-Q qualification requirements.

## Interaction with Mode A (#99)

Mode A's per-item loop is structured around this 3-camp model:

1. **Query construction**: Uses Camp 1 attributes as hard constraints
2. **Candidate display**: Shows Camp 2 attributes with domain defaults as pre-selections;
   suppresses Camp 3 attributes
3. **Confirmation**: `[a]ccept` writes sourcing fields + confirmed Camp 2 values; `[s]kip`
   writes nothing for this item; `[n]ext` shows next ranked candidate
4. **Flag summary**: Items where all candidates were exhausted or skipped; includes the
   constructed query string for each (Camp 2 context visible, actionable)

**Mode A is Camp 2's activation mechanism.** Without Mode A, Camp 2 attributes can only be
manually edited in the schematic. With Mode A, the designer gets a structured, domain-aware
confirmation workflow that respects the deliberate design decision to leave fields blank.

## Relationship to Existing Architecture

- **Aggregation** (Step 2 in BOM pipeline): operates on Camp 1 attributes only — Camp 2
  absence is part of the electro-mechanical equivalence key
- **Matching** (Step 5 in BOM pipeline): Camp 1 attributes are hard constraints; Camp 2
  attributes (if confirmed and present) are soft constraints with domain-default fallback
- **Enrichment** (Mode A loop): Camp 2 activation; Camp 3 suppression; write-back on
  confirmation
- **Fabricator profiles**: Supply chain field routing (C-number → fab_pn, etc.); orthogonal
  to Camp classification; do not define domain defaults

See also:
- `workflow-architecture.md` — BOM generation pipeline and component attribute foundations
- `domain-centric-design.md` — bounded contexts and domain model structure
- GitHub #98 — enrichment output structure (implementation issue)
- GitHub #99 — Mode A interactive loop (implementation issue)
