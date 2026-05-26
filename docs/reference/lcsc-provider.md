# LCSC / JLCPCB Search Provider

jBOM searches the LCSC/JLCPCB parts catalog using the live JLCPCB parts API.
No local database download, no account, and no API key are required.

## How it works

### Items with a known Manufacturer Part Number (MPN)

If an inventory item has `Manufacturer` and `MPN` fields populated, jBOM performs a
**deterministic lookup** via `JlcpcbProvider.lookup_by_mpn()`. This returns the
corresponding LCSC C-number directly — no keyword search, no candidate ranking.
When multiple C-numbers exist for the same MPN (batch/warehouse variants), the
highest-stock result is selected.

### Generic / underspecified items (no MPN)

If an inventory item has no MPN, jBOM uses parametric heuristics to build a
structured query from the item's category and attributes:

| Category | Mode | Notes |
|---|---|---|
| RES | Parametric | Resistance, Tolerance, Package, Technology, Power |
| CAP | Parametric | Capacitance, Tolerance, Voltage, Dielectric, Package |
| IND | Keyword fallback | Parametric heuristics not yet implemented |
| CON | Keyword fallback | Connector taxonomy mismatch; expect low hit rate |
| Others | Keyword fallback | — |

Results are sorted stock-descending by default: high stock correlates with commodity
availability and price, naturally surfacing the parts experienced designers reach for.

The parametric query planner is implemented in
`src/jbom/suppliers/lcsc/query_planner.py`.

## Configuration

The LCSC supplier profile is the `supplier:` stanza in
`src/jbom/config/jlc.jbom.yaml` (the unified config file for the JLC fabricator and
LCSC supplier, per [ADR 0008](../architecture/adr/0008-unified-jbom-config-schema.md)):

```yaml
supplier:
  name: "LCSC"
  id: "lcsc"
  search:
    cache:
      ttl_hours: 24
    api:
      timeout_seconds: 20.0
      max_retries: 3
      retry_delay_seconds: 1.0
    providers:
      - type: jlcpcb_api
        rate_limit_seconds: 2
```

`rate_limit_seconds` controls the delay between API calls. The default of 2 seconds
is conservative; reducing it risks throttling by the JLCPCB endpoint.

To override defaults for RES/CAP parametric queries (tolerance, dielectric, package
power ratings), create a project-level `.jbom.yaml` with a `defaults:` stanza. See
`src/jbom/config/jlc.jbom.yaml` (the `defaults:` stanza) for the available keys.

## Cache

Search results are cached to disk at `~/.cache/jbom/` with a 24-hour TTL configured
in `jlc.jbom.yaml`. Repeated queries within the TTL window make no API calls.

Cache management differs by command:

- **`jbom audit --supplier lcsc`** and **`jbom inventory --supplier lcsc`**: batch
  supplier flows use the configured TTL only. There is no per-run cache bypass flag
  on these commands; to force a fresh lookup, delete
  `~/.cache/jbom/lcsc/` or adjust `ttl_hours` in `jlc.jbom.yaml`.
- **`jbom search`**: the interactive search command exposes per-run cache flags:

```bash
jbom search "10k 0603" --supplier lcsc --no-cache    # bypass cache for this run
jbom search "10k 0603" --supplier lcsc --clear-cache # delete cached results and re-query
```

## Known limitations

- **CON (connectors)**: keyword search only; ~0% hit rate observed in batch validation
  because KiCad connector attribute vocabulary does not map to JLCPCB's connector
  taxonomy. Manual search via `jbom search --supplier lcsc "..."` is the current workaround.
- **IND (inductors)**: keyword search only; parametric heuristics for inductors are
  planned in a follow-on issue.
- **Unofficial API**: The JLCPCB endpoint is undocumented and may change without
  notice. Cached results continue to work offline if the endpoint becomes unavailable.
- **Rate limiting**: Aggressive polling will trigger throttling. The 2s default is
  intentional. Do not reduce `rate_limit_seconds` below 1.0.

## Related

- [ADR 0002: JLCPCB/LCSC provider](../architecture/adr/0002-jlcpcb-lcsc-provider.md) —
  the architectural decision behind this provider
- [ADR 0003: Search heuristic signal framework](../architecture/adr/0003-search-heuristic-signal-framework.md) —
  the signal-based ranking model that sorts candidates
- `src/jbom/suppliers/lcsc/query_planner.py` — parametric query planner implementation
- `src/jbom/config/jlc.jbom.yaml` — supplier and fabricator configuration stanzas
