# DQ-18 Gold BLS Q01 population-context validation

## Deployment identity

- Git revision: `57073141c8faa35de2b90a1346162f10ee479c69`
- Branch: `codex/dq-18-q01-population`
- Pipeline: `data-quest-gold`
- Pipeline identifier omitted from the submission
- Validated on: October 19, 2026

The operator switched the Databricks Git folder directly to the reviewed DQ-18
branch and pulled the revision before running the pipeline. The screenshots
establish the displayed branch context and live results; they do not
independently prove the remote Git commit identity.

## Primary PySpark result

The triggered Gold update completed at 3:33 PM EDT with zero displayed errors
or warnings. The new `gold_bls_q01_population` materialized view completed a
full recompute in 8 seconds and published 39 rows. The existing Question 1 and
Question 2 Gold outputs remained green with `No change`.

The published result contains one row for each available `Q01` observation of
`PRS30006032`, ordered from 1988 through 2026. Its six-column contract is:

| Column | Type |
| --- | --- |
| `series_id` | string |
| `series_label` | string |
| `year` | integer |
| `q01_value` | decimal(20,6) |
| `population` | long |
| `population_match_found` | boolean |

The provider-grounded label is `Manufacturing | All workers | Hours worked | %
Change from previous quarter | Seasonal Adjusted`. The BLS history is the left
side of the join. Years without a population row remain visible with null
`population` and `population_match_found = false`; matched years contain the
population and set the flag to true. The inspected result includes both outer
missing years and the internal missing year 2020, proving that the output does
not infer coverage from year bounds.

## Fail-fast expectations

Both input-validation expectations used the `FAIL` action and recorded zero
percent failures and zero failed records:

- the selected Q01 history is nonempty and has one row per distinct year;
- the selected series resolves to exactly one metadata row.

Both candidate expectations also used the `FAIL` action and recorded zero
percent failures and zero failed records:

- the joined result retains exactly one row per BLS year;
- the nullable population and visible match indicator remain consistent.

## Spark SQL and PySpark parity

The excluded, reviewer-visible
`sql/alternatives/question_3_bls_q01_population.sql` query completed
successfully at 3:42 PM EDT and returned 39 ordered rows. A separate read-only,
null-safe full-outer comparison returned:

| Check | Spark SQL | PySpark |
| --- | ---: | ---: |
| Rows | 39 | 39 |
| Distinct `series_id + year` keys | 39 | 39 |
| Rows without a population match | 28 | 28 |

The comparison reported zero mismatches across the series label, Q01 value,
nullable population, and population-match indicator.

## Independent source-level spot check

A separate read-only query joined the governed Silver observation and
population tables directly, then compared five representative years with the
Gold output:

| Year | Source Q01 value | Source population | Expected match state |
| --- | ---: | ---: | --- |
| 2012 | 2.500000 | null | false |
| 2013 | 0.500000 | 316128839 | true |
| 2020 | -7.000000 | null | false |
| 2024 | -0.700000 | 340110990 | true |
| 2026 | 0.000000 | null | false |

For all five rows, the source-to-Gold Q01 comparison, nullable population
comparison, and match-indicator comparison returned true. This independently
checks the coverage boundary, an internal population gap, a later match, and a
post-coverage BLS year.

## Evidence files

| Screenshot | SHA-256 |
| --- | --- |
| `dq18_gold_run_completed.png` | `15a0e912187e924b692457d9b41675fb1c03f8c58fe8f58917fbee83cbc21903` |
| `dq18_gold_tables.png` | `e0243bcefe06250f9f4323225f19111fb79c138ffbd7287ab5bc1bf7a5771807` |
| `dq18_gold_result_matches.png` | `297fe6eb689387ce249c3325059ff30599aa068b599421c997b505084191001f` |
| `dq18_gold_columns.png` | `d566166fddf59d300a34f617cd20bf0427322342f9b2619e624e41e8835e9d28` |
| `dq18_candidate_expectations.png` | `e170c6c51cdf752d62fe85b1da21d10e46aa71ccb7623ab894cbfae59ea36e18` |
| `dq18_input_expectations.png` | `fc083cbfabed960787573a246f61bf57fb1b4a36f165870436d292b8cee8d95d` |
| `dq18_sql_result.png` | `e7c4d05db4b9a7c147c502e712e4f8ffc16744f4eae499c7c50283003eb119a0` |
| `dq18_sql_pyspark_parity_counts.png` | `4bda6beb1dcc20726981b8309ec3c53939e5dfe007be4eb6d244ef1b01a0cb2e` |
| `dq18_sql_pyspark_parity_outcome.png` | `f7eef3cafef23b380fd8dbae1f71de87f4e048bd4a33f14fcab6bdfdb487a825` |
| `dq18_independent_spot_check_values.png` | `b660f4383233b1927ab64f1839310fc83d3819edab04d23f4ba2ce6ffbbe4d7b` |
| `dq18_independent_spot_check_matches.png` | `6287b7dfe6bfe9ce8337cefc3469c4d48d9f2ac22b87bd478a60343f5dbd0c04` |

## Scope boundary

This evidence validates Question 3's governed Gold contract for the reviewed
snapshot. Population is contextual evidence only. Neither the table nor this
validation claims that population caused changes in the BLS series. Broader
cross-question validation remains DQ-19, and dashboard or Genie presentation
remains downstream work.
