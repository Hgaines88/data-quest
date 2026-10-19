# DQ-13 Silver series live validation

## Result

The `data-quest-silver` triggered update completed successfully in Databricks on
October 18, 2026 at 7:55 PM EDT. The update reported zero errors and zero
warnings. `silver_bls_series` published exactly 282 rows in 7 seconds, matching
the 282-row Bronze series inventory recorded during DQ-11. The previously
validated `silver_bls_observation` remained green and was reported as
`No change`, so the metadata extension did not recompute or alter that output.

This run validates DQ-13 branch head `bfb044c`. The commit association is
operator-recorded because the Databricks update screen does not display a Git
SHA.

## Evidence

- [Completed update](../screenshots/dq13_silver_series_run_completed.png) shows
  the explicit `Completed` status, zero errors and warnings, pipeline ID, and
  both the metadata and observation paths in the update graph.
- [Pipeline graph](../screenshots/dq13_silver_series_graph.png) shows
  `bronze_bls_series` plus sector, class, measure, duration, and seasonal lookup
  tables feeding `silver_bls_series_candidates`, then `silver_bls_series`.
- [Performance summary](../screenshots/dq13_silver_series_performance.png) shows
  both materialized-view refresh statements finished successfully.
- [Table results](../screenshots/dq13_silver_series_tables.png) show the
  candidate gate, the 282-row published series dimension, its 7-second full
  recompute, and the unchanged green observation table.

The committed screenshot SHA-256 digests are:

| Screenshot | SHA-256 |
|---|---|
| `dq13_silver_series_run_completed.png` | `44ae80922a3aa39f3da07d7ef067e9d58ade35f1eca7f046400b4447130859f1` |
| `dq13_silver_series_graph.png` | `9b2de4c8c4fcb995b1b8abb46d9bb67067990f8c933ee814cf6c9718f70ea5e7` |
| `dq13_silver_series_performance.png` | `d22274a69030bc8c00057c422c371a944533006ccde74a4fb6d68a13e2e65c80` |
| `dq13_silver_series_tables.png` | `3bb6a1479f514a6093510824e11bd01110e79ca1ff3a58a6f6086fccc3a12ced` |

## Quality interpretation

The candidate view has one fail-fast expectation requiring complete provider
lookup coverage and exactly one joined row per `series_id`. A missing lookup,
duplicate series, or duplicated lookup key would violate that gate and prevent
the dependent materialized view from publishing. The completed update and the
282-row result therefore establish that every Bronze series produced exactly
one fully labeled Silver row for this source snapshot.

The UI labels the gate as `1 defined`; it does not display a separate numeric
`met` count in the captured table view. This evidence consequently claims only
what the successful dependency and update state prove, not an unsupported
per-rule metric.

