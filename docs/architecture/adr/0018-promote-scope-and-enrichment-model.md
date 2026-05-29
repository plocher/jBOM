# ADR 0018: Promote Command Scope and Enrichment Model
Date: 2026-05-29
Status: Accepted
Related: #323, #324, #325, #327, #329, #330, #331, ADR 0008, ADR 0012, ADR 0013

## Context

`jbom promote` was introduced (issue #323, PR #325) as a way to materialize a
supplier-export CSV (initially the JLCPCB private parts export) into the
canonical jBOM inventory schema so downstream `jbom bom`, `jbom audit`, and
`jbom annotate` workflows can consume it as if it were a curated inventory.

During the implementation and review of PR #325, three architecture-level
decisions emerged that bound `promote`'s responsibility and shape over time.
The same review also accepted a number of CLI ergonomics decisions
(removal of `--source-format` and `--no-enrich`, the supplier-context
implicit rule); those are part of the user-facing CLI contract and live in
`docs/reference/cli.md`, not in this ADR.

This ADR records the three scope/direction decisions so they do not live only
in PR comments and so the followup issues hang off them cleanly.

## Decision drivers

- Preserve jBOM's design principle that fabricator- and supplier-specific
  knowledge lives in configuration (`*.jbom.yaml`, ADR 0008), not in code.
- Avoid promoting (no pun intended) a temporary implementation choice into an
  architectural commitment. Specifically, do not treat free-text description
  parsing as a strategic data source.
- Keep individual jBOM commands responsible for one bounded
  concept. A supplier-invoice transform and an inventory-curation activity
  are two different bounded concepts even when they touch the same canonical
  rows.
- Keep `promote`'s contract narrow enough that it can run offline and
  per-invoice, and broad enough that the same workflow benefits from
  supplier-side parametric data when a catalog is available.

## Decisions

### D1. Provider parametric attributes are the primary parameterized data source; description-regex parsing is a last-resort fallback

The original intent of `promote` was:

1. Resolve identity via supplier catalog (deterministic MPN/SPN lookup).
2. Use the provider's parametric attributes (`SearchResult.attributes`) as
   the primary source of typed canonical fields such as `Tolerance`, `V`,
   `A`, `W`, dielectric `Type`, `Datasheet`, etc.
3. Fall back to a regex parse of the free-text `Description` only where the
   provider did not supply a field.

The implementation in PR #325 currently runs the description-regex parser
first and consults the provider only to fill missing canonical fields. That
inversion is recognised as a temporary shape, retained because reusing the
provider's parametric data is non-trivial and was scoped out of #325.

The committed direction is the provider-first ordering. The description
regex parser is intentionally bounded in scope: it must not accumulate
domain knowledge that belongs in supplier responses, nor should new
electrical categories be added by extending the regex parser when the
provider already returns them.

Followup that realises this decision: issue #329.

### D2. Source-export shapes are declarative configuration, not code

A supplier-export CSV shape (header signature, column → canonical-seed
mapping, traceability columns) is declarative data about a supplier's view
of its own catalog. Under ADR 0008, that belongs inside the supplier's
unified `*.jbom.yaml` configuration, under a new `export:` block.

The code-side concern reduces to one `ConfigDrivenAdapter(supplier.export)`
plus a header-signature auto-detector that walks loaded supplier profiles
and chooses the highest-confidence match. The in-code `JlcpcbExportAdapter`,
the `GenericCsvAdapter`, and the `select_adapter` switch shipped in PR #325
are interim shapes; they will be retired in favour of the config-driven
adapter.

This decision also reinforces the broader jBOM principle that adding
support for a new fabricator/supplier is a configuration drop-in, not a
code change.

Followup that realises this decision: issue #327.

### D3. `promote` is per-invoice; cross-supplier discovery and freshness/lifecycle/stock stamping belong to `inventory`

`promote` operates on one supplier's export and produces canonical inventory
rows that describe what *that* supplier sees of its own catalog. Two
adjacent capabilities are explicitly out of scope:

- **Cross-supplier alternative discovery** — looking up the same MPN at
  other suppliers and emitting additional `Priority>1` rows under the same
  IPN. This is an inventory-curation activity that grows an already-canonical
  inventory and belongs in `jbom inventory --supplier <other>` (followup
  issue #330).
- **Freshness, lifecycle, and stock stamping** — querying providers for
  current lifecycle/stock data and stamping canonical columns on existing
  rows. This is also an inventory-curation activity and shares plumbing
  with `jbom audit --supplier`; it belongs in `jbom inventory` (followup
  issue #331).

The promote command stays focused on the per-invoice ETL contract: source
adapter → semantic extraction → identity → optional supplier enrichment of
the same MPN/SPN it already saw in the source row → canonical-row output.

## Consequences

### Positive

- The promote command has a clear, bounded contract that does not grow with
  every adjacent inventory-curation feature.
- The unified-config direction (ADR 0008) is reinforced rather than
  contradicted: new supplier shapes are declarative drop-ins, not code
  changes.
- The description-regex parser stops accruing maintenance load as the
  provider-attributes-first ordering lands; its scope is explicitly capped
  as fallback-only.
- Followup work has clean issue boundaries: #327, #329, #330, #331 each
  realise one part of one of these decisions.

### Negative / tradeoffs

- The interim shape shipped in PR #325 (description-first parser, in-code
  JLC adapter) will require follow-on work before this ADR is fully realised
  in code.
- Some near-term feature requests that feel like they belong in `promote`
  (multi-supplier views, freshness stamping) will be routed to `inventory`
  instead. The CLI surface must remain consistent enough that this routing
  is predictable.

### Neutral

- Does not prescribe a concrete provider-attribute mapping schema; that
  detail belongs to issue #329's implementation.
- Does not prescribe the exact name or shape of the `supplier.export:`
  stanza; that detail belongs to issue #327's implementation.

## Provenance

Decisions D1–D3 were established during PR #325 review. The plan that
drove that PR is preserved as a PR comment for design history. This ADR
exists so the decisions are durable in `docs/architecture/adr/` and not
only in PR conversation.
