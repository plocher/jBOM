# Issue #123 Findings: LEDStripDriver
## Sparse detection
- Inventory rows: 20
- Searchable rows (`--dry-run`): 11
- Searchable by category: `CAP=4`, `CON=4`, `IC=2`, `RES=1`
- Excluded rows: 9 (`UNKNOWN=9`)

Interpretation:
- Expected exclusion behavior held for `UNKNOWN`.
- This project is useful because it includes connector and IC categories directly in the searchable set.

## Query quality and hit rate (LCSC)
- Total searchable: 11
- Unique queries: 10
- Successes: 6 (54.5%)
- Failures: 5 (45.5%)
- Category hit rates:
  - `CAP`: 4/4 (100.0%)
  - `RES`: 1/1 (100.0%)
  - `IC`: 1/2 (50.0%)
  - `CON`: 0/4 (0.0%)

Representative successful queries:
- `150uF capacitor CP_Elec_8x10`
- `DMN4468 IC soic`

Representative failed queries:
- `CONNECTOR-M02MSTBA2 connector ...`
- `GROVE-4P-2.0 connector 4P-2.0`
- `PCA9685PW IC tssop`
- `CONNECTOR-M045.08 connector ...`

## Ranking quality observations
- Multi-candidate rows reviewed: 6 (all available)
- `IC_DMN4468` ranked plausibly with two close MPN variants.
- `RES_10k` and `CAP_0.1uF` again show repeated top-1 candidate patterns that do not consistently reflect expected part-family distinctions.
- Connector rows had no candidates, so rank quality is undefined there.

## Optional provider comparison (Mouser)
Same project, same sparse inventory:
- LCSC: 6/11 successes (54.5%)
- Mouser: 7/11 successes (63.6%)

By category:
- `CON`: 0/4 for both providers
- `CAP`: 4/4 for both providers
- `IC`: LCSC 1/2 vs Mouser 2/2

Interpretation:
- Connector failure appears query/category-shaping related, not provider-specific.
- Some IC misses may be provider-specific or provider-coverage-sensitive.

## Project-level conclusion
`LEDStripDriver` is the clearest signal that connector handling must improve before building interactive flows. Provider choice alone does not address the dominant connector miss pattern.
