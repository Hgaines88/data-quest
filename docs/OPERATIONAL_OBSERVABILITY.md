# Operational observability and recovery

## Purpose and boundary

This runbook lets an operator answer three questions without exposing secrets
or personal information:

1. Did both source landings complete recently and what happened to each file?
2. Did the Bronze, Silver, and Gold pipelines complete with acceptable quality?
3. If a run failed, where should recovery start and what last-good state remains?

The design preserves the existing single-writer contract. Only the two landing
notebooks append to `ingestion_run_audit`, and they are never scheduled inside
the downstream bundle job. Pipelines and reviewer queries remain read-only with
respect to the source schema.

## Signals

| Signal | Authoritative source | Healthy | Warning | Failure |
| --- | --- | --- | --- | --- |
| BLS and Data USA landing freshness | Latest terminal row per source in `ingestion_run_audit` | `SUCCEEDED`, age < 24 h | Successful age 24–48 h | Latest outcome `FAILED` or age > 48 h |
| File processing | `ingestion_run_audit` | `failed_file_count = 0`; counts reconcile to the run | Unexpected nonzero removals or changes require source review | Any failed file or failed terminal run |
| Gold freshness | Latest terminal Gold `update_progress` event | `COMPLETED`, age < 24 h | Completed age 24–48 h | `FAILED`/`CANCELED` or age > 48 h |
| Gold contracts | Direct counts in `inspect_health.sql` | 1 / 282 / 39 rows | Not applicable | Any exact count mismatch |
| Pipeline quality | Latest `flow_progress` expectation arrays | Zero failed records | Nonzero failures on a retain-only advisory expectation | Dropped records or a fail-fast expectation blocks the update |
| Workflow execution | Lakeflow Jobs run page; optionally `system.lakeflow.job_run_timeline` | All three tasks succeed in order | Queue/runtime materially exceeds its recent baseline | Any task fails, times out, or is canceled |
| Deployment | `databricks bundle validate/plan/deploy` output | Valid, reviewed plan; post-deploy plan has no changes | Unexpected change requiring review | Validation/deployment error or unreviewed destructive change |

The 24/48-hour limits are operational exercise thresholds, not claims about
the publication cadence of BLS or Data USA business periods. They are strict
enough to expose a missed daily exercise run and can be relaxed only after an
owner documents an agreed service level.

`skipped_count` means a downloaded and hash-verified file whose immutable
version and manifest state were unchanged, so publication was skipped. The
landing implementation deliberately downloads every discovered source object
before comparing its digest; it does not infer unchanged content from provider
headers alone. `downloaded_count` therefore equals `discovered_count` on a
successful run. A failed run reports only completely verified downloads known
at its terminal stage; it never guesses partial progress.

## Operator procedure

1. Run [`sql/operations/inspect_health.sql`](../sql/operations/inspect_health.sql)
   as the project owner. Confirm two current successful source rows, healthy
   Gold status, exact Gold counts, and no unexplained recent failures.
2. Run
   [`sql/operations/inspect_pipeline_expectations.sql`](../sql/operations/inspect_pipeline_expectations.sql).
   Confirm every layer's `update_state` is `COMPLETED` and every non-null
   expectation row has `passed = true`. A status-only row with null expectation
   counts means that update emitted no expectation metrics; it is not evidence
   of zero rejected records. For drop expectations, failed records are rejected
   rows. For fail-fast expectations, a failure blocks the update and the prior
   published table remains the last-good result. This
   project has no quarantine table; it reports that explicitly rather than
   implying that rejected data was retained elsewhere.
3. Open the refresh job and confirm `refresh_bronze`, `refresh_silver`, and
   `refresh_gold` completed in dependency order. The UI is the immediate
   diagnostic surface. Where account system tables are enabled, retain the
   `system.lakeflow.job_run_timeline` and
   `system.lakeflow.pipeline_update_timeline` queries described in the official
   [jobs system-table reference](https://docs.databricks.com/aws/en/admin/system-tables/jobs)
   as longer-lived history; system-table delivery can lag.
4. Inspect categorical failure fields before opening raw task output. Raw
   messages can contain provider URLs or operator context and are not copied
   into evidence, tickets, or committed files.

The event-log query follows Databricks' documented
[`event_log` table-valued function](https://docs.databricks.com/aws/en/sql/language-manual/functions/event_log)
and is owner-scoped. An empty result under another identity is not proof that
expectations did not run.

## Failure diagnosis and recovery

| Failure stage/category | Interpretation | Safe recovery |
| --- | --- | --- |
| `DISCOVERY` / `SOURCE_UNAVAILABLE` | Provider listing could not be read | Leave manifests unchanged; verify provider availability, then rerun the same notebook |
| `DISCOVERY_CONFIRMATION` / `INVENTORY_SAFETY` | Removal inventories disagree or exceed the guardrail | Do not override automatically; compare both inventories and obtain operator review before any explicit mass-removal override |
| `DOWNLOAD_AND_VALIDATE` / `FILE_VALIDATION` | A staged object or response failed its contract | Staging is cleaned and no manifest transition publishes; fix the source/contract cause and rerun |
| `PUBLICATION` | Promotion, verification, or atomic manifest append failed | Prior manifest truth remains valid; rerun. Immutable objects already promoted are verified and reused |
| `RECONCILIATION` | Post-commit inventory or digest check failed | Stop downstream refresh, inspect the named manifest run, and rerun landing after correcting the mismatch |
| Pipeline expectation failure | Candidate data violated a fail-fast rule | Prior materialized result remains the recovery point; inspect the named expectation and upstream run, correct it, rerun from the failed layer |
| Bundle validation/deployment failure | Configuration or workspace capability mismatch | Do not apply ad hoc UI drift; restore the last reviewed commit/configuration, validate and review `bundle plan`, then deploy again |

Landing notebooks are idempotent and use immutable content-addressed objects.
Rerunning after a transient failure is the preferred recovery. Do not delete
the manifest, raw Volume, or last-good tables. A code rollback means deploying
the last reviewed Git commit, reviewing the plan for deletions, and running the
downstream refresh job. If a downstream task alone failed after an upstream
success, repair/rerun from that failed task only after confirming its input
table is healthy.

## Controlled failure exercise

The BLS notebook has a `controlled_failure` widget that defaults to `false`.
It is never enabled in scheduled configuration. To exercise recovery safely:

1. Record the current manifest transition count and latest successful audit row.
2. Run BLS landing once with `controlled_failure=true`.
3. Confirm the run fails during `PUBLICATION`, staging is cleaned, a sanitized
   `FILE_VALIDATION` audit row has `failed_file_count = 1`, and the manifest
   transition count and active inventory did not change.
4. Reset the widget to `false` and rerun.
5. Confirm a new `SUCCEEDED` row, zero failed files, reconciled active files,
   and unchanged last-good data. Never leave the widget enabled.

This failure is injected in the promoter callback before any promotion or
manifest publication. The existing `finally` cleanup path still runs.

## Alerts and ownership

The repository does not embed recipient addresses or webhook credentials.
For a maintained workspace, the platform owner should create Databricks SQL
alerts over the health query after confirming SQL-alert availability, choose
`TRIGGERED` for `WARN`/`FAIL`, enable recovery notifications, and store
destinations only in workspace settings. Databricks documents scheduled query
evaluation and alert history in
[Databricks SQL alerts](https://docs.databricks.com/aws/en/sql/user/alerts/).
Job failure notifications are the fallback where SQL alerts are unavailable.

| Owner | Responsibility |
| --- | --- |
| Data product operator | Run authorized landings; review removals; inspect health; recover transient failures |
| Pipeline owner | Maintain expectations, investigate failed/dropped rows, and protect last-good outputs |
| Workspace/platform admin | Own notification destinations, job/pipeline permissions, and system-table access |
| Read-only analyst | Consume only the three governed Gold contracts; report anomalies without changing operational state |

Escalate immediately for repeated source failures, any unexplained removal,
contract-count mismatch, authorization regression, or a recovery that would
require deleting or overwriting last-good state.
