# Spark manifest adapter validation

This runbook closes the evidence boundary between controlled adapter unit tests
and execution on Databricks. The fake-backed tests verify generated statements,
row mapping, validation, and writer calls; they do not execute Spark SQL or
Delta Lake.

## Preconditions

- Open `notebooks/03_validate_manifest_adapter.py` from this repository's
  Databricks Git folder.
- Attach the same authorized general or serverless Python compute used for the
  landing notebooks. A SQL Warehouse cannot execute the Python cells.
- Keep the verified `workspace.rearc_data_quest` defaults unless the authorized
  workspace differs.
- Do not run two copies concurrently. Each run uses a random table suffix, but
  the repository's assessment workflow remains single-writer.

## Execution

Run all cells in order. The notebook creates a uniquely named temporary Delta
table, calls the table-creation function twice to prove idempotency, appends four
synthetic contract-valid transitions in one batch, and loads current state.

The two `ranked.txt` rows with the latest timestamp differ only by lexical
`run_id`. The expected winner is `20261018T010000Z-b` with status `removed`,
which proves that the executed window uses timestamp then run-ID ordering. An
independent `other.txt` row proves partitioning by relative path.

Expected output:

- `inserted_transition_count = 4`
- `current_path_count = 2`
- `ranked_run_id = 20261018T010000Z-b`
- `ranked_status = removed`
- `schema_column_count = 11`

The `finally` block drops the temporary table on success or assertion failure.
If compute terminates before cleanup, locate only the table whose generated
name begins `spark_manifest_validation_`, verify that it belongs to this run,
and drop that table manually. Never drop either ingestion manifest.

## Claim boundary

This validation proves that the adapter's current DDL, DataFrame append, and
latest-state query execute together on the observed Databricks runtime. It does
not prove concurrency safety, clock monotonicity, or behavior on another Spark
or Delta version.
