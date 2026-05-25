# ADR 0002: JLCPCB/LCSC Provider — Live API over Local Database
Date: 2026-03-04
Status: Accepted

Closes: #93, #115, #116, #103

## Context

jBOM needs a search provider for LCSC/JLCPCB parts to fill sparse inventory items
(missing supplier part numbers). Two architectural options were evaluated.

### Option A — Local SQLite database (jlcparts)

The yaqwsx/jlcparts project maintained a canonical LCSC component database (~1 GB
SQLite, FTS5-indexed). However, since July 2025, JLCPCB throttled their catalog API
so severely that a full download cannot complete within GitHub Actions' 6-hour timeout.
The canonical database is now frozen with **missing descriptions** — not just stale but
structurally incomplete. All downstream projects (Bouni/kicad-jlcpcb-tools,
CDFER/jlcpcb-parts-database) inherit this degraded data.

References: https://github.com/yaqwsx/jlcparts/issues/151

### Option B — Live JLCPCB parts API

An apparently-open JLCPCB search API was discovered via sleemanj's active fork
(https://sleemanj.github.io/jlcparts/). The endpoint:

```
POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2
```

accepts category + attribute filters, returns up to 1024 results per call with current
stock and price data, and requires no authentication or API key.

## Decision

**Option B (live API) was chosen.**

Key decision factors:

1. **Data quality**: The local DB is structurally broken upstream. The live API returns
   current stock and price on every query.
2. **No credentials or local setup required**: The live endpoint is unauthenticated.
   Users get LCSC search working immediately without downloading a ~1 GB database.
3. **Cache handles cold-start**: `DiskSearchCache` with a 30-day TTL on taxonomy
   responses eliminates repeated calls. The cold-start problem the local DB was meant
   to solve is already addressed by the cache layer.
4. **API ethics**: jBOM issues targeted per-item queries only (one call per unique
   component type per session). This is qualitatively equivalent to a user manually
   searching jlcpcb.com/parts and does not constitute bulk catalog extraction.
   Rate limiting: 2 seconds default between calls, configurable in `lcsc.supplier.yaml`.

## Architecture

```
JlcpcbProvider  (src/jbom/services/search/jlcpcb_provider.py)
├── JlcpcbPartsApi  (src/jbom/services/search/jlcpcb_api.py)
│     └── responses cached via DiskSearchCache (24h TTL)
└── build_phase4_parametric_query_plan()
      (src/jbom/services/search/jlcpcb_phase4_heuristics.py)
      └── config-driven via DefaultsConfig / generic.defaults.yaml

JlcpartsProvider  (src/jbom/services/search/jlcparts_provider.py)
└── stub only — available() → False
    preserved for potential future air-gapped use; no implementation planned
```

Provider type identifiers in `lcsc.supplier.yaml`:
- `jlcpcb_api` → `JlcpcbProvider` (active)
- `jlcparts_sqlite` → `JlcpartsProvider` stub (inactive)

## MPN Routing Split

`InventorySearchService.search(item)` routes based on whether a manufacturer part
number is present (design notes from issue #116):

```
InventorySearchService.search(item)
│
├── item.mpn is set   →  JlcpcbProvider.lookup_by_mpn()
│                         Deterministic lookup. Highest-stock C-number wins on
│                         multiple matches. No candidate ranking needed.
│
└── item.mpn absent   →  build_phase4_parametric_query_plan()
                          Parametric search using category-based attribute filtering.
                          Category-aware heuristics select relevant API filters.
```

Well-specified items (MPN present) never touch parametric search. The two paths have
a clean boundary and are independently deliverable.

## Phase 4 Parametric Heuristics

Category-specific query shaping in `jlcpcb_phase4_heuristics.py`, driven by
`DefaultsConfig` loaded from `generic.defaults.yaml` (overridable at project level).

| Category | Parametric support | Key attributes |
|---|---|---|
| RES | ✅ Full | Resistance, Tolerance, Package, Technology, Power |
| CAP | ✅ Full | Capacitance, Tolerance, Voltage, Dielectric, Package |
| IND | ❌ Keyword fallback | Phase 4 heuristics not yet implemented |
| CON | ❌ Keyword fallback | Connector taxonomy mismatch; low hit rate |
| Others | ❌ Keyword fallback | — |

Key defaults (all overridable via `generic.defaults.yaml`):
- Resistor tolerance: `5%`
- Capacitor tolerance: `10%`
- Capacitor dielectric: `X7R`
- Sort order: stock-descending (`sortMode=STOCK_SORT`) — high stock correlates with
  commodity availability and price. Applied as default for generic/underspecified items.

## Consequences

### Positive
- No local database download or maintenance required
- Works out of the box with no user configuration beyond the supplier YAML
- Current stock and price data on every non-cached query
- Cache layer handles repeated queries efficiently (24h TTL)
- MPN routing eliminates expensive catalog search for well-specified items
- Phase 4 heuristics are config-driven and overridable without code changes

### Negative / Risks
- Dependent on JLCPCB API availability (mitigated by cache; cached results serve
  offline sessions)
- API is unofficial and undocumented; endpoint URL or schema may change without notice
- CON (connector) category not yet viable for parametric search — keyword fallback
  has ~0% hit rate in current validation (see `docs/dev/validation/issue-123/`)
- IND (inductor) falls through to keyword search; Phase 4 heuristics planned in a
  follow-on issue

### Neutral
- `jlcparts_sqlite` stub preserved in provider registry for forward compatibility
- POC script and API recording fixtures retained in `scripts/` for reference
