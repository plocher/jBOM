# Issue #123 Methodology: inventory-search batch validation
## Scope
This validation tests whether the current batch `inventory-search` pipeline is strong enough to justify follow-on interaction work in #99, #100, #101, and #102.

Projects evaluated:
- `AltmillSwitchController`
- `AltmillSwitchRemote`
- `Core-wt32-eth0`
- `LEDStripDriver`

Primary provider:
- `lcsc` (JLCPCB/LCSC alignment for tutorial and fabrication workflow relevance)

Secondary comparison:
- `mouser` on `LEDStripDriver` only, to separate provider effects from query-construction effects.

## Commands run
For each project:
```bash
jbom inventory <project-path> -o /tmp/jbom-issue-123/<project>-sparse.csv -F
jbom inventory-search /tmp/jbom-issue-123/<project>-sparse.csv --provider lcsc --dry-run
jbom inventory-search /tmp/jbom-issue-123/<project>-sparse.csv --provider lcsc \
  -o /tmp/jbom-issue-123/<project>-candidates-lcsc.csv \
  --report /tmp/jbom-issue-123/<project>-report-lcsc.txt -F
```

Optional comparison run:
```bash
jbom inventory-search /tmp/jbom-issue-123/LEDStripDriver-sparse.csv --provider mouser \
  -o /tmp/jbom-issue-123/LEDStripDriver-candidates-mouser.csv \
  --report /tmp/jbom-issue-123/LEDStripDriver-report-mouser.txt -F
```

## Measurement approach
- Sparse detection:
  - `inventory_rows` from generated sparse CSV
  - `dry_run_searchable` and searchable category counts from `--dry-run`
  - excluded count/category inferred as `inventory_by_category - searchable_by_category`
- Query quality and hit rate:
  - Overall and by-category hit rate from report files (`success/total`)
  - Representative success/failure query samples from enhanced candidate CSV
- Ranking quality:
  - Multi-candidate rows only (`Candidate 2 MPN` present)
  - Stratified review policy requested for this issue:
    - categories expected to work well (`RES`, `CAP`)
    - vocabulary-risk categories (`CON`, `IC`)
    - zero-result rows
  - Because all categories had fewer than 10 multi-candidate rows per project, all available multi-candidate rows were reviewed.
- Intentional sparseness correctness:
  - `UNKNOWN` and `SWI` rows were treated as expected exclusions.
  - False-positive focus was placed on connector-like and non-passive symbols that landed in searchable categories.

## Notes
- Raw CSV/report artifacts were intentionally kept local under `/tmp/jbom-issue-123/` to avoid noisy repository diffs.
- Repository artifacts for this issue capture analysis and recommendations only.
