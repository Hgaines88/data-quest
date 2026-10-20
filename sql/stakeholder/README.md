# Stakeholder exploration SQL

These read-only datasets are the governed semantic surface for DQ-25. Each
query selects explicit fields from one published Gold table at that table's
documented grain. They do not reimplement business logic from Silver or Bronze.

| Dataset file | Gold source | Grain | Intended use |
| --- | --- | --- | --- |
| `population_summary.sql` | `gold_population_summary_2013_2018` | One requested year range | KPI cards and coverage definition |
| `bls_best_year_by_series.sql` | `gold_bls_best_year_by_series` | One row per governed series | Searchable best-year and availability table |
| `q01_population_context.sql` | `gold_bls_q01_population` | One selected series and year | Quarterly-value context with nullable population |

`validate_stakeholder_values.sql` is the machine-readable acceptance query. A
successful run returns four rows and every row has `passed = true`. Its fixed
values are regression anchors from the accepted 2026-10-19 Gold run, not a
substitute for provider-revision investigation.

If the deployment uses another catalog or schema, replace every
`workspace.rearc_data_quest` reference consistently. Do not point dashboard
datasets directly at lower medallion layers.
