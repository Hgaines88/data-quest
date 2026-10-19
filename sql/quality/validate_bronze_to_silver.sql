-- DQ-15: repeatable Bronze-to-Silver reconciliation.
-- Passing condition: every output row has passed = true.

WITH
counts AS (
  SELECT
    (SELECT count(*) FROM workspace.rearc_data_quest.bronze_bls_observation_all) AS bronze_observations,
    (SELECT count(*) FROM workspace.rearc_data_quest.silver_bls_observation) AS silver_observations,
    (SELECT count(*) FROM workspace.rearc_data_quest.bronze_bls_series) AS bronze_series,
    (SELECT count(*) FROM workspace.rearc_data_quest.silver_bls_series) AS silver_series,
    (
      SELECT count(*)
      FROM workspace.rearc_data_quest.bronze_datausa_population
      WHERE trim(`Nation ID`) = '01000US'
        AND trim(`Nation`) = 'United States'
    ) AS bronze_us_population,
    (SELECT count(*) FROM workspace.rearc_data_quest.silver_population) AS silver_population
),
checks AS (
  SELECT
    'observation_row_count_reconciles' AS check_name,
    silver_observations AS actual_value,
    bronze_observations AS expected_value,
    silver_observations = bronze_observations AS passed,
    'A difference is the number of Bronze rows rejected by Silver normalization.' AS interpretation
  FROM counts

  UNION ALL
  SELECT
    'series_row_count_reconciles',
    silver_series,
    bronze_series,
    silver_series = bronze_series,
    'A difference indicates a rejected or ambiguously enriched series.'
  FROM counts

  UNION ALL
  SELECT
    'population_us_row_count_reconciles',
    silver_population,
    bronze_us_population,
    silver_population = bronze_us_population,
    'Silver intentionally excludes Bronze records outside the US national grain.'
  FROM counts

  UNION ALL
  SELECT
    'observation_duplicate_keys',
    count(*),
    0,
    count(*) = 0,
    'Expected key: series_id + year + period_code.'
  FROM (
    SELECT series_id, year, period_code
    FROM workspace.rearc_data_quest.silver_bls_observation
    GROUP BY series_id, year, period_code
    HAVING count(*) > 1
  )

  UNION ALL
  SELECT
    'series_duplicate_keys',
    count(*),
    0,
    count(*) = 0,
    'Expected key: series_id.'
  FROM (
    SELECT series_id
    FROM workspace.rearc_data_quest.silver_bls_series
    GROUP BY series_id
    HAVING count(*) > 1
  )

  UNION ALL
  SELECT
    'population_duplicate_keys',
    count(*),
    0,
    count(*) = 0,
    'Expected key: nation_id + year.'
  FROM (
    SELECT nation_id, year
    FROM workspace.rearc_data_quest.silver_population
    GROUP BY nation_id, year
    HAVING count(*) > 1
  )

  UNION ALL
  SELECT
    'observation_required_nulls',
    count_if(
      series_id IS NULL OR year IS NULL OR period_code IS NULL OR value IS NULL
      OR source_file IS NULL OR source_path IS NULL OR ingested_at_utc IS NULL
      OR run_id IS NULL OR content_sha256 IS NULL
    ),
    0,
    count_if(
      series_id IS NULL OR year IS NULL OR period_code IS NULL OR value IS NULL
      OR source_file IS NULL OR source_path IS NULL OR ingested_at_utc IS NULL
      OR run_id IS NULL OR content_sha256 IS NULL
    ) = 0,
    'All required observation and provenance fields must be populated.'
  FROM workspace.rearc_data_quest.silver_bls_observation

  UNION ALL
  SELECT
    'series_required_nulls_or_blank_labels',
    count_if(
      series_id IS NULL OR series_label IS NULL OR trim(series_label) = ''
      OR sector_code IS NULL OR sector_name IS NULL
      OR class_code IS NULL OR class_text IS NULL
      OR measure_code IS NULL OR measure_text IS NULL
      OR duration_code IS NULL OR duration_text IS NULL
      OR seasonal_code IS NULL OR seasonal_text IS NULL
      OR begin_year IS NULL OR begin_period IS NULL
      OR end_year IS NULL OR end_period IS NULL
      OR source_file IS NULL OR source_path IS NULL OR ingested_at_utc IS NULL
      OR run_id IS NULL OR content_sha256 IS NULL
    ),
    0,
    count_if(
      series_id IS NULL OR series_label IS NULL OR trim(series_label) = ''
      OR sector_code IS NULL OR sector_name IS NULL
      OR class_code IS NULL OR class_text IS NULL
      OR measure_code IS NULL OR measure_text IS NULL
      OR duration_code IS NULL OR duration_text IS NULL
      OR seasonal_code IS NULL OR seasonal_text IS NULL
      OR begin_year IS NULL OR begin_period IS NULL
      OR end_year IS NULL OR end_period IS NULL
      OR source_file IS NULL OR source_path IS NULL OR ingested_at_utc IS NULL
      OR run_id IS NULL OR content_sha256 IS NULL
    ) = 0,
    'Every series requires provider-grounded labels and complete provenance.'
  FROM workspace.rearc_data_quest.silver_bls_series

  UNION ALL
  SELECT
    'population_required_nulls_or_invalid_values',
    count_if(
      nation_id IS NULL OR nation_id <> '01000US'
      OR nation IS NULL OR nation <> 'United States'
      OR year IS NULL OR population IS NULL
      OR population < 0 OR source_file IS NULL OR source_path IS NULL
      OR ingested_at_utc IS NULL OR run_id IS NULL OR content_sha256 IS NULL
    ),
    0,
    count_if(
      nation_id IS NULL OR nation_id <> '01000US'
      OR nation IS NULL OR nation <> 'United States'
      OR year IS NULL OR population IS NULL
      OR population < 0 OR source_file IS NULL OR source_path IS NULL
      OR ingested_at_utc IS NULL OR run_id IS NULL OR content_sha256 IS NULL
    ) = 0,
    'Population keys, values, and provenance must be present and valid.'
  FROM workspace.rearc_data_quest.silver_population

  UNION ALL
  SELECT
    'observation_series_orphans',
    count(*),
    0,
    count(*) = 0,
    'Every observation series_id must resolve to provider-grounded metadata.'
  FROM (
    SELECT DISTINCT observation.series_id
    FROM workspace.rearc_data_quest.silver_bls_observation AS observation
    LEFT ANTI JOIN workspace.rearc_data_quest.silver_bls_series AS series
      ON observation.series_id = series.series_id
  )

  UNION ALL
  SELECT
    'population_missing_required_years',
    count(*),
    0,
    count(*) = 0,
    'Required years are 2013 through 2018 inclusive.'
  FROM (
    SELECT explode(sequence(2013, 2018)) AS required_year
  ) AS required_years
    LEFT ANTI JOIN workspace.rearc_data_quest.silver_population AS population
      ON required_years.required_year = population.year
      AND population.nation_id = '01000US'
)
SELECT check_name, actual_value, expected_value, passed, interpretation
FROM checks
ORDER BY check_name;

