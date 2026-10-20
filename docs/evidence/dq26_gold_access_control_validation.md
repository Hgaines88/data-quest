# DQ-26 Gold access-control live validation

## Scope and identity boundary

- Validation date: 2026-10-19
- Platform: Databricks Free Edition with Unity Catalog
- Analyst group: `data_quest_readonly_analysts`
- Validation identity: separate non-admin user controlled by the operator
- Analyst entitlements: Databricks SQL access enabled; Consumer access,
  Workspace access, and Admin access disabled
- Warehouse ACL: **Can use** on Serverless Starter Warehouse
- Dashboard ACL: **Can view** on **US Productivity Insight Workspace**
- Published dashboard permission mode: individual data permission

The validation identity's email is deliberately omitted. On 2026-10-20, the
operator inspected the identity's complete workspace **Groups** field. It
listed exactly `data_quest_readonly_analysts` and the system `users` group;
there were no other direct or inherited workspace group memberships. The
operator also confirmed that the identity did not own the governed objects.

## Effective data grants

The owner/admin inspection returned exactly five direct grants for the analyst
group:

| Object type | Object | Privilege |
| --- | --- | --- |
| Catalog | `workspace` | `USE_CATALOG` |
| Schema | `workspace.rearc_data_quest` | `USE_SCHEMA` |
| Table | `gold_bls_best_year_by_series` | `SELECT` |
| Table | `gold_bls_q01_population` | `SELECT` |
| Table | `gold_population_summary_2013_2018` | `SELECT` |

No schema-wide `SELECT`, lower-layer `SELECT`, Volume access, object-creation,
or management privilege appeared in that direct-group grant inspection.
Ownership is recorded separately in object metadata and was not established by
this result. The separate analyst's successful and denied operations establish
the observed effective behavior for the tested objects. Post-review audits of
the workspace `users` group and the validation identity itself each returned
zero rows across catalog, project-schema, table/view, Volume, and routine
privileges. Because the complete membership inspection identified no group
beyond `data_quest_readonly_analysts` and `users`, these queries cover every
group effective for the validation identity. The identity therefore receives
the five required data privileges through the analyst group without additional
direct or inherited-group grants in the audited scope.

On 2026-10-20, the metastore-administrator ownership inventory returned 44
project-scope objects. Filtering the `owner` column separately for
`data_quest_readonly_analysts`, `users`, and the validation identity returned
zero rows for each principal. Because the membership inspection established
the complete effective-group set, the validation identity and every effective
group therefore own none of the audited catalog, schema, table/view, Volume,
or routine objects.

The workspace ACL inventory found three project workloads and no separate
jobs: `data-quest-bronze`, `data-quest-gold`, and `data-quest-silver`. Each
pipeline listed only the operator as owner and the inherited `Admins` group as
**Can manage**. The analyst group, `users`, and validation identity were absent
from all three ACLs. Those principals comprise the identity's complete
direct-and-group authorization set, so the validation identity has no pipeline
run, management, or ownership authority in the inventoried workspace.

## Positive validation

As the separate analyst, all three exact Gold count queries completed
successfully. The Q01 population-context result contained 39 rows. The
published dashboard rendered through individual data permission, including the
`322.07m` mean-population KPI, `3.8m` population-standard-deviation KPI,
coverage row, best-year table, and Q01 nullable-context table. Series and
Observation year filters were exercised successfully and reset to `All`.

## Negative validation

Each statement was run separately as the analyst:

| Probe | Observed result | Interpretation |
| --- | --- | --- |
| `UPDATE` Gold population summary | `EXPECT_TABLE_NOT_VIEW.NO_ALTERNATIVE` | The deployed Gold contract is a view, so it is structurally non-writable. This is not an authorization denial. |
| `SELECT` Bronze observation | `INSUFFICIENT_PERMISSIONS`, missing `SELECT` | Bronze data is not exposed. |
| `SELECT` Silver observation | `INSUFFICIENT_PERMISSIONS`, missing `SELECT` | Silver data is not exposed. |
| `LIST` raw landing Volume | `PERMISSION_DENIED`, missing `READ VOLUME` | Raw provider artifacts are not exposed. |
| `CREATE TABLE` in project schema | `PERMISSION_DENIED`, missing `CREATE TABLE` | The analyst cannot create schema objects. |

The evidence therefore contains four authorization denials plus a distinct
structural Gold-view write block. It does not claim that the Gold write probe
reached an authorization check. Together with the exact-grant inspection, the
result establishes the observed data-access boundary for the tested deployed
view-backed Gold contracts. The five-row inventory establishes only the audited
Unity Catalog grants. The separate 44-object ownership inventory and three-
pipeline workspace-ACL inventory establish the remaining ownership and
Lakeflow authority boundaries described above.

## Privacy-safe screenshots

| Screenshot | Evidence | SHA-256 |
| --- | --- | --- |
| `docs/screenshots/dq26_analyst_dashboard_overview.png` | Individual-permission dashboard with all filters reset, KPI cards, coverage, and best-year data | `b1cd430590e8a68868dc53c234540df6c45e2983a7cbcb705c043793ea87c6c5` |
| `docs/screenshots/dq26_analyst_dashboard_detail.png` | Paginated best-year data and Q01 nullable population context | `f8d0c9934699b3a1f614ca5a1428f77179984f1788cf27e96d02b11b36c9a3bc` |
| `docs/screenshots/dq26_effective_grants.png` | Admin audit showing exactly the catalog, schema, and three Gold `SELECT` grants | `3336d823178effb2eab126349353cfdf51899299360ebb814c438890f9f8b254` |
| `docs/screenshots/dq26_users_group_zero_grants.png` | Complete project-scope inventory for inherited `users` group returning zero rows | `d502552b065f4d9189113c51628f4f7e2140f61d052770eb0e40698fc1ae04ba` |
| `docs/screenshots/dq26_validation_user_zero_direct_grants.png` | Complete project-scope inventory for the validation identity returning zero direct grants, with the email excluded from the crop | `bcff5c4679eb3f4ddcb61871f07905a690282404080112efb522511c87fd83f4` |

The dashboard captures exclude browser chrome, workspace URLs, account
identifiers, and credentials. The grant capture is cropped to the Databricks
query/result surface and contains no email or token. Negative-result details
are operator-recorded outcomes from the separate analyst session; their source
captures were reviewed during validation but are not retained in the repository.
The group-membership, ownership-filter, and pipeline-permission captures were
likewise reviewed but not retained because they expose personal email addresses
and workspace identifiers.
