# DQ-25 stakeholder exploration live validation

## Scope and environment

- Validation date: 2026-10-19
- Platform: Databricks Free Edition AI/BI dashboards
- Dashboard: **US Productivity Insight Workspace**
- Page: **Executive overview**
- Published query compute: Serverless Starter Warehouse
- Published permission mode: shared data permission using the publisher's
  credentials
- Dataset materialization: disabled
- Viewer notification: disabled

The live dashboard reads only the three governed Gold-backed SQL datasets:
`population_summary`, `bls_best_year_by_series`, and
`q01_population_context`.

## Published dashboard evidence

The published dashboard rendered the following stakeholder surface:

- filters for series, best year, observation year, and quarterly availability;
- mean population KPI `322.07m`;
- population standard deviation KPI `3.8m`;
- a one-row coverage summary showing 2013 through 2018, six years, and
  population standard-deviation semantics;
- a paginated best-year table that preserves series inventory and quarterly
  observation status;
- a paginated Q01 table that preserves nullable population context;
- the visible boundary that BLS Q01 and population have different units and
  that proximity or co-movement is not evidence of causation; and
- the visible source note stating that freshness is operator-verified and
  automated monitoring is not yet enabled.

The first published revision returned `No warehouse selected to run query`.
The operator explicitly selected and started the Serverless Starter Warehouse,
successfully reran `population_summary`, and republished. All published widgets
then rendered. This establishes recovery for the observed configuration error;
it does not establish scheduled refresh or automated freshness monitoring.

## Acceptance-query reconciliation

`sql/stakeholder/validate_stakeholder_values.sql` returned exactly four rows,
all with `passed = true`:

| Check | Actual | Expected | Passed |
| --- | --- | --- | --- |
| `bls_series_spot_check` | `1994,14.600000,4,true` | `1994,14.600000,4,true` | `true` |
| `population_summary_bounds` | `2013,2018,6,population` | `2013,2018,6,population` | `true` |
| `population_summary_values` | `3.22069808E8,3796119.9369343743` | `322069808,3796119.9369343743` | `true` |
| `q01_population_context_spot_checks` | `0` | `0` | `true` |

The scientific-notation rendering of the first population actual value is
numerically equal to the integer expected value.

## Published interaction and null preservation

In published mode, filtering observation year to `2026` returned the governed
row for `PRS30006032` with `q01_value = 0.00`, `population = null`, and
`population_match_found = false`. The operator then reset the filter to its
default. An earlier published/draft interaction test for quarterly availability
`false` preserved null best-year fields, zero quarterly observations, and the
false availability flag.

## Genie reconciliation and limitation

Two representative answers were checked against the visible Gold-backed data:

1. For `PRS30006032`, Genie reported best year `1994`, annual available-quarter
   sum `14.6`, and four supporting quarterly observations. These values match
   the acceptance query. The widget-scoped authoring assistant initially
   changed the table filter while answering; the operator undid that mutation
   and restored the multi-series table.
2. A read-only dataset question returned average population `322,069,808`
   people and population standard deviation `3,796,120` people, explicitly
   identifying population (`N`) rather than sample (`N-1`) semantics. The
   displayed rounded KPI values reconcile to those exact results.

The observed Free Edition interface did not expose a verified custom Genie
instruction editor. This evidence therefore supports reconciled generated
answers, not deployment of the proposed custom instruction set.

## Privacy-safe screenshots

| Screenshot | Evidence | SHA-256 |
| --- | --- | --- |
| `docs/screenshots/dq25_published_dashboard_overview.png` | Published title, default filters, KPI cards, non-causality boundary, coverage summary, and best-year table | `dbf347c68541e623b6e622b9b7392ea06f85bf904c8e1afbc8ca387881f8fe6e` |
| `docs/screenshots/dq25_published_dashboard_detail.png` | Published best-year pagination, Q01 nullable-context table, and full source note | `a012d6d98bb8777b430368146abf11721dcca7a0dfe60e367ba7b3684525e72b` |
| `docs/screenshots/dq25_published_2026_null_filter.png` | Published `2026` filter and null-preservation result | `52951062f8a98207da972890722754fd0eb0b4eafb1009e4811b196308e59ddb` |
| `docs/screenshots/dq25_validation_results_left.png` | Four named validation checks, actual and expected values, and four true pass flags | `73c7f8d491de59b818a58d29373ecbe2cb36bdcd858eef3a9068962cfef95512` |
| `docs/screenshots/dq25_validation_results_right.png` | Expected values, four true pass flags, and interpretations | `02aca944ae7836d289770fdda7ba47206d2670ce8759efa25686d9ff9a033759` |

The captures exclude browser chrome, workspace URLs, account identifiers, and
credentials. The published dashboard remains workspace state; no schedule or
custom dashboard serialization is claimed by this record.
