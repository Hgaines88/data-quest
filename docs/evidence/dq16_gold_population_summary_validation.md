# DQ-16 Gold population summary live validation

## Result

After pulling reviewed branch head `c0da369`, the `data-quest-gold` triggered
pipeline completed successfully in Databricks on October 19, 2026 at 12:41 PM
EDT with zero displayed errors or warnings. The pipeline read the published
`silver_population` materialized view, evaluated the six-year candidate gate,
and published one row to `gold_population_summary_2013_2018`.

The tracked Spark SQL alternative then ran independently from
`sql/alternatives/question_1_population_summary.sql` at 12:57 PM EDT. It read
six source rows and returned the same one-row summary:

| Field | PySpark Gold output | Spark SQL output |
|---|---:|---:|
| `start_year` | 2013 | 2013 |
| `end_year` | 2018 | 2018 |
| `year_count` | 6 | 6 |
| `mean_population` | 322069808 | 322069808 |
| `population_stddev` | 3796119.9369343743 | 3796119.936934375 |
| `stddev_semantics` | `population` | `population` |

The standard-deviation difference is approximately `7e-10`, far below the
manually applied comparison tolerance of `1e-6`. The committed structural tests
verify the two implementations' filters, completeness conditions, output
contract, and `stddev_pop` semantics; they do not execute this live numeric
comparison. An independent calculation from the six annual
values also produced a mean of `322069808.0` and a population standard
deviation of approximately `3796119.936934378`.

The commit association is operator-recorded because the Databricks result
screens do not display a Git SHA. The editor displayed the
`codex/dq-16-population-summary` branch, and the operator pulled the branch
before creating and running the Gold pipeline.

## Evidence

- [Gold table results](../screenshots/dq16_gold_tables.png) show the candidate
  expectation definition, the successful published materialized view, one
  output record, and zero displayed errors or warnings.
- [Gold expectation result](../screenshots/dq16_gold_expectation_passed.png)
  shows the candidate's fail-fast expectation evaluated with action `FAIL`, a
  `0%` failure rate, and zero failed records.
- [Gold performance](../screenshots/dq16_gold_performance.png) shows the
  successful materialized-view refresh and zero displayed errors or warnings.
- [Gold dependency graph](../screenshots/dq16_gold_pipeline_graph.png) shows
  `silver_population` feeding the candidate gate and the published materialized
  view.
- [Gold result bounds](../screenshots/dq16_gold_result_bounds.png) shows the
  start and end years, year count, mean, and standard deviation.
- [Gold result semantics](../screenshots/dq16_gold_result_semantics.png) shows
  the complementary right side of the same row, including
  `stddev_semantics = population`.
- [SQL result bounds](../screenshots/dq16_sql_result_bounds.png) shows the
  successful tracked SQL-file execution and the left side of its one-row
  result.
- [SQL result semantics](../screenshots/dq16_sql_result_semantics.png) shows
  the complementary right side of the SQL result.
- [SQL performance](../screenshots/dq16_sql_performance.png) shows one completed
  task and six source rows read.

The committed screenshot SHA-256 digests are:

| Screenshot | SHA-256 |
|---|---|
| `dq16_gold_tables.png` | `e21bba50a628ded1ecc0a603e3a9f8bf7a9f57210e44c477a86a23f01ca543ac` |
| `dq16_gold_expectation_passed.png` | `0bdcc3cde83e6e189c08ee429b68995abb6a4a41fde9b64daa29a1128c1a3c42` |
| `dq16_gold_performance.png` | `1a2bd3781eea5099d79450bf60ed1b197f17b540882c15864b9ee66c3c997318` |
| `dq16_gold_pipeline_graph.png` | `93c05b71bd1a06211d2d9a6157a5a9387906566157cd078f73b70c074111c259` |
| `dq16_gold_result_bounds.png` | `717567075f543bf8fd791d6762f9bc5e296044310fd9c38c1cdf9c9a67608b7e` |
| `dq16_gold_result_semantics.png` | `3253c404240ecaea9adc0f7e497eab1ca557a2137f75629247279ae2386c05ba` |
| `dq16_sql_result_bounds.png` | `171eba72d0f3e580ac044c08dd8b0083650757b06bc960f07b28a5290d646fee` |
| `dq16_sql_result_semantics.png` | `d34e2c9de66e2d3fa23c9c7804a8c6ab5b0604827693e348b954a28eb5eb653b` |
| `dq16_sql_performance.png` | `014c89ee1a737915c2791251cfa39ec99f0db92a3d864b240d2de41b10bfcffe` |

## Quality interpretation

The candidate expectation requires six rows, six distinct years, and observed
bounds of 2013 and 2018 after filtering to that inclusive range. Because
`silver_population` already enforces one row per `nation_id + year`, successful
publication establishes one normalized United States row for each requested
year rather than merely a plausible aggregate. The captured expectation panel
directly confirms that the fail-fast rule evaluated with zero failed records;
this is distinct from the table overview, which shows only that one expectation
is defined.

The primary PySpark implementation and independent Spark SQL implementation
agree exactly on the discrete fields, mean, and semantic label and agree on
standard deviation within the declared numeric tolerance. The direct six-row
read count and independent calculation provide separate checks on completeness
and arithmetic.

This evidence proves the DQ-16 result for the validated Databricks snapshot. It
does not establish scheduling, incremental processing, dashboard behavior,
Genie behavior, or results for later provider revisions.
