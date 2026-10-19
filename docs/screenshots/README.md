# Reviewer Evidence

## DQ-21 curated submission set

These nine screenshots are the minimum reviewer-facing set for the assignment.
They are losslessly cropped copies of the authoritative live evidence described
later in this index. The crops remove browser chrome, the workspace hostname,
the operator avatar, pipeline identifiers, and account email while preserving
the pipeline status, tables, result values, and relevant Databricks context.
No result pixels were synthesized or retouched.

| Requirement | Curated evidence |
| --- | --- |
| Successful Spark Declarative Pipeline | [`dq21_pipeline_completed.png`](dq21_pipeline_completed.png) |
| Representative Bronze tables | [`dq21_bronze_tables.png`](dq21_bronze_tables.png) |
| Representative Silver tables | [`dq21_silver_tables.png`](dq21_silver_tables.png) |
| Representative Gold tables | [`dq21_gold_tables.png`](dq21_gold_tables.png) |
| Question 1 values | [`dq21_question_1_values.png`](dq21_question_1_values.png) |
| Question 1 population-standard-deviation semantic | [`dq21_question_1_semantics.png`](dq21_question_1_semantics.png) |
| Question 2 readable labels and values | [`dq21_question_2_labels.png`](dq21_question_2_labels.png) |
| Question 2 observation status | [`dq21_question_2_status.png`](dq21_question_2_status.png) |
| Question 3 Q01 values and nullable population matches | [`dq21_question_3_values.png`](dq21_question_3_values.png) |

SHA-256 digests for the curated files:

| Screenshot | SHA-256 |
| --- | --- |
| `dq21_pipeline_completed.png` | `91e4e76c6d6a688aa832c57528f69de32c696a12e36d235e89e9cbf48f3b13da` |
| `dq21_bronze_tables.png` | `b24a5462df7c3a32b74a7584bb503edf9706b06c7a31ba0fc9bbd3b6fd8e5a7c` |
| `dq21_silver_tables.png` | `a83ce17d7ebe838bfee46743403243d4d63d51e9b026739a3a18ae34a470918b` |
| `dq21_gold_tables.png` | `3caf9a30bf60a7fdecc263ede6a46c7e7a856f30751f50b7f818fe947b82cac0` |
| `dq21_question_1_values.png` | `ed3151351aa779308aab7ef7c8235837be984029ff299b32cc5b209d72ff7bf1` |
| `dq21_question_1_semantics.png` | `2536e045c76e2a0b88d16e192f97772690bd7e3dbc2946b9b09f172a8bf161c8` |
| `dq21_question_2_labels.png` | `9c1b4e3b95e39c87985ef321cc92689a2b5ed902112b21489c1b0456b89263f2` |
| `dq21_question_2_status.png` | `5169b9d742b92493f5a2482e2faf3c548ddb24791d51ae09c1e767fba42a6f92` |
| `dq21_question_3_values.png` | `e77a709905b88f0f06e8c71d0f27c23f920558a9ee167da4291df7cc04a79e14` |

## Detailed implementation evidence

The remaining screenshots preserve the chronological implementation and review
record. They are indexed by card below, with exact claims and limitations in
`docs/evidence/`.

## DQ-07 BLS landing evidence

- `dq07_first_run_reconciliation.png`: 12 first-run active objects with byte
  counts, original run ID, and shortened digest evidence.
- `dq07_no_change_counts_publication.png`: second-run discovery, new, promoted,
  and published-transition counts.
- `dq07_no_change_counts_unchanged.png`: second-run removed, reused-version, and
  unchanged counts.
- `dq07_no_change_reconciliation.png`: post-rerun reconciliation retaining the
  original first-run manifest ID for all 12 objects.

Digest prefixes are displayed for safe, readable evidence. The notebook
recomputed and compared each complete 64-character SHA-256 digest.

## DQ-08 Data USA landing evidence

- `dq08_no_change_counts.png`: immediate rerun showing one unchanged response,
  zero promotions, and zero published transitions.
- `dq08_reconciliation_identity.png`: final active-object reconciliation showing
  the original run ID, shortened digest, path, and status.
- `dq08_reconciliation_schema.png`: complementary reconciliation view showing
  the four validated column names, byte size, record count, and year bounds.

Databricks exports the displayed column-name sequence as a struct with `_1`
through `_4` field labels. Those labels are serialization artifacts; the values
are the validated `Nation ID`, `Nation`, `Year`, and `Population` names.

The request-contact widget was excluded from committed evidence. Digest prefixes
are displayed for readability; the notebook compared the complete digest.

## DQ-11 Bronze pipeline evidence

- `dq11_bronze_run_completed.png`: pipeline update started at 5:46 PM EDT and
  marked `Completed`, with zero reported errors and warnings.
- `dq11_bronze_tables_expectations.png`: successful Bronze output counts and
  expectation results, including both BLS observation views, Data USA, and the
  source-contract audit.

The operator-recorded deployment revision, pipeline ID, displayed metrics,
evidence digests, attribution limitation, and scope boundary are indexed in
`docs/evidence/dq11_bronze_live_validation.md`.

## DQ-12 Silver pipeline evidence

- `dq12_silver_run_completed.png`: explicit `Completed` update, zero errors and
  warnings, validation views, and the successful approximately 77K-row table.
- `dq12_silver_performance.png`: finished refresh query and execution stages.
- `dq12_silver_pipeline_graph.png`: AllData normalization and uniqueness plus
  the independent Current consistency path feeding the published table.
- `dq12_silver_pipeline_selector.png`: confirms the `2 pipelines` badge is the
  Bronze/Silver navigation selector and names Silver as the current pipeline.

The operator-recorded revision, metric limits, evidence digests, and quality
interpretation are indexed in
`docs/evidence/dq12_silver_live_validation.md`.

## DQ-13 Silver series evidence

- `dq13_silver_series_run_completed.png`: completed update with zero errors and
  warnings and both Silver paths visible.
- `dq13_silver_series_graph.png`: provider series and five lookup dependencies
  feeding the candidate gate and published dimension.
- `dq13_silver_series_performance.png`: two successful materialized-view
  refresh statements.
- `dq13_silver_series_tables.png`: 282-row series result and unchanged green
  observation result.

The revision attribution, exact claims, limitations, and image digests are in
`docs/evidence/dq13_silver_series_live_validation.md`.

## DQ-14 Silver population evidence

- `dq14_bronze_scientific_notation_fail_closed.png`: diagnostic Bronze run in
  which the integral-form gate safely dropped all 11 scientific-notation rows.
- `dq14_bronze_population_corrected_success.png`: corrected Bronze run with 11
  population rows and all 10 expectations met.
- `dq14_silver_corrected_completed.png`: fresh completed Silver update on the
  reviewed correction with zero errors and warnings.
- `dq14_silver_corrected_tables.png`: fresh 77K observation, 282 series, and 11
  population results after full recompute.
- `dq14_silver_corrected_graph.png`: all three corrected Silver dependency paths.
- `dq14_silver_corrected_performance.png`: three successful corrected refresh
  statements.
- `dq14_sql_warehouse_capacity_limit.png`: recorded free-edition serverless
  capacity limit that blocked the supplemental fresh SQL retry.
- `dq14_silver_population_run_completed.png`: completed 8:14 PM EDT update with
  zero errors and warnings and all three Silver paths visible.
- `dq14_silver_population_tables.png`: 11-row population result, defined
  candidate and uniqueness expectations, and unchanged green observation and
  series results.
- `dq14_silver_population_graph.png`: isolated Bronze population-to-candidate,
  uniqueness, and published-table dependency chain.
- `dq14_silver_population_performance.png`: three successful materialized-view
  refresh statements.
- `dq14_silver_population_2013_2018_coverage.png`: read-only SQL and six result
  rows proving one published population value for every year from 2013 through
  2018.

The correction history, revision attribution, exact claims, limitations,
year-coverage result, and image digests are in
`docs/evidence/dq14_silver_population_live_validation.md`.

## DQ-16 Gold population summary evidence

- `dq16_gold_tables.png`: candidate expectation, successful published
  materialized view, one output record, and zero displayed errors or warnings.
- `dq16_gold_expectation_passed.png`: candidate expectation evaluated with
  fail action, zero percent failures, and zero failed records.
- `dq16_gold_performance.png`: successful materialized-view refresh and zero
  displayed errors or warnings.
- `dq16_gold_pipeline_graph.png`: Silver source, candidate gate, and published
  Gold materialized view.
- `dq16_gold_result_bounds.png`: Gold result start year, end year, year count,
  mean, and population standard deviation.
- `dq16_gold_result_semantics.png`: complementary Gold result view showing the
  population standard-deviation semantic.
- `dq16_sql_result_bounds.png`: successful tracked SQL-file execution and the
  left side of its one-row result.
- `dq16_sql_result_semantics.png`: complementary SQL result view showing the
  right side and population semantic.
- `dq16_sql_performance.png`: one completed SQL task and six source rows read.

The exact values, numerical comparison, revision attribution, evidence digests,
and claim boundaries are in
`docs/evidence/dq16_gold_population_summary_validation.md`.

## DQ-17 Gold BLS best-year evidence

- `dq17_gold_run_completed.png`: completed final Gold update with the metadata
  validation dependency and zero displayed errors or warnings.
- `dq17_gold_expectations.png`: both candidate expectations using the fail
  action with zero percent failures and zero failed records.
- `dq17_metadata_validation_run.png`: completed final update showing the new
  metadata-validation view and its fail-fast expectation in the table list.
- `dq17_gold_pipeline_graph.png`: both governed Silver sources feeding the
  candidate and published best-year materialized view.
- `dq17_gold_result_labels.png`: 282-row result with provider-grounded labels,
  selected years, annual quarterly sums, and visibly retained null selections.
- `dq17_gold_result_status.png`: quarterly counts and explicit observation
  availability flags, including the zero/false missing-history state.
- `dq17_sql_result.png`: successful final excluded Spark SQL alternative with
  its orphan-series guard, 282 rows, and readable labels.
- `dq17_sql_pyspark_parity.png`: read-only comparison returning 282 SQL rows,
  282 PySpark rows, and zero field-level mismatches.
- `dq17_independent_spot_check.png`: direct four-quarter Silver observations for
  `PRS30006032` in 1994, independently summing to `14.600000`.

The deployment attribution, exact validation claims, evidence digests, and
scope boundaries are indexed in
`docs/evidence/dq17_gold_bls_best_year_validation.md`.

## DQ-18 Gold BLS Q01 population-context evidence

- `dq18_gold_run_completed.png`: completed Gold update with the new Question 3
  dependency paths and zero displayed errors or warnings.
- `dq18_gold_tables.png`: 39-row published result, 8-second full recompute, and
  unchanged green Question 1 and Question 2 outputs.
- `dq18_gold_result_matches.png`: ordered BLS history showing both nullable
  unmatched years and populated matched years with explicit status values.
- `dq18_gold_columns.png`: the six published contract fields and their types.
- `dq18_candidate_expectations.png`: result cardinality and match-indicator
  expectations with zero failures.
- `dq18_input_expectations.png`: nonempty unique history and exact metadata
  cardinality expectations with zero failures.
- `dq18_sql_result.png`: successful excluded Spark SQL alternative returning
  39 rows.
- `dq18_sql_pyspark_parity_counts.png`: matching SQL/PySpark row and distinct-key
  counts.
- `dq18_sql_pyspark_parity_outcome.png`: matching 28-row missing-population
  counts and zero field-level mismatches.
- `dq18_independent_spot_check_values.png`: five direct Silver-to-Gold value and
  nullable-population comparisons.
- `dq18_independent_spot_check_matches.png`: all three comparison booleans true
  for all five representative rows.

The deployment attribution, exact results, evidence digests, causal claim
boundary, and limitations are indexed in
`docs/evidence/dq18_gold_bls_q01_population_validation.md`.

## DQ-19 Gold cross-implementation evidence

The `dq19_validation_*` images preserve the initial successful run before
Copilot review hardening. They are historical review evidence, not the final
acceptance run.

- `dq19_validation_checks_overview.png`: successful 17-row validation result
  showing the named Question 1, Question 2, and Question 3 checks and their
  actual and expected values.
- `dq19_validation_performance.png`: successful Databricks execution with 85 of
  85 tasks completed.
- `dq19_validation_passed.png`: the result's `passed` and `interpretation`
  columns showing true outcomes for every displayed check.
- `dq19_validation_checks_complete.png`: the final result rows proving all 17
  checks are present, including Question 3 bounds, spot check, and key parity.
- `dq19_validation_passed_complete.png`: the lower result rows with the
  `passed` column visible, directly confirming true outcomes through row 17.
- `dq19_final_passed_rows_1_14.png`: corrected revision with true outcomes for
  rows 1–14, including the independent Question 1 calculation.
- `dq19_final_values_rows_1_14.png`: corrected actual values, including zero
  Question 1 source discrepancies and `282,0` Question 2 inventory/metadata.
- `dq19_final_values_rows_4_17.png`: corrected lower values, including
  Question 3 preservation `39,39,1988,2026` and sample coverage `5,5,0`.
- `dq19_final_passed_rows_4_17.png`: corrected revision with true outcomes for
  rows 4–17, completing direct evidence that all 17 checks passed.
- `dq19_post_review_passed_rows_1_14.png`: final reviewed revision with true
  outcomes for rows 1–14 and analyzed schema signatures.
- `dq19_post_review_passed_rows_4_17.png`: final reviewed revision with true
  outcomes for rows 4–17, completing direct proof that all 17 checks passed.
- `dq19_post_review_values_rows_1_14.png`: final reviewed actual values for the
  upper checks, including analyzed Question 1 and Question 2 schemas.
- `dq19_post_review_values_rows_4_17.png`: final reviewed lower values,
  including Question 3 preservation and five-year source coverage.
- `dq19_post_review_performance.png`: successful final reviewed execution with
  111 of 111 tasks completed.

The `dq19_post_review_*` captures are the authoritative final acceptance run;
the earlier `dq19_validation_*` and `dq19_final_*` images are retained as
review history.

The exact validation claims, intentional representation differences, evidence
digests, and scope boundary are indexed in
`docs/evidence/dq19_gold_cross_implementation_validation.md`.

