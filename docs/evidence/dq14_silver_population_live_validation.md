# DQ-14 Silver population live validation

## Result

The `data-quest-silver` triggered update completed successfully in Databricks on
October 18, 2026 at 8:14 PM EDT. The update reported zero errors and zero
warnings. `silver_population` published 11 rows in 6 seconds. The previously
validated `silver_bls_observation` and `silver_bls_series` outputs remained
green and were both reported as `No change`, so adding the population path did
not recompute or alter either existing Silver output.

This run validates DQ-14 branch head `b052817`. The commit association is
operator-recorded because the Databricks update screen does not display a Git
SHA.

## Evidence

- [Completed update](../screenshots/dq14_silver_population_run_completed.png)
  shows the explicit `Completed` status, zero errors and warnings, the pipeline
  ID, and all three Silver paths in the update graph.
- [Table results](../screenshots/dq14_silver_population_tables.png) show four
  candidate expectations defined, one uniqueness expectation defined, the
  11-row population output, its 6-second full recompute, and both existing
  Silver outputs remaining green with `No change`.
- [Pipeline graph](../screenshots/dq14_silver_population_graph.png) shows
  `bronze_datausa_population` feeding `silver_population_candidates`, then the
  uniqueness gate, and finally `silver_population`.
- [Performance summary](../screenshots/dq14_silver_population_performance.png)
  shows three materialized-view refresh statements finishing successfully.
- [2013–2018 coverage query](../screenshots/dq14_silver_population_2013_2018_coverage.png)
  shows a successful read-only query returning exactly six ordered rows: one
  each for 2013, 2014, 2015, 2016, 2017, and 2018.

The committed screenshot SHA-256 digests are:

| Screenshot | SHA-256 |
|---|---|
| `dq14_silver_population_run_completed.png` | `53129f6a7f694e88dd1de9c9633bd2a9cc7d133b57dc1d6c45a321aa0b7eb6e0` |
| `dq14_silver_population_tables.png` | `c429412d45ef8490a25bf3fa6a7536f4e55ff63a387d436ac669bef501facbd8` |
| `dq14_silver_population_graph.png` | `0e6175bf9bd471462a4f4ef0be99ef31fd08567137eb8bb49a86909ab960d9d2` |
| `dq14_silver_population_performance.png` | `bc4df36e8bbed868a75866a45525e17a20368cc7580d304d523386268f6e8533` |
| `dq14_silver_population_2013_2018_coverage.png` | `4b4598b4736ad1738da143b13b21c149836bfda8c3fce2c8fd82429ed627edde` |

## Quality interpretation

The candidate view drops and measures records that violate the exact US
national grain, integer-year rule, nonnegative exact-integral population rule,
or provenance rule. Its downstream fail-fast expectation requires exactly one
row for each `nation_id + year`. Successful publication therefore establishes
that all 11 published rows passed those gates and have unique business keys for
this source snapshot.

The UI labels the candidate rules as `4 defined` and the uniqueness rule as
`1 defined`; it does not display separate numeric `met` counts in the captured
table view. This record consequently makes no unsupported per-rule count claim.

The separate SQL result capture closes the year-coverage boundary without
inferring it from the 11-row total. It directly shows exactly one published row
for every requested year from 2013 through 2018. This establishes DQ-14's
coverage requirement while leaving the later Gold pipeline responsible for
enforcing the six-year analytical range at its own publication boundary.
