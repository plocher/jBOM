# Inventory Data Model

This document explains why jBOM's inventory is shaped the way it is: why the same IPN
appears on multiple rows, what the Supplier/SPN relationship captures, and what the
`Priority` field governs. It is the rationale layer sitting below the field-level
semantics defined in [inventory-field-semantics.md](inventory-field-semantics.md).

The domain layer commitment to inventory as a first-class entity is recorded in
[ADR 0013](../architecture/adr/0013-domain-centric-design.md) under the Manufacturing
Domain bounded context, where `InventoryItem` is named as a domain entity with internal
part number identity.

---

## The challenge: relational data in a spreadsheet format

An inventory that serves real procurement workflows needs to represent two distinct
concepts that have a many-to-many relationship:

- **A component** — a specific part with a defined electrical and mechanical specification.
  This is supplier-neutral: "a 10k 1% 0603 resistor."
- **A sourcing option** — a specific supplier, their part number, the price they charge,
  and how preferred that source is relative to alternatives.

A normalized relational database would model these as separate tables joined by the
component's internal identifier. jBOM's inventory uses CSV (or Excel or Numbers) as its
interchange format because spreadsheets are the tool PCB designers already live in.
That constraint means relational normalization cannot be expressed as separate sheets
in the common case.

The design decision is to represent the normalized intent in a single flat table:
multiple rows per component, one row per sourcing option, all sharing the same IPN.

---

## The IPN as component identity

The Internal Part Number (`IPN`) is the stable identity for a component across all rows
that represent it. Two rows with the same IPN are asserting that they represent the same
component — same type, same value, same package — but from different suppliers or at
different price points.

This means the IPN must be chosen to reflect component identity, not sourcing identity.
An IPN that encodes the supplier or part number defeats the purpose: if you add a second
supplier for an existing part, you should not need to assign a new IPN.

A typical IPN convention encodes the component's essential electrical and physical
specification — for example, `IPN-10k-1pct-0603-RES`. The exact format is a project
or organization convention; jBOM does not enforce a schema on the IPN string beyond
treating it as an opaque identifier for matching purposes.

---

## The Supplier / SPN relationship

Each row pairs an `IPN` with a `Supplier` and a `Supplier Part Number` (`SPN`). This
triple — `IPN`, `Supplier`, `SPN` — is what a procurement workflow needs: it answers
"which component," "from whom," and "by what order code."

The `MPN` (Manufacturer Part Number) captures the manufacturer's catalog reference,
which is independent of where you buy it. A single MPN may be stocked by multiple
suppliers under different SPNs.

```
IPN (component identity)
  └── Manufacturer A, MPN-A  (physical part)
       ├── Supplier X, SPN-X1  (row 1: buy from X)
       └── Supplier Y, SPN-Y1  (row 2: buy from Y)
  └── Manufacturer B, MPN-B  (equivalent alternate part)
       └── Supplier X, SPN-X2  (row 3: alternate mfr, same supplier)
```

All three rows carry the same IPN because they represent equivalent components. The
schematic refers to the IPN; the procurement workflow selects a specific row based on
availability and preference.

---

## The Priority field and ranking semantics

When multiple rows share an IPN, `Priority` tells jBOM which to prefer. Lower values
are higher priority (1 = most preferred). The matcher applies priority-aware ranking
during component matching:

- For **passive components** (resistors, capacitors, inductors): sort order is
  `(preference tier ascending, Priority ascending, match score descending)`.
  Priority wins ties between equally-scored candidates.
- For **non-passive components**: sort order is
  `(preference tier ascending, match score descending, Priority ascending)`.
  Match quality leads; Priority breaks ties among equivalent-score candidates.

This asymmetry reflects that passives are highly substitutable — any 10k 1% 0603 from
any approved supplier is equally correct — so the explicit Priority preference is the
meaningful differentiator. Non-passives often have functionally relevant properties
that make one match clearly better than another, so score leads.

An inventory file whose rows do not carry a `Priority` column receives the default
priority value for all rows. This means "any source is equally preferred" — appropriate
for a starter inventory that has not been curated for multi-supplier scenarios.

---

## Data validation intent

Because the flat CSV format cannot enforce the relational constraint mechanically, data
integrity relies on authoring discipline reinforced by jBOM's diagnostic output. The
expected invariant is:

- Rows sharing an IPN must agree on `Type`, `Value`, and `Package`. Disagreement
  indicates a data authoring error — either two different parts were given the same IPN
  by mistake, or the IPN was changed for one row without propagating to others.
- Different `Priority` values for the same IPN are correct and expected when representing
  real supplier alternatives.

jBOM emits warnings when same-IPN rows carry conflicting component specifications,
surfacing these authoring errors at processing time rather than silently producing an
incorrect BOM.

---

## Migration path

The flat-CSV approach is explicitly designed to tolerate a future migration to a fully
normalized store (separate component and sourcing tables, a relational database) without
breaking existing workflows. Because the IPN is stable component identity and the
multi-row structure encodes the normalized intent, extracting the component table and
sourcing table from existing CSVs is a mechanical transformation.

Existing inventory files will continue to work with jBOM regardless of whether that
migration happens. The design choice favors maintainability and broad tool compatibility
today while keeping the door open for a more structured store if the scale of managed
inventory warrants it.

---

## Related material

- [Inventory field semantics](inventory-field-semantics.md) — the two-state blank/explicit
  model, `~` handling, electrical column aliases, and annotate write-back rules.
- [ADR 0013 — Domain-Centric Design](../architecture/adr/0013-domain-centric-design.md) —
  the `InventoryItem` entity and the Manufacturing Domain bounded context.
- [Inventory workflows tutorial](../tutorials/inventory-workflows.md) — how to build,
  enhance, and grow an inventory using these concepts in practice.
