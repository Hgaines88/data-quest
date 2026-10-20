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

The validation identity's email is deliberately omitted. The operator confirmed
that it did not own the governed objects and belonged to the analyst group.

## Effective data grants

The owner/admin inspection returned exactly five effective grants for the
analyst group:

| Object type | Object | Privilege |
| --- | --- | --- |
| Catalog | `workspace` | `USE_CATALOG` |
| Schema | `workspace.rearc_data_quest` | `USE_SCHEMA` |
| Table | `gold_bls_best_year_by_series` | `SELECT` |
| Table | `gold_bls_q01_population` | `SELECT` |
| Table | `gold_population_summary_2013_2018` | `SELECT` |

No schema-wide `SELECT`, lower-layer `SELECT`, Volume access, object-creation
privilege, ownership, or management privilege appeared in the inspection.

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
result establishes the required read-only stakeholder boundary for the
deployed view-backed Gold contracts.

## Privacy-safe screenshots

| Screenshot | Evidence | SHA-256 |
| --- | --- | --- |
| `docs/screenshots/dq26_analyst_dashboard_overview.png` | Individual-permission dashboard with all filters reset, KPI cards, coverage, and best-year data | `b1cd430590e8a68868dc53c234540df6c45e2983a7cbcb705c043793ea87c6c5` |
| `docs/screenshots/dq26_analyst_dashboard_detail.png` | Paginated best-year data and Q01 nullable population context | `f8d0c9934699b3a1f614ca5a1428f77179984f1788cf27e96d02b11b36c9a3bc` |
| `docs/screenshots/dq26_effective_grants.png` | Admin audit showing exactly the catalog, schema, and three Gold `SELECT` grants | `3336d823178effb2eab126349353cfdf51899299360ebb814c438890f9f8b254` |

The dashboard captures exclude browser chrome, workspace URLs, account
identifiers, and credentials. The grant capture is cropped to the Databricks
query/result surface and contains no email or token. Negative-result details
are operator-recorded outcomes from the separate analyst session; their source
captures were reviewed during validation but are not retained in the repository.
