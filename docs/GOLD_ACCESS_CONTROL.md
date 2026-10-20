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

If the catalog or schema differs from the verified defaults, replace every
`workspace.rearc_data_quest` reference in the security SQL consistently.

## Apply the access model

1. As an account or workspace administrator, create the account group
   `data_quest_readonly_analysts` in **Settings > Identity and access > Groups**
   and assign it to the workspace with ordinary workspace-user entitlement.
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
   separately. Every statement must fail with an authorization error:
   - a write to an allowed Gold table;
   - a read from a Bronze table;
   - a read from a Silver table;
   - a read from the raw Volume; and
   - creation of a table in the project schema.
4. As the owner/admin, run the statements in
   [`inspect_gold_readonly_access.sql`](../sql/security/inspect_gold_readonly_access.sql)
   and confirm the group has only the intended catalog, schema, and three table
   grants. Also inspect group membership to rule out inherited elevated roles.

SQL authorization failures are the expected negative-test result. Do not make
the negative script executable as one batch because execution normally stops
at the first denied statement.

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
the published credential mode are distinct controls. Repository tests can
verify that the intended policy is narrow, but only a separate live principal
can prove effective allowed and denied behavior. DQ-26 remains incomplete
until that live identity test and privacy-safe evidence are recorded.

