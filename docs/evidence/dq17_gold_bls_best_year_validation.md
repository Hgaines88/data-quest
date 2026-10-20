# DQ-17 Gold BLS best-year live validation

## Deployment identity

- Git revision: `5009e0c2c2fea025b79df856c2026dffe1e232b7`
- Branch: `codex/dq-17-bls-best-year`
- Pipeline: `data-quest-gold`
- Pipeline identifier omitted from the submission
- Validated on: October 19, 2026

The operator pulled the reviewed feature revision into the Databricks Git
folder before starting the update. The screenshots establish the deployed
revision context and live results; they do not independently prove the remote
Git commit identity.

## Pipeline result

The final triggered Gold update completed at 2:45 PM EDT with zero displayed
errors or warnings.
`gold_bls_best_year_by_series` published 282 rows while the existing population
summary remained green and unchanged. The dependency graph shows validated
`silver_bls_observation` and `silver_bls_series` feeding the candidate view and
published materialized view.

The final graph also contains `gold_bls_series_metadata_validation`, which
requires every quarterly observation series to resolve to exactly one Silver
metadata row before the Gold candidate can publish. Its fail-fast expectation
passed as part of the completed update.

Both candidate expectations used the `FAIL` action and recorded zero percent
failures and zero failed records:

- exactly one output row per expected `series_id`;
- each row has either a complete selected quarterly result or an explicit
  missing-history state.

The result inspection shows provider-grounded labels, deterministic best years,
annual `Q01`-through-`Q04` sums, four observations for complete selected years,
and `has_quarterly_observations = true`. Series without quarterly observations
remain visible with null year and sum, count zero, and the flag set to false.

## Independent SQL parity

After the metadata guard was added, the excluded, reviewer-visible
`sql/alternatives/question_2_bls_best_year.sql` query ran successfully against
the same governed Silver tables at 2:49 PM EDT and returned 282 rows without
raising its orphan-series error. A separate read-only
full-outer comparison used null-safe equality across the label, year, sum,
observation count, and availability flag. It returned:

| Check | Result |
| --- | ---: |
| SQL rows | 282 |
| PySpark rows | 282 |
| Field-level mismatches | 0 |

This proves row-count, key, null-behavior, and value parity between the two
implementations for the validated revision.

## Independent source-level spot check

For `PRS30006032`, the selected Gold result is year 1994 with an annual
quarterly sum of `14.600000`. A separate read-only query retrieved the four
Silver observations directly:

| Period | Value |
| --- | ---: |
| Q01 | 1.700000 |
| Q02 | 4.000000 |
| Q03 | 4.200000 |
| Q04 | 4.700000 |

Their independent window sum is `14.600000`, and the window count is four on
every row. This reconciles the selected Gold value without reading the Gold
table as the calculation source. The Gold ranking and committed SQL both order
annual sums descending and years ascending, so the earliest year wins any tie.

## Evidence files

| Screenshot | SHA-256 |
| --- | --- |
| `dq17_gold_run_completed.png` | `35e08a54bc04b99a25ed952ce65b35180e54818f1c705d5c74b2e2f812cc4337` |
| `dq17_gold_expectations.png` | `63b94ffefad4d22c2ac2e414e969d2b1676013a3ead7ac049f9c9bcc2df27bca` |
| `dq17_metadata_validation_run.png` | `4f5b43f5bda65938af13e000eec21926dbec2794be7d7ab3dd87293a2c0c08c0` |
| `dq17_gold_pipeline_graph.png` | `c45351116b65afef3e73aeb3f1ee9d3ca557de87b106afc92a3a590c44da84a5` |
| `dq17_gold_result_labels.png` | `02c0c2bdafd35fa673c38a505c6577797a75e5155926101591cde3649507035d` |
| `dq17_gold_result_status.png` | `8c774e14c6c753858544edd9bac4fe2f2a6e1b5968d7d1bd396a4970389f0aa2` |
| `dq17_sql_result.png` | `78e872594df511f446cdef714e446014b31071d60b9e02fb26d07f5c053eb131` |
| `dq17_sql_pyspark_parity.png` | `1acd417edefb5932c97d1a78bb6d3baec818a7d8de7448e42a2b8ce5ea6c579b` |
| `dq17_independent_spot_check.png` | `eeb772d4c4862361aeb3ccad1adf2a1848ebe740ea0502132868bf688862f706` |

## Scope boundary

This evidence validates Question 2's governed Gold contract. It does not claim
that every BLS series has quarterly history, interpret a missing series as a
data error, or establish business causality. Dashboard and Genie presentation
remain downstream work.
