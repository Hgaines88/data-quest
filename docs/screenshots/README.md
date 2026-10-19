# Reviewer Evidence

Required screenshots of the Databricks pipeline, representative tables, and all three analytical outputs will be stored here. Images must be descriptively named and reviewed for sensitive information before they are committed.

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

