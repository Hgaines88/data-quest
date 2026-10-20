# DQ-26 Gold-layer access control

## Persona and boundary

The `data_quest_readonly_analysts` group represents an interactive analyst who
can use the published stakeholder dashboard and independently query its three
governed Gold contracts. The persona does not operate ingestion, pipelines,
quality jobs, schemas, tables, Volumes, or access policy.

The group is intentionally separate from `admins`, pipeline identities, and
object owners. Do not use the project operator as the denial-test identity:
ownership and administrator privileges would make a negative result
meaningless.

## Required objects and permissions

| Object | Required permission | Reason |
| --- | --- | --- |
| `workspace` catalog | `USE CATALOG` | Parent traversal required by Unity Catalog |
| `workspace.rearc_data_quest` schema | `USE SCHEMA` | Parent traversal required by Unity Catalog |
| `gold_population_summary_2013_2018` | `SELECT` | Population KPI and coverage dataset |
| `gold_bls_best_year_by_series` | `SELECT` | Best-year and quarterly-availability dataset |
| `gold_bls_q01_population` | `SELECT` | Q01 population-context dataset |
| Serverless Starter Warehouse | `CAN USE` | Run read-only SQL and individual-permission dashboard queries |
| US Productivity Insight Workspace | `CAN VIEW` | Use the published stakeholder experience |

The data grants are object-specific. Do not grant `SELECT` on the schema or
catalog: that would expose Bronze, Silver, manifests, quality helpers, future
tables, and implementation details. Do not grant ownership, `MANAGE`,
`MODIFY`, fine-grained DML privileges, object-creation privileges, or Volume
access.

If the catalog or schema differs from the verified defaults, retarget all three
reference forms in the security SQL: the standalone `workspace` catalog, every
dotted `workspace.rearc_data_quest` object reference, and the slash-delimited
`/Volumes/workspace/rearc_data_quest/` path. Also replace the standalone filter
literals used by the inspection queries: `catalog_name = 'workspace'`, each
`*_catalog = 'workspace'`, `schema_name = 'rearc_data_quest'`, and each
`*_schema = 'rearc_data_quest'`. A partial replacement can audit or grant one
environment while probing another.

## Apply the access model

1. As an account or workspace administrator, create the account group
   `data_quest_readonly_analysts` in **Settings > Identity and access > Groups**
   and assign it to the workspace with **Databricks SQL access** enabled.
   Leave **Consumer access**, **Workspace access**, and **Admin access**
   disabled. Verify the effective entitlements after the group propagates; the
   warehouse **Can use** ACL does not itself provide Databricks SQL access.
2. Add a dedicated non-admin validation user or service principal. The
   identity must not own project objects and must not inherit broader access
   from another group.
3. As the catalog/schema owner or a principal with `MANAGE`, run
   [`sql/security/apply_gold_readonly_access.sql`](../sql/security/apply_gold_readonly_access.sql).
4. On **SQL Warehouses**, grant the group **Can use** on the Serverless Starter
   Warehouse. Do not grant **Can monitor** or **Can manage**.
5. On the published dashboard, grant the group **Can view**. Do not grant
   **Can edit** or **Can manage**.
6. Publish the dashboard with **Individual data permission** for the analyst
   validation. Shared data permission uses the publisher's data and compute
   authority and therefore cannot prove that the analyst's Unity Catalog
   grants are sufficient.

The checked-in SQL deliberately does not create identities, add members, or
alter workspace-object ACLs. Those are administrative actions whose targets
must be reviewed in the live account.

## Validate with the dedicated analyst

Sign in or authenticate as the non-admin group member. Capture the identity and
results without exposing email addresses, tokens, workspace URLs, or other
credentials.

1. Run each statement in
   [`analyst_positive_checks.sql`](../sql/security/analyst_positive_checks.sql).
   All three exact Gold reads must succeed.
2. Open the published dashboard and exercise at least the Series and
   Observation year filters. The visualizations must render using individual
   data permission.
3. Run each statement in
   [`analyst_negative_checks.sql`](../sql/security/analyst_negative_checks.sql)
   separately. The attempted write to the deployed Gold view must fail because
   a view is not an updateable table; this establishes non-writability but is
   not evidence of an authorization denial. The remaining statements must fail
   with authorization errors:
   - a read from a Bronze table;
   - a read from a Silver table;
   - a read from the raw Volume; and
   - creation of a table in the project schema.
4. As a verified **metastore administrator**, run the statements in
   [`inspect_gold_readonly_access.sql`](../sql/security/inspect_gold_readonly_access.sql)
   and confirm the group has only the intended catalog, schema, and three table
   grants across the complete project schema. Repeat the consolidated inventory
   for every effective group inherited by the validation identity, including
   the workspace `users` group, and confirm the new validation identity has no
   direct grants. A principal with only `MANAGE` is insufficient for this
   consolidated audit because Databricks INFORMATION_SCHEMA privilege views can
   hide other principals' grants. If metastore-admin visibility is unavailable,
   enumerate every project object and execute `SHOW GRANTS` on each one.
5. Run the ownership inventory in the same script. Confirm that neither the
   validation identity nor any effective group owns the catalog, project
   schema, any project table/view, Volume, or routine. Also inspect group
   membership to rule out other inherited elevated roles.
6. Independently inspect workspace ACLs for every project Lakeflow pipeline and
   job under **Jobs & Pipelines > object > Share** (or the equivalent permissions
   API). Confirm that the validation identity and every effective group have no
   pipeline `CAN RUN`, `CAN MANAGE`, or ownership permission and no job
   `CAN MANAGE RUN`, `CAN MANAGE`, or ownership permission. Record each object
   checked; Unity Catalog SQL does not inspect these ACLs.

The absence of mutation and refresh authority must be established by a complete
grant inventory; ownership by the separate owner inventory; and pipeline/job
authority by the separate workspace-ACL inventory. None is established by the
unsupported Gold-view `UPDATE`. Do not make the negative script executable as
one batch because execution
normally stops at the first failed statement. Record the structural Gold-view
failure separately from the four authorization denials.

## Revocation and recovery

To remove access, first remove **Can view** from the dashboard and **Can use**
from the warehouse, then run
[`revoke_gold_readonly_access.sql`](../sql/security/revoke_gold_readonly_access.sql).
Removing the group from the workspace is not a substitute for revocation:
Databricks retains its object permissions if the group is assigned again.

If allowed reads fail, inspect parent `USE` privileges, exact table `SELECT`,
warehouse **Can use**, dashboard **Can view**, and dashboard publication mode.
Do not resolve a failure by granting schema-wide access or elevating the analyst
to administrator.

## Platform and evidence boundary

Unity Catalog privileges, warehouse ACLs, dashboard ACLs, group membership, and
the published credential mode are distinct controls. Repository tests verify
that the intended policy is narrow. The 2026-10-19 live validation used a
separate non-admin principal and is recorded in
[`docs/evidence/dq26_gold_access_control_validation.md`](evidence/dq26_gold_access_control_validation.md).

