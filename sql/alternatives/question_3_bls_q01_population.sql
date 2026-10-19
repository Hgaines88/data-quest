-- Question 3 Spark SQL alternative to the primary PySpark Gold pipeline.
-- Population is contextual only; this output makes no causal claim.
WITH selected_observations AS (
  SELECT
    series_id,
    year,
    value AS q01_value
  FROM workspace.rearc_data_quest.silver_bls_observation
  WHERE series_id = 'PRS30006032'
    AND period_code = 'Q01'
),
input_cardinality AS (
  SELECT
    COUNT(*) AS observation_row_count,
    COUNT(DISTINCT year) AS distinct_year_count
  FROM selected_observations
),
selected_metadata AS (
  SELECT
    series_id,
    series_label
  FROM workspace.rearc_data_quest.silver_bls_series
  WHERE series_id = 'PRS30006032'
),
metadata_cardinality AS (
  SELECT COUNT(*) AS metadata_row_count
  FROM selected_metadata
),
input_validation AS (
  SELECT
    CASE
      WHEN input.observation_row_count > 0
        AND input.distinct_year_count = input.observation_row_count
        AND metadata.metadata_row_count = 1
      THEN TRUE
      ELSE RAISE_ERROR(
        CONCAT(
          'Question 3 requires a nonempty unique Q01 history and exactly one ',
          'metadata row; found observations=',
          CAST(input.observation_row_count AS STRING),
          ', distinct_years=',
          CAST(input.distinct_year_count AS STRING),
          ', metadata_rows=',
          CAST(metadata.metadata_row_count AS STRING),
          '.'
        )
      )
    END AS input_is_valid
  FROM input_cardinality AS input
  CROSS JOIN metadata_cardinality AS metadata
),
us_population AS (
  SELECT
    year,
    population
  FROM workspace.rearc_data_quest.silver_population
  WHERE nation_id = '01000US'
    AND nation = 'United States'
)
SELECT
  observations.series_id,
  metadata.series_label,
  observations.year,
  observations.q01_value,
  population.population,
  population.population IS NOT NULL AS population_match_found
FROM selected_observations AS observations
INNER JOIN selected_metadata AS metadata
  ON observations.series_id = metadata.series_id
LEFT JOIN us_population AS population
  ON observations.year = population.year
INNER JOIN input_validation AS validation
  ON validation.input_is_valid
ORDER BY observations.year;
