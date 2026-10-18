# Machine-readable validation evidence

These CSV exports preserve the result rows displayed by the Databricks landing
notebooks. They contain no credentials or contact-widget values.

## DQ-08 Data USA landing

- `dq08_first_run.csv`: first landing counts and parsed response summary.
- `dq08_first_reconciliation.csv`: first committed-object reconciliation.
- `dq08_no_change_run.csv`: immediate rerun counts and response summary.
- `dq08_no_change_reconciliation.csv`: final reconciliation retaining the
  original published run ID.

The screenshots in `docs/screenshots/` are the primary reviewer-facing evidence;
these exports support exact value inspection.

## DQ-41 Spark manifest adapter validation

- `dq41_spark_manifest_validation.csv`: live Databricks result proving four
  transitions remained after two writes, two current paths were selected, the
  expected timestamp/run-ID winner was returned as removed, and all 11 manifest
  columns were present.
