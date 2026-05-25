# Inventory matching semantics

This document records the behavioral axioms governing how jBOM matches schematic
components to inventory items. These invariants are distinct from the field-level
write-back semantics documented in [Inventory field semantics](inventory-field-semantics.md)
and from the fabricator-aware selection layer described in
[ADR 0001](../architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md).

The column reference — what each field name means and how it is parsed — lives in
[Inventory file format](../reference/inventory-format.md). This document explains the
matching rules that operate on those columns.

## The blank-field invariant

A blank value in any component attribute means the designer chose not to constrain that
attribute. Blank is not "unknown" — it is an explicit non-requirement.

This is a codebase invariant: blank fields are excluded from both primary filtering and
scoring. Any inventory item is acceptable on a blank-constrained attribute. The
invariant applies to Tolerance, Voltage, Current, Power, Dielectric, and all other
optional attributes. KiCad's `~` placeholder in component attributes is treated as
blank under this rule — jBOM does not assign `~` any sentinel meaning beyond "this
field was left empty." (The annotate write-back treatment of `~` is distinct; see
[Inventory field semantics](inventory-field-semantics.md) for that side of the
two-state model.)

The rationale for this design is that the jBOM workflow proceeds in defined phases: the
designer creates the project, runs an audit (B1), optionally repairs attributes (B2),
then generates the fabrication BOM. By the time jBOM runs, every blank field represents
a conscious decision — the designer has reviewed it and left it blank. jBOM trusts that
workflow. No sentinel value is needed to encode "designer chose generic."

## IPN multi-row design intent

The same IPN can and should appear in multiple rows of an inventory file. Each row with
a given IPN shares the same electronic and mechanical fingerprint but carries different
supply chain metadata — a different supplier, a different pricing tier, a different
manufacturer. This is the canonical way to represent multi-sourced or dual-sourced
parts.

The consequence is that matching produces a candidate pool, not a single result.
Multiple ITEM rows with the same IPN are each independently evaluated as candidates;
they are ranked by priority and technical score to select the most appropriate for the
current BOM context. jBOM's value is precisely in navigating this candidate pool
deterministically.

This design also means that an inventory file is not a unique-keyed table — it is a
catalog. Adding a second supplier for an existing part is a matter of inserting another
row with the same IPN and different `Supplier`/`SPN` values; no existing row is
modified. The fabricator-aware selection layer (ADR 0001) may later prune this pool to
items eligible for a given fabricator before the matcher scores and ranks the
remainder.

## Primary filtering

Matching begins with a mandatory filter stage. An ITEM row is admitted to the candidate
pool only if all of the following hold:

- Its `Category` matches the schematic component's detected type.
- Its `Package` matches the footprint extraction exactly.
- Its `Value` matches numerically (for `RES`, `CAP`, and `IND` categories; see
  [Category-specific value parsing](#category-specific-value-parsing) below).

Blank component attributes are excluded from this filter — a blank `Package` on a
schematic component does not require an exact Package match; any package is accepted.
The same applies to blank Category or Value.

## Category-specific value parsing

For passive component categories, jBOM parses value strings numerically rather than
comparing them as raw text. This allows `10k`, `10K`, `10K0`, and `10000` to all
represent the same 10 kΩ resistor. The category-to-parsing mapping is:

- `RES` — ohms; accepts engineering notation (`330R`, `3R3`, `2M2`, `0R22`), SI
  suffixes (`k`, `M`), and bare numeric strings.
- `CAP` — farads; accepts SI prefixes (`p`, `n`, `u`, `µ`, `m`) and engineering
  notation (`1u0`, `220pF`).
- `IND` — henrys; same SI-prefix handling as capacitors.

For all other categories (`LED`, `DIO`, `IC`, `MCU`, `CON`, etc.), the `Value` field
is treated as an opaque string and matched exactly or ignored, depending on whether the
schematic component carries a Value constraint.

## Scoring and candidate selection

When multiple ITEM rows pass the primary filter, jBOM ranks them by a composite score:

**Technical score** is accumulated from optional attribute matches. Tolerance, Voltage,
Current, Power, and similar attributes each contribute when both the schematic component
and the inventory item carry non-blank values. Blank component attributes contribute
zero to scoring — consistent with the blank-field invariant.

**Priority** is the integer ranking set by the inventory author (1 = most preferred).
Lower Priority values rank higher. Priority is the primary sort key; technical score is
the secondary.

### Tolerance-aware substitution

Tolerance matching applies an asymmetric rule: a tighter tolerance can substitute for a
looser requirement, but a looser tolerance cannot substitute for a tighter requirement.

When the exact required tolerance is available, it is selected and receives the full
score bonus. When no exact match exists, jBOM ranks candidates by how close their
tolerance is to the requirement — a 5% part substituting for a 10% requirement scores
higher than a 1% part substituting for the same requirement, because the 5% part has a
smaller gap from the requirement. Substitution within 1 percentage point of the
requirement receives the full bonus; larger gaps receive a reduced bonus to discourage
over-specification. No looser substitution is permitted: if a schematic component
requires 1% and the inventory has only 5% and 10%, no match is produced on tolerance
grounds.

This rule captures the engineering intuition that substituting a 1% part for a 10%
requirement is wasteful (it consumes expensive precision stock) and may mislead future
reviewers about design intent, while substituting a 5% part for a 10% requirement is a
reasonable and transparent tradeoff.

### Tie-breaking

When candidates are tied on both Priority and technical score, the selection is
deterministic but not semantically significant — the tie-break is an implementation
artifact, not a design choice. Inventory authors who care about selection order should
use Priority to express that preference explicitly.

## Relationship to fabricator-aware selection

The matching axioms described here operate on a candidate pool that may already have
been pruned by fabricator-aware inventory selection. ADR 0001 establishes that
fabricator selection is a separate step from matching: the selection layer filters the
inventory to items eligible for a given fabricator and annotates them with a preference
tier (catalog vs crossref); the matcher then ranks the remaining candidates using
Priority and technical score. These two concerns are explicitly separated so the matcher
stays fabricator-agnostic and testable in isolation.
