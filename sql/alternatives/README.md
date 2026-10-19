# Spark SQL Alternatives

Each analytical question requires both Spark SQL and PySpark implementations. Spark SQL versions that do not serve as the primary Gold-table implementation will live here and will be validated against their PySpark counterparts.

`question_1_population_summary.sql` is the runnable Spark SQL alternative for
`gold_population_summary_2013_2018`. It returns the same six contract fields and
returns no result row unless the Silver input contains exactly one normalized
US row for every year from 2013 through 2018. Live validation will compare its
schema, count, key, null behavior, and values with the primary PySpark output.

`question_2_bls_best_year.sql` is the runnable Spark SQL alternative for
`gold_bls_best_year_by_series`. It sums only `Q01` through `Q04`, ranks annual
sums descending with year ascending as the deterministic tie-breaker, and
starts from the Silver series inventory so a series without quarterly history
remains visible with `has_quarterly_observations = false`. Live validation will
compare its schema, row count, series keys, null behavior, and values with the
primary PySpark output and independently spot-check a selected annual sum.

