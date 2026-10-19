-- DQ-19: repeatable SQL/PySpark reconciliation for all required Gold outputs.
-- Passing condition: every output row has passed = true.
-- Floating-point tolerance applies only to Question 1 DOUBLE aggregates.

WITH
validation_settings AS (
  SELECT CAST(0.000001 AS DOUBLE) AS double_tolerance
),

-- Question 1: independently recompute the SQL alternative from Silver.
q1_sql AS (
  SELECT
    CAST(2013 AS INT) AS start_year,
    CAST(2018 AS INT) AS end_year,
    CAST(COUNT(*) AS INT) AS year_count,
    AVG(CAST(population AS DOUBLE)) AS mean_population,
    STDDEV_POP(CAST(population AS DOUBLE)) AS population_stddev,
    CAST('population' AS STRING) AS stddev_semantics
  FROM workspace.rearc_data_quest.silver_population
  WHERE nation_id = '01000US'
    AND nation = 'United States'
    AND year BETWEEN 2013 AND 2018
  HAVING COUNT(*) = 6
    AND COUNT(DISTINCT year) = 6
    AND MIN(year) = 2013
    AND MAX(year) = 2018
),
q1_pyspark AS (
  SELECT
    start_year,
    end_year,
    year_count,
    mean_population,
    population_stddev,
    stddev_semantics
  FROM workspace.rearc_data_quest.gold_population_summary_2013_2018
),
q1_sql_schema AS (
  SELECT concat_ws(
    ',',
    typeof(start_year),
    typeof(end_year),
    typeof(year_count),
    typeof(mean_population),
    typeof(population_stddev),
    typeof(stddev_semantics)
  ) AS schema_signature
  FROM q1_sql
),
q1_pyspark_schema AS (
  SELECT concat_ws(
    ',',
    typeof(start_year),
    typeof(end_year),
    typeof(year_count),
    typeof(mean_population),
    typeof(population_stddev),
    typeof(stddev_semantics)
  ) AS schema_signature
  FROM q1_pyspark
),
q1_value_mismatches AS (
  SELECT COUNT(*) AS mismatch_count
  FROM q1_sql AS sql_result
  FULL OUTER JOIN q1_pyspark AS pyspark_result
    ON sql_result.start_year = pyspark_result.start_year
    AND sql_result.end_year = pyspark_result.end_year
  CROSS JOIN validation_settings AS settings
  WHERE sql_result.start_year IS NULL
    OR pyspark_result.start_year IS NULL
    OR sql_result.year_count <> pyspark_result.year_count
    OR (
      NOT (sql_result.mean_population <=> pyspark_result.mean_population)
      AND (
        sql_result.mean_population IS NULL
        OR pyspark_result.mean_population IS NULL
        OR ABS(sql_result.mean_population - pyspark_result.mean_population)
          > settings.double_tolerance
      )
    )
    OR (
      NOT (sql_result.population_stddev <=> pyspark_result.population_stddev)
      AND (
        sql_result.population_stddev IS NULL
        OR pyspark_result.population_stddev IS NULL
        OR ABS(sql_result.population_stddev - pyspark_result.population_stddev)
          > settings.double_tolerance
      )
    )
    OR NOT (sql_result.stddev_semantics <=> pyspark_result.stddev_semantics)
),

-- Question 2: independently reproduce the deterministic SQL ranking.
q2_annual_sums AS (
  SELECT
    series_id,
    year,
    SUM(value) AS annual_quarterly_sum,
    CAST(COUNT(*) AS INT) AS quarterly_observation_count
  FROM workspace.rearc_data_quest.silver_bls_observation
  WHERE period_code IN ('Q01', 'Q02', 'Q03', 'Q04')
  GROUP BY series_id, year
),
q2_ranked AS (
  SELECT
    series_id,
    year AS best_year,
    annual_quarterly_sum,
    quarterly_observation_count,
    ROW_NUMBER() OVER (
      PARTITION BY series_id
      ORDER BY annual_quarterly_sum DESC, year ASC
    ) AS result_rank
  FROM q2_annual_sums
),
q2_sql AS (
  SELECT
    series.series_id,
    series.series_label,
    ranked.best_year,
    ranked.annual_quarterly_sum,
    CAST(COALESCE(ranked.quarterly_observation_count, 0) AS INT)
      AS quarterly_observation_count,
    ranked.best_year IS NOT NULL AS has_quarterly_observations
  FROM workspace.rearc_data_quest.silver_bls_series AS series
  LEFT JOIN q2_ranked AS ranked
    ON series.series_id = ranked.series_id
    AND ranked.result_rank = 1
),
q2_pyspark AS (
  SELECT
    series_id,
    series_label,
    best_year,
    annual_quarterly_sum,
    quarterly_observation_count,
    has_quarterly_observations
  FROM workspace.rearc_data_quest.gold_bls_best_year_by_series
),
q2_sql_schema AS (
  SELECT concat_ws(
    ',',
    typeof(series_id),
    typeof(series_label),
    typeof(best_year),
    typeof(annual_quarterly_sum),
    typeof(quarterly_observation_count),
    typeof(has_quarterly_observations)
  ) AS schema_signature
  FROM q2_sql
  LIMIT 1
),
q2_pyspark_schema AS (
  SELECT concat_ws(
    ',',
    typeof(series_id),
    typeof(series_label),
    typeof(best_year),
    typeof(annual_quarterly_sum),
    typeof(quarterly_observation_count),
    typeof(has_quarterly_observations)
  ) AS schema_signature
  FROM q2_pyspark
  LIMIT 1
),
q2_value_mismatches AS (
  SELECT COUNT(*) AS mismatch_count
  FROM q2_sql AS sql_result
  FULL OUTER JOIN q2_pyspark AS pyspark_result
    ON sql_result.series_id = pyspark_result.series_id
  WHERE sql_result.series_id IS NULL
    OR pyspark_result.series_id IS NULL
    OR NOT (sql_result.series_label <=> pyspark_result.series_label)
    OR NOT (sql_result.best_year <=> pyspark_result.best_year)
    OR NOT (
      sql_result.annual_quarterly_sum
        <=> pyspark_result.annual_quarterly_sum
    )
    OR NOT (
      sql_result.quarterly_observation_count
        <=> pyspark_result.quarterly_observation_count
    )
    OR NOT (
      sql_result.has_quarterly_observations
        <=> pyspark_result.has_quarterly_observations
    )
),
q2_expected_best_year AS (
  SELECT
    annual.series_id,
    MIN(annual.year) AS expected_best_year
  FROM q2_annual_sums AS annual
  INNER JOIN (
    SELECT series_id, MAX(annual_quarterly_sum) AS maximum_sum
    FROM q2_annual_sums
    GROUP BY series_id
  ) AS maxima
    ON annual.series_id = maxima.series_id
    AND annual.annual_quarterly_sum = maxima.maximum_sum
  GROUP BY annual.series_id
),
q2_tie_break_violations AS (
  SELECT COUNT(*) AS violation_count
  FROM q2_pyspark AS result
  INNER JOIN q2_expected_best_year AS expected
    ON result.series_id = expected.series_id
  WHERE NOT (result.best_year <=> expected.expected_best_year)
),
q2_spot_check AS (
  SELECT
    result.series_id,
    result.best_year,
    result.annual_quarterly_sum,
    SUM(source.value) AS source_sum,
    COUNT(*) AS source_quarter_count
  FROM q2_pyspark AS result
  INNER JOIN workspace.rearc_data_quest.silver_bls_observation AS source
    ON result.series_id = source.series_id
    AND result.best_year = source.year
    AND source.period_code IN ('Q01', 'Q02', 'Q03', 'Q04')
  WHERE result.series_id = 'PRS30006032'
  GROUP BY result.series_id, result.best_year, result.annual_quarterly_sum
),

-- Question 3: independently reproduce the left population join from Silver.
q3_sql AS (
  SELECT
    observation.series_id,
    series.series_label,
    observation.year,
    observation.value AS q01_value,
    population.population,
    population.population IS NOT NULL AS population_match_found
  FROM workspace.rearc_data_quest.silver_bls_observation AS observation
  INNER JOIN workspace.rearc_data_quest.silver_bls_series AS series
    ON observation.series_id = series.series_id
  LEFT JOIN workspace.rearc_data_quest.silver_population AS population
    ON observation.year = population.year
    AND population.nation_id = '01000US'
    AND population.nation = 'United States'
  WHERE observation.series_id = 'PRS30006032'
    AND observation.period_code = 'Q01'
),
q3_pyspark AS (
  SELECT
    series_id,
    series_label,
    year,
    q01_value,
    population,
    population_match_found
  FROM workspace.rearc_data_quest.gold_bls_q01_population
),
q3_sql_schema AS (
  SELECT concat_ws(
    ',',
    typeof(series_id),
    typeof(series_label),
    typeof(year),
    typeof(q01_value),
    typeof(population),
    typeof(population_match_found)
  ) AS schema_signature
  FROM q3_sql
  LIMIT 1
),
q3_pyspark_schema AS (
  SELECT concat_ws(
    ',',
    typeof(series_id),
    typeof(series_label),
    typeof(year),
    typeof(q01_value),
    typeof(population),
    typeof(population_match_found)
  ) AS schema_signature
  FROM q3_pyspark
  LIMIT 1
),
q3_value_mismatches AS (
  SELECT COUNT(*) AS mismatch_count
  FROM q3_sql AS sql_result
  FULL OUTER JOIN q3_pyspark AS pyspark_result
    ON sql_result.series_id = pyspark_result.series_id
    AND sql_result.year = pyspark_result.year
  WHERE sql_result.series_id IS NULL
    OR pyspark_result.series_id IS NULL
    OR NOT (sql_result.series_label <=> pyspark_result.series_label)
    OR NOT (sql_result.q01_value <=> pyspark_result.q01_value)
    OR NOT (sql_result.population <=> pyspark_result.population)
    OR NOT (
      sql_result.population_match_found
        <=> pyspark_result.population_match_found
    )
),
q3_source_invariants AS (
  SELECT
    COUNT(*) AS source_rows,
    COUNT(DISTINCT year) AS source_years,
    MIN(year) AS source_start_year,
    MAX(year) AS source_end_year
  FROM workspace.rearc_data_quest.silver_bls_observation
  WHERE series_id = 'PRS30006032'
    AND period_code = 'Q01'
),
q3_result_invariants AS (
  SELECT
    COUNT(*) AS result_rows,
    COUNT(DISTINCT year) AS result_years,
    MIN(year) AS result_start_year,
    MAX(year) AS result_end_year,
    COUNT_IF(population_match_found <> (population IS NOT NULL))
      AS inconsistent_match_flags
  FROM q3_pyspark
),
q3_spot_check AS (
  SELECT COUNT(*) AS mismatch_count
  FROM (
    SELECT
      source.year,
      source.value AS source_q01_value,
      population.population AS source_population,
      result.q01_value AS result_q01_value,
      result.population AS result_population,
      result.population_match_found
    FROM workspace.rearc_data_quest.silver_bls_observation AS source
    LEFT JOIN workspace.rearc_data_quest.silver_population AS population
      ON source.year = population.year
      AND population.nation_id = '01000US'
      AND population.nation = 'United States'
    INNER JOIN q3_pyspark AS result
      ON source.series_id = result.series_id
      AND source.year = result.year
    WHERE source.series_id = 'PRS30006032'
      AND source.period_code = 'Q01'
      AND source.year IN (2012, 2013, 2020, 2024, 2026)
  ) AS samples
  WHERE NOT (source_q01_value <=> result_q01_value)
    OR NOT (source_population <=> result_population)
    OR NOT (
      population_match_found <=> (source_population IS NOT NULL)
    )
),

checks AS (
  SELECT
    'question_1' AS question,
    'q1_schema_parity' AS check_name,
    sql_schema.schema_signature AS actual_value,
    pyspark_schema.schema_signature AS expected_value,
    sql_schema.schema_signature = pyspark_schema.schema_signature AS passed,
    'SQL and PySpark expose the same ordered field types.' AS interpretation
  FROM q1_sql_schema AS sql_schema
  CROSS JOIN q1_pyspark_schema AS pyspark_schema

  UNION ALL
  SELECT
    'question_1',
    'q1_row_count_and_key_parity',
    CAST((SELECT COUNT(*) FROM q1_sql) AS STRING),
    CAST((SELECT COUNT(*) FROM q1_pyspark) AS STRING),
    (SELECT COUNT(*) FROM q1_sql) = 1
      AND (SELECT COUNT(*) FROM q1_pyspark) = 1
      AND (SELECT COUNT(DISTINCT struct(start_year, end_year)) FROM q1_sql) = 1
      AND (
        SELECT COUNT(DISTINCT struct(start_year, end_year)) FROM q1_pyspark
      ) = 1,
    'Both implementations require one row keyed by the inclusive year range.'

  UNION ALL
  SELECT
    'question_1',
    'q1_values_within_tolerance',
    CAST(mismatch_count AS STRING),
    '0',
    mismatch_count = 0,
    'Discrete fields are exact; DOUBLE mean and stddev use tolerance 1e-6.'
  FROM q1_value_mismatches

  UNION ALL
  SELECT
    'question_1',
    'q1_year_bounds_and_semantics',
    concat_ws(
      ',',
      CAST(start_year AS STRING),
      CAST(end_year AS STRING),
      CAST(year_count AS STRING),
      stddev_semantics
    ),
    '2013,2018,6,population',
    start_year = 2013
      AND end_year = 2018
      AND year_count = 6
      AND stddev_semantics = 'population',
    'The requested complete finite range uses population standard deviation.'
  FROM q1_pyspark

  UNION ALL
  SELECT
    'question_1',
    'q1_source_spot_check',
    CAST(mismatch_count AS STRING),
    '0',
    mismatch_count = 0,
    'The published summary reconciles to a direct six-row Silver calculation.'
  FROM q1_value_mismatches

  UNION ALL
  SELECT
    'question_2',
    'q2_schema_parity',
    sql_schema.schema_signature,
    pyspark_schema.schema_signature,
    sql_schema.schema_signature = pyspark_schema.schema_signature,
    'SQL and PySpark expose the same ordered field types.'
  FROM q2_sql_schema AS sql_schema
  CROSS JOIN q2_pyspark_schema AS pyspark_schema

  UNION ALL
  SELECT
    'question_2',
    'q2_row_count_parity',
    CAST((SELECT COUNT(*) FROM q2_sql) AS STRING),
    CAST((SELECT COUNT(*) FROM q2_pyspark) AS STRING),
    (SELECT COUNT(*) FROM q2_sql) = (SELECT COUNT(*) FROM q2_pyspark)
      AND (SELECT COUNT(*) FROM q2_sql) = (
        SELECT COUNT(*) FROM workspace.rearc_data_quest.silver_bls_series
      ),
    'Both implementations preserve the complete governed series inventory.'

  UNION ALL
  SELECT
    'question_2',
    'q2_unique_key_parity',
    CAST((SELECT COUNT(DISTINCT series_id) FROM q2_sql) AS STRING),
    CAST((SELECT COUNT(DISTINCT series_id) FROM q2_pyspark) AS STRING),
    (SELECT COUNT(*) FROM q2_sql)
      = (SELECT COUNT(DISTINCT series_id) FROM q2_sql)
      AND (SELECT COUNT(*) FROM q2_pyspark)
        = (SELECT COUNT(DISTINCT series_id) FROM q2_pyspark),
    'Every series_id appears exactly once in each result.'

  UNION ALL
  SELECT
    'question_2',
    'q2_exact_value_parity',
    CAST(mismatch_count AS STRING),
    '0',
    mismatch_count = 0,
    'Labels, nullable years, DECIMAL sums, counts, and flags match exactly.'
  FROM q2_value_mismatches

  UNION ALL
  SELECT
    'question_2',
    'q2_earliest_year_tie_break',
    CAST(violation_count AS STRING),
    '0',
    violation_count = 0,
    'Each selected result uses the earliest year among equal maximum sums.'
  FROM q2_tie_break_violations

  UNION ALL
  SELECT
    'question_2',
    'q2_source_spot_check',
    CAST(COUNT_IF(
      best_year = 1994
      AND annual_quarterly_sum = source_sum
      AND source_quarter_count = 4
    ) AS STRING),
    '1',
    COUNT(*) = 1
      AND COUNT_IF(
        best_year = 1994
        AND annual_quarterly_sum = source_sum
        AND source_quarter_count = 4
      ) = 1,
    'PRS30006032 reconciles to four source quarters in selected year 1994.'
  FROM q2_spot_check

  UNION ALL
  SELECT
    'question_3',
    'q3_schema_parity',
    sql_schema.schema_signature,
    pyspark_schema.schema_signature,
    sql_schema.schema_signature = pyspark_schema.schema_signature,
    'SQL and PySpark expose the same ordered field types.'
  FROM q3_sql_schema AS sql_schema
  CROSS JOIN q3_pyspark_schema AS pyspark_schema

  UNION ALL
  SELECT
    'question_3',
    'q3_row_count_parity',
    CAST((SELECT COUNT(*) FROM q3_sql) AS STRING),
    CAST((SELECT COUNT(*) FROM q3_pyspark) AS STRING),
    (SELECT COUNT(*) FROM q3_sql) = (SELECT COUNT(*) FROM q3_pyspark),
    'Both implementations retain the same selected BLS history.'

  UNION ALL
  SELECT
    'question_3',
    'q3_unique_key_parity',
    CAST((
      SELECT COUNT(DISTINCT struct(series_id, year)) FROM q3_sql
    ) AS STRING),
    CAST((
      SELECT COUNT(DISTINCT struct(series_id, year)) FROM q3_pyspark
    ) AS STRING),
    (SELECT COUNT(*) FROM q3_sql) = (
      SELECT COUNT(DISTINCT struct(series_id, year)) FROM q3_sql
    )
      AND (SELECT COUNT(*) FROM q3_pyspark) = (
        SELECT COUNT(DISTINCT struct(series_id, year)) FROM q3_pyspark
      ),
    'The deterministic ordering key series_id + year is complete and unique.'

  UNION ALL
  SELECT
    'question_3',
    'q3_exact_value_parity',
    CAST(mismatch_count AS STRING),
    '0',
    mismatch_count = 0,
    'Labels, DECIMAL values, nullable population, and flags match exactly.'
  FROM q3_value_mismatches

  UNION ALL
  SELECT
    'question_3',
    'q3_source_preservation_and_bounds',
    concat_ws(
      ',',
      CAST(result.result_rows AS STRING),
      CAST(result.result_years AS STRING),
      CAST(result.result_start_year AS STRING),
      CAST(result.result_end_year AS STRING)
    ),
    concat_ws(
      ',',
      CAST(source.source_rows AS STRING),
      CAST(source.source_years AS STRING),
      CAST(source.source_start_year AS STRING),
      CAST(source.source_end_year AS STRING)
    ),
    result.result_rows = source.source_rows
      AND result.result_years = source.source_years
      AND result.result_start_year = source.source_start_year
      AND result.result_end_year = source.source_end_year
      AND result.inconsistent_match_flags = 0,
    'The left join preserves source cardinality and bounds; flags reflect nulls.'
  FROM q3_result_invariants AS result
  CROSS JOIN q3_source_invariants AS source

  UNION ALL
  SELECT
    'question_3',
    'q3_source_spot_check',
    CAST(mismatch_count AS STRING),
    '0',
    mismatch_count = 0,
    'Five boundary, matched, and internal-gap years reconcile to Silver.'
  FROM q3_spot_check
)
SELECT
  question,
  check_name,
  actual_value,
  expected_value,
  passed,
  interpretation
FROM checks
ORDER BY question, check_name;
