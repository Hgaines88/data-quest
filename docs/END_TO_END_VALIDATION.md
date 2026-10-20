# DQ-28 end-to-end validation

This runbook validates the extended Databricks product as one connected system
without implying that Databricks Free Edition or the Asset Bundle manages
resources that remain external to bundle state.

## Validation boundary

The bundle manages the three triggered pipelines and their ordered
Bronze-to-Gold refresh job. Landing remains a single-writer manual prerequisite.
The published dashboard, warehouse, analyst identity, Unity Catalog grants,
and notification destinations remain externally governed. The bundle's
isolated development outputs and the shared, manually managed stakeholder
surface are therefore validated as two explicit paths over the same governed
source contracts; they are not presented as one bundle-owned deployment.

Do not run two landing notebooks concurrently. Keep `allow_mass_removal=false`
and `controlled_failure=false` throughout this validation.

## 1. Record the exact revision and local baseline

From the repository root:

```bash
git rev-parse HEAD
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src pipelines notebooks tests
git diff --check
```

Record the revision and summarized results in
`docs/evidence/dq28_end_to_end_validation.md`. Local checks do not replace live
Databricks evidence.

## 2. Confirm starting health

As the project owner, run `sql/operations/inspect_health.sql` and
`sql/operations/inspect_pipeline_expectations.sql`. Record:

- the latest BLS and Data USA terminal audit rows;
- the latest completed Gold update;
- the exact Gold contract counts;
- the latest Bronze, Silver, and Gold expectation results; and
- any `WARN`, `FAIL`, null metric, or count mismatch that requires explanation.

Stop if the starting state is not healthy. Do not use a later successful run to
hide an unexplained earlier failure.

## 3. Rerun landing safely

From the repository's Databricks Git folder, run the BLS notebook and then the
Data USA notebook. Run them serially with the documented defaults. On unchanged
provider content, expect no new promotion or manifest transition. If upstream
content changed, record the new or changed counts and reconcile every active
manifest entry to an immutable Volume object before continuing.

Follow the source-specific procedures in `docs/BLS_LANDING_RUNBOOK.md` and
`docs/DATAUSA_LANDING_RUNBOOK.md`. The controlled-failure exercise belongs to
DQ-27 evidence and is not repeated during this final healthy-path validation.

## 4. Validate and run the supported bundle resources

Follow `docs/BUNDLE_DEPLOYMENT.md` against the isolated `dev` target:

```bash
databricks bundle validate --target dev
databricks bundle plan --target dev
databricks bundle deploy --target dev
databricks bundle run --target dev refresh
databricks bundle plan --target dev
```

Before deployment, stop if the plan deletes a resource, changes an unexpected
resource, or targets a shared output schema. After the run, require all three
ordered tasks to succeed and the final plan to converge with no pending change.
Do not deploy the `prod` target for this assessment validation.

## 5. Reconcile both output paths

For the isolated development output schema, make copies of these read-only
queries without committing the generated files:

1. `sql/quality/validate_bronze_to_silver.sql`;
2. `sql/quality/validate_gold_cross_implementation.sql`;
3. `sql/operations/inspect_health.sql`; and
4. `sql/operations/inspect_pipeline_expectations.sql`.

In each copy, replace pipeline-output references to
`workspace.rearc_data_quest` with the exact per-user `output_schema` shown by
the reviewed bundle plan. In the Gold reconciliation copy, also keep the
metadata lookup aligned: use `<catalog>.information_schema.columns` and change
every `table_schema = 'rearc_data_quest'` predicate to the exact development
schema name. In the health copy, leave `ingestion_run_audit` pointed at the
shared source schema because landing is not deployed by the bundle. Run all
four copies, require every reconciliation pass flag to be true, and use the
expectations copy to record the Bronze, Silver, and Gold update IDs produced by
this bundle run. Require Gold row counts of 1, 282, and 39 with zero invalid
rows.

Next, update the separately governed shared stakeholder path. From the same
reviewed Git revision, run the existing shared Bronze, Silver, and Gold
pipelines in that order. Do not deploy the bundle's `prod` target. Record the
three successful shared update IDs and verify that
`sql/operations/inspect_pipeline_expectations.sql` reports those exact IDs for
the corresponding layers. The other queries below validate the resulting data
and stakeholder surface; they do not report pipeline update IDs:

1. run `sql/quality/validate_bronze_to_silver.sql`;
2. run `sql/quality/validate_gold_cross_implementation.sql`;
3. run `sql/stakeholder/validate_stakeholder_values.sql`;
4. run `sql/operations/inspect_health.sql`;
5. run `sql/operations/inspect_pipeline_expectations.sql`;
6. refresh the published dashboard and verify its three Gold-backed datasets;
7. ask the two representative Genie questions recorded in
   `docs/evidence/dq25_stakeholder_exploration_validation.md`; and
8. reconcile the displayed answers to the query results.

Every machine-readable pass flag must be true. Preserve null population context
and unavailable BLS history rather than replacing either with zero.

## 6. Reconfirm the access boundary

Use the separate non-admin analyst identity and the exact positive and negative
checks in `sql/security/`. Require all three Gold reads and the published
dashboard to work. Require Bronze, Silver, raw Volume, and schema-creation
operations to remain unavailable. Keep the structural Gold-view write block
separate from authorization-denial claims.

Do not commit identity names, email addresses, workspace URLs, or uncropped
authorization screenshots.

## 7. Confirm final health and operational limits

Rerun both operational SQL files against the shared schema and rerun the
development-schema copies defined in step 5. Confirm fresh successful source
audit rows in the shared source schema. For both output schemas, match the
Bronze, Silver, and Gold update IDs reported by
`inspect_pipeline_expectations.sql` to this validation, confirm the completed
Gold update and exact Gold counts, require visible expectation results, and
resolve every failure signal. Review the runtime, serverless
compute choices, single-writer landing boundary, isolated development schema,
cleanup procedure, and likely cost drivers in `docs/BUNDLE_DEPLOYMENT.md` and
`docs/OPERATIONAL_OBSERVABILITY.md`.

Free Edition does not establish a production SLA, production schedule,
production alert destination, or bundle ownership of the dashboard, warehouse,
identity, or grants. Retain those limitations in the final evidence.

## 8. Close the evidence loop

Update the DQ-28 evidence record with the exact revision, date, environment,
commands or notebook actions, counts, observed failures and recoveries, and
privacy-safe screenshots. Then run the repository link, secret, privacy, and
explainability review required by `docs/QUALITY_ASSURANCE_PROTOCOL.md`.

DQ-28 is not complete until the live gates above are recorded for the exact
reviewed revision.
