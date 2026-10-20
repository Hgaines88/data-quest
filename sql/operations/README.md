# Operational SQL

These read-only queries are the reviewer-facing operational surface for DQ-27.
Run them as the project owner because Databricks restricts `event_log(...)` to
the owner of the materialized view or streaming table being inspected.

- `inspect_health.sql` reports landing-run counts, source and Gold freshness,
  Gold contract row counts, and recent sanitized failures.
- `inspect_pipeline_expectations.sql` reports expectation pass/fail counts for
  the latest Bronze, Silver, and Gold updates.

The checked-in queries target the production contract
`workspace.rearc_data_quest`. For an isolated bundle development deployment,
replace only the schema name with the reviewed per-user output schema from the
bundle plan. Do not commit that generated schema name or any workspace IDs.

Neither query mutates data, changes privileges, or contains notification
destinations. Thresholds, alerting choices, and recovery steps are documented
in [`docs/OPERATIONAL_OBSERVABILITY.md`](../../docs/OPERATIONAL_OBSERVABILITY.md).
