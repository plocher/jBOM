# Issue #123 Summary and recommendations
## Cross-project metrics (LCSC primary)
Projects measured:
- `AltmillSwitchController`
- `AltmillSwitchRemote`
- `Core-wt32-eth0`
- `LEDStripDriver`

Total searchable rows across runs: 39
Total successful searches: 17 (43.6%)

Category hit rates:
- `RES`: 10/11 (90.9%)
- `CAP`: 7/21 (33.3%)
- `IC`: 1/3 (33.3%)
- `CON`: 0/4 (0.0%)

## What the data says
1. Sparse detection is mostly calibrated.
- Expected non-search rows (`UNKNOWN`, `SWI`) were excluded consistently in these projects.
- The dominant issue is not excluded-category leakage; it is semantically weak rows in searchable categories.

2. Query quality is uneven and category-dependent.
- `RES` performs strongly.
- `CAP` quality is mixed because connector/function-like values and footprints can be pulled into capacitor-style queries.
- `CON` is currently non-viable in this sample (0% hit rate).

3. Ranking quality is not yet dependable.
- Multi-candidate rows reviewed: 18 (all available under the requested sampling policy).
- Several rows show repeated top-1 candidates across materially different values/categories, indicating scoring/ranking is not robust enough for confident interactive “pick best” workflows.

4. Provider choice is a secondary factor.
- Optional Mouser comparison (`LEDStripDriver`) improved overall success modestly (63.6% vs 54.5%) and IC outcomes, but connector failures remained 0/4 in both providers.
- This points to query/category normalization as the first-order problem.

## Recommendations for #99, #100, #101, #102
## #99 interactive model
Do not prioritize full interactive mode yet. Current connector and mixed-category quality means the operator would spend time rejecting bad/noisy rows, reducing UX value.

## #100 multi-candidate write-back
Prioritize the non-interactive “batch candidate rows + spreadsheet delete” stepping stone first. It fits current pipeline quality better and allows rapid human triage without new UI complexity.

## #101 explain output
Proceed partially now. Adding score/query rationale to existing batch output is useful immediately for diagnosing bad category/value mappings and ranking anomalies.

## #102 smart query batching
Defer. Batching efficiency gains should follow query quality fixes; optimizing dispatch over low-quality queries compounds noise faster.

## Suggested near-term execution order
1. Improve query/category normalization for connector-like and mislabeled capacitor rows.
2. Strengthen ranking/scoring to reduce repeated top-1 anomalies across different values.
3. Extend explainability output (#101) to make per-row decisions auditable.
4. Add `--top N` batch write-back mode from #100 as the first workflow enhancement.
5. Re-run this validation suite; only then reconsider #99 interactive flow as default.
