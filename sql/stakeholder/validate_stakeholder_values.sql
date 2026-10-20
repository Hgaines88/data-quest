-- DQ-25 acceptance query for the stakeholder exploration surface.
-- The expected values are regression anchors accepted on 2026-10-19.
-- A provider revision requires investigation and a reviewed anchor update.
WITH
q1 AS (
  SELECT *
  FROM workspace.rearc_data_quest.gold_population_summary_2013_2018
),
q2 AS (
  SELECT *
  FROM workspace.rearc_data_quest.gold_bls_best_year_by_series
  WHERE series_id = 'PRS30006032'
),
q3_expected AS (
  SELECT * FROM VALUES
    (2012, CAST(2.5 AS DECIMAL(20, 6)), CAST(NULL AS BIGINT), false),
    (2013, CAST(0.5 AS DECIMAL(20, 6)), CAST(316128839 AS BIGINT), true),
    (2020, CAST(-7.0 AS DECIMAL(20, 6)), CAST(NULL AS BIGINT), false),
    (2024, CAST(-0.7 AS DECIMAL(20, 6)), CAST(340110990 AS BIGINT), true),
    (2026, CAST(0.0 AS DECIMAL(20, 6)), CAST(NULL AS BIGINT), false)
  AS expected(year, q01_value, population, population_match_found)
),
q3_mismatches AS (
  SELECT expected.year
  FROM q3_expected AS expected
  LEFT JOIN workspace.rearc_data_quest.gold_bls_q01_population AS actual
    ON actual.series_id = 'PRS30006032'
   AND actual.year = expected.year
  WHERE actual.year IS NULL
     OR NOT (actual.q01_value <=> expected.q01_value)
     OR NOT (actual.population <=> expected.population)
     OR NOT (actual.population_match_found <=> expected.population_match_found)
),
checks AS (
  SELECT
    'population_summary_bounds' AS check_name,
    CONCAT_WS(',', start_year, end_year, year_count, stddev_semantics) AS actual_value,
    '2013,2018,6,population' AS expected_value,
    start_year = 2013 AND end_year = 2018 AND year_count = 6
      AND stddev_semantics = 'population' AS passed,
    'The KPI range is complete and uses population standard deviation.' AS interpretation
  FROM q1

  UNION ALL

  SELECT
    'population_summary_values',
    CONCAT_WS(',', mean_population, population_stddev),
    '322069808,3796119.9369343743',
    ABS(mean_population - 322069808.0) <= 0.000001
      AND ABS(population_stddev - 3796119.9369343743) <= 0.000001,
    'The two population KPI values reconcile to the accepted Gold run.'
  FROM q1

  UNION ALL

  SELECT
    'bls_series_spot_check',
    CONCAT_WS(',', best_year, annual_quarterly_sum, quarterly_observation_count,
      has_quarterly_observations),
    '1994,14.600000,4,true',
    best_year = 1994
      AND annual_quarterly_sum = CAST(14.6 AS DECIMAL(30, 6))
      AND quarterly_observation_count = 4
      AND has_quarterly_observations,
    'PRS30006032 uses four quarters and the deterministic best-year rule.'
  FROM q2

  UNION ALL

  SELECT
    'q01_population_context_spot_checks',
    CAST(COUNT(*) AS STRING),
    '0',
    COUNT(*) = 0,
    'Five boundary, matched, and internal-gap years preserve nullable context.'
  FROM q3_mismatches
)
SELECT
  check_name,
  actual_value,
  expected_value,
  passed,
  interpretation
FROM checks
ORDER BY check_name;
