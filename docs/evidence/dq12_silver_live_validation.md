# DQ-12 Silver live validation

## Result

The `data-quest-silver` triggered update completed successfully in Databricks on
October 18, 2026 at 7:21 PM EDT. The update reported zero errors and zero
warnings. The published `silver_bls_observation` materialized in 5 seconds with
approximately 77,000 output rows (the table view rounds the count to `77K`).

This run validates the Silver implementation at branch head `b0247c0`. The
commit association is operator-recorded because the Databricks update screen
does not display a Git SHA.

## Evidence

- [Completed update and table result](../screenshots/dq12_silver_run_completed.png)
  shows the explicit `Completed` status, zero errors and warnings, the four
  Silver datasets, and the successful published table.
- [Pipeline graph](../screenshots/dq12_silver_pipeline_graph.png) shows the
  intended dependency structure: AllData feeds normalization and uniqueness;
  Current feeds the consistency gate; both gates feed the published table.
- [Performance details](../screenshots/dq12_silver_performance.png) show the
  refresh query finished and processed approximately 77.13K rows through the
  execution stages.
- [Pipeline selector](../screenshots/dq12_silver_pipeline_selector.png) confirms
  that the editor's `2 pipelines` badge refers to the separate
  `data-quest-silver` and `data-quest-bronze` pipelines associated with the same
  Git folder. `data-quest-silver` is the current pipeline; the badge does not
  mean the Silver source ran twice or belongs to the Bronze pipeline.

The committed screenshot SHA-256 digests are:

| Screenshot | SHA-256 |
|---|---|
| `dq12_silver_run_completed.png` | `71460cce37e7f04a007e89f8eecdf6e933db969cbb05b5c5edc46d0048223509` |
| `dq12_silver_performance.png` | `7dbe042462529681e8d83eced0998c5407c8928a11ebe60c16387785701e4cb6` |
| `dq12_silver_pipeline_graph.png` | `e241d9562d0e671c7c5c1f6750b796a24d8bff4349547815e65574ac647e078e` |
| `dq12_silver_pipeline_selector.png` | `40d54e1757ad446112a901d4bb42e71a7ff817c2403ff00908b20879bb2dd54e` |

## Quality interpretation

The successful publication is meaningful because `silver_bls_observation`
depends on two fail-fast temporary views:

1. `unique_silver_bls_observations` rejects any duplicate normalized business
   key (`series_id`, `year`, `period_code`).
2. `bls_current_consistency` rejects any normalized Current record that does
   not match the unique AllData candidate on the full key and value.

The candidates view also applies five named drop expectations before either
gate. Databricks displays those expectations as defined on the temporary views;
it does not show per-expectation `met` counts in the captured table screen.
Therefore this evidence does not claim a numeric count for each rule. It does
show that the fail-fast uniqueness and Current-consistency gates completed and
that the final table was published with no pipeline error or warning.

## Engineering judgment

The implementation deliberately separates normalization, uniqueness, and
cross-file consistency instead of hiding all three decisions in one transform.
That decomposition made failures attributable, kept the public model to one
table, and preserved a simple explanation of why publication is trustworthy.
Malformed numeric text uses ANSI-safe `try_cast`, allowing the named validity
expectations to observe and drop bad rows rather than letting Spark terminate
the update before quality rules run. No arbitrary duplicate winner is chosen,
because doing so could silently change analytical totals.

