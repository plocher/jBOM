# Issue #123 Findings: AltmillSwitchController + AltmillSwitchRemote
## Why combined
Issue #123 referenced `AltmillSwitches`. In this workspace, the equivalent projects are `AltmillSwitchController` and `AltmillSwitchRemote`, so findings are reported together.

## Sparse detection
### AltmillSwitchController
- Inventory rows: 18
- Searchable rows (`--dry-run`): 10
- Searchable by category: `CAP=5`, `IC=1`, `RES=4`
- Excluded rows: 8 (`UNKNOWN=7`, `SWI=1`)

### AltmillSwitchRemote
- Inventory rows: 6
- Searchable rows (`--dry-run`): 4
- Searchable by category: `CAP=2`, `RES=2`
- Excluded rows: 2 (`UNKNOWN=1`, `SWI=1`)

Interpretation:
- Expected exclusion behavior held for non-search categories (`UNKNOWN`, `SWI`).
- No obvious “already filled LCSC” suppression appeared in these fresh `jbom inventory` outputs.

## Query quality and hit rate (LCSC)
### AltmillSwitchController
- Total searchable: 10
- Successes: 4 (40.0%)
- Failures: 6 (60.0%)
- Category hit rates:
  - `RES`: 3/4 (75.0%)
  - `CAP`: 1/5 (20.0%)
  - `IC`: 0/1 (0.0%)

Representative successful query:
- `10K resistor 0603 5%` → candidates returned, high match score.

Representative failure queries:
- `DCJ0202 capacitor DCJ0202` (power jack treated as capacitor)
- `Conn_01x02 capacitor ...` (connector symbol treated as capacitor)
- `4N28SM IC SMDIP-6_W7.62mm` (no candidates)

### AltmillSwitchRemote
- Total searchable: 4
- Successes: 2 (50.0%)
- Failures: 2 (50.0%)
- Category hit rates:
  - `RES`: 2/2 (100.0%)
  - `CAP`: 0/2 (0.0%)

Failure examples:
- `Conn_6P6C capacitor RJ12_TOP`
- `1e+03uF capacitor CP_Elec_10x10`

## Ranking quality observations
- Multi-candidate rows reviewed:
  - Controller: 4
  - Remote: 2
- Pattern:
  - `RES` rows often produce ranked candidates, but top-1 repeatedly includes `CC0603KRX7R9BB104` for multiple resistor values, suggesting ranking/scoring instability or category/value mismatch leakage.
  - Valid-looking resistor rankings also appear (`10K` query returning resistor-family parts with descending relevance).

## False positives and intentional sparseness
- Intentional exclusions (`SWI`, `UNKNOWN`) were correctly excluded.
- Main false-positive pattern was not excluded items; it was searchable items with connector/power-jack semantics encoded as `CAP`, leading to low-quality capacitor queries.

## Project-level conclusion
The AltmillSwitch family supports the issue premise: sparse detection itself is mostly acceptable, but query construction and ranking quality are not yet reliable outside straightforward resistor cases.
