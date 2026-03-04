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

If an inventory item has no MPN, jBOM uses **Phase 4 parametric heuristics** to build
a structured query from the item's category and attributes:

| Category | Mode | Notes |
|---|---|---|
| RES | Parametric | Resistance, Tolerance, Package, Technology, Power |
| CAP | Parametric | Capacitance, Tolerance, Voltage, Dielectric, Package |
| IND | Keyword fallback | Parametric heuristics not yet implemented |
| CON | Keyword fallback | Connector taxonomy mismatch; expect low hit rate |
| Others | Keyword fallback | — |

Results are sorted stock-descending by default: high stock correlates with commodity
availability and price, naturally surfacing the parts experienced designers reach for.

## Configuration

The LCSC provider is configured in `src/jbom/config/suppliers/lcsc.supplier.yaml`:

```yaml
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
power ratings), create a `jbom-defaults.yaml` in your project directory. See
`src/jbom/config/defaults/generic.defaults.yaml` for the available keys.

## Cache

Search results are cached to disk at `~/.cache/jbom/` with a 24-hour TTL.
Repeated queries within the TTL window make no API calls.

```bash
jbom inventory-search --no-cache    # bypass cache for this run
jbom inventory-search --clear-cache # delete cached results and re-query
```

## Known limitations

- **CON (connectors)**: keyword search only; ~0% hit rate observed in batch validation
  because KiCad connector attribute vocabulary does not map to JLCPCB's connector
  taxonomy. Manual search via `jbom search --query "..."` is the current workaround.
- **IND (inductors)**: keyword search only; Phase 4 heuristics for inductors are
  planned in a follow-on issue.
- **Unofficial API**: The JLCPCB endpoint is undocumented and may change without
  notice. Cached results continue to work offline if the endpoint becomes unavailable.
- **Rate limiting**: Aggressive polling will trigger throttling. The 2s default is
  intentional. Do not reduce `rate_limit_seconds` below 1.0.

## See also

- Architecture decision: `docs/dev/architecture/adr/0002-jlcpcb-lcsc-provider.md`
- Batch validation findings: `docs/dev/validation/issue-123/summary.md`
- Phase 4 heuristics: `src/jbom/services/search/jlcpcb_phase4_heuristics.py`
- Default config: `src/jbom/config/defaults/generic.defaults.yaml`
