# Issue #123 Findings: Core-wt32-eth0
## Sparse detection
- Inventory rows: 23
- Searchable rows (`--dry-run`): 14
- Searchable by category: `CAP=10`, `RES=4`
- Excluded rows: 9 (`UNKNOWN=8`, `SWI=1`)

Interpretation:
- Exclusions are consistent with expected non-search categories.
- Searchable set is dominated by passives, which is useful for baseline quality measurement.

## Query quality and hit rate (LCSC)
- Total searchable: 14
- Unique queries: 13
- Successes: 6 (42.9%)
- Failures: 8 (57.1%)
- Category hit rates:
  - `RES`: 4/4 (100.0%)
  - `CAP`: 2/10 (20.0%)

Representative successful queries:
- `10K resistor 0603 5%`
- `10uF capacitor 1206`

Representative failed queries:
- `IO capacitor Connector_PlexiData`
- `FTDI Programmer capacitor Connector_FTDI-DEVICE-SIDE`
- `Conn_01x02 capacitor PinHeader_1x02_P2.54mm_Vertical`

Interpretation:
- Many failures are connector-like semantics mapped into `CAP` rows, not pure passive capacitor value lookups.

## Ranking quality observations
- Multi-candidate rows reviewed: 6 (all available)
- For resistor rows:
  - Rankings are consistent in shape but sometimes repeat top candidates across distinct resistor values.
- For capacitor rows:
  - Some high-confidence results look plausible (`10uF 1206` family).
  - `100nF capacitor 0603` produced top-1 `CC0603KRX7R9BB104`, likely not the intended capacitor-family match.

## False positives and intentional sparseness
- `UNKNOWN` and `SWI` were excluded as expected.
- Operational false positives are mostly “searchable but semantically wrong” rows (connector/function labels mapped as `CAP`) rather than excluded-category leakage.

## Project-level conclusion
`Core-wt32-eth0` confirms strong `RES` behavior but weak mixed `CAP` behavior due to category/value semantics. This supports prioritizing query/category normalization before interactive UX work.
