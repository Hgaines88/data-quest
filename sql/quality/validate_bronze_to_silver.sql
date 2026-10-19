-- DQ-15: repeatable Bronze-to-Silver reconciliation.
-- Passing condition: every output row has passed = true.

WITH
bronze_observations_normalized AS (
  SELECT
    trim(series_id) AS series_id,
    try_cast(trim(year) AS INT) AS year,
    trim(period) AS period_code,
    try_cast(trim(value) AS DECIMAL(20, 6)) AS value,
    nullif(trim(footnote_codes), '') AS footnote_codes
  FROM workspace.rearc_data_quest.bronze_bls_observation_all
),
silver_observations_core AS (
  SELECT series_id, year, period_code, value, footnote_codes
  FROM workspace.rearc_data_quest.silver_bls_observation
),
observation_conversion_mismatches AS (
  SELECT bronze.*
  FROM bronze_observations_normalized AS bronze
  LEFT ANTI JOIN silver_observations_core AS silver
    ON bronze.series_id <=> silver.series_id
    AND bronze.year <=> silver.year
    AND bronze.period_code <=> silver.period_code
    AND bronze.value <=> silver.value
    AND bronze.footnote_codes <=> silver.footnote_codes
  UNION ALL
  SELECT silver.*
  FROM silver_observations_core AS silver
  LEFT ANTI JOIN bronze_observations_normalized AS bronze
    ON bronze.series_id <=> silver.series_id
    AND bronze.year <=> silver.year
    AND bronze.period_code <=> silver.period_code
    AND bronze.value <=> silver.value
    AND bronze.footnote_codes <=> silver.footnote_codes
),
bronze_series_normalized AS (
  SELECT
    trim(series_id) AS series_id,
    trim(sector_code) AS sector_code,
    trim(class_code) AS class_code,
    trim(measure_code) AS measure_code,
    trim(duration_code) AS duration_code,
    trim(seasonal) AS seasonal_code,
    try_cast(nullif(trim(base_year), '-') AS INT) AS base_year,
    nullif(trim(footnote_codes), '') AS footnote_codes,
    try_cast(trim(begin_year) AS INT) AS begin_year,
    trim(begin_period) AS begin_period,
    try_cast(trim(end_year) AS INT) AS end_year,
    trim(end_period) AS end_period
  FROM workspace.rearc_data_quest.bronze_bls_series
),
silver_series_core AS (
  SELECT
    series_id, sector_code, class_code, measure_code, duration_code,
    seasonal_code, base_year, footnote_codes, begin_year, begin_period,
    end_year, end_period
  FROM workspace.rearc_data_quest.silver_bls_series
),
series_conversion_mismatches AS (
  SELECT bronze.*
  FROM bronze_series_normalized AS bronze
  LEFT ANTI JOIN silver_series_core AS silver
    ON bronze.series_id <=> silver.series_id
    AND bronze.sector_code <=> silver.sector_code
    AND bronze.class_code <=> silver.class_code
    AND bronze.measure_code <=> silver.measure_code
    AND bronze.duration_code <=> silver.duration_code
    AND bronze.seasonal_code <=> silver.seasonal_code
    AND bronze.base_year <=> silver.base_year
    AND bronze.footnote_codes <=> silver.footnote_codes
    AND bronze.begin_year <=> silver.begin_year
    AND bronze.begin_period <=> silver.begin_period
    AND bronze.end_year <=> silver.end_year
    AND bronze.end_period <=> silver.end_period
  UNION ALL
  SELECT silver.*
  FROM silver_series_core AS silver
  LEFT ANTI JOIN bronze_series_normalized AS bronze
    ON bronze.series_id <=> silver.series_id
    AND bronze.sector_code <=> silver.sector_code
    AND bronze.class_code <=> silver.class_code
    AND bronze.measure_code <=> silver.measure_code
    AND bronze.duration_code <=> silver.duration_code
    AND bronze.seasonal_code <=> silver.seasonal_code
    AND bronze.base_year <=> silver.base_year
    AND bronze.footnote_codes <=> silver.footnote_codes
    AND bronze.begin_year <=> silver.begin_year
    AND bronze.begin_period <=> silver.begin_period
    AND bronze.end_year <=> silver.end_year
    AND bronze.end_period <=> silver.end_period
),
bronze_population_normalized AS (
  SELECT
    trim(`Nation ID`) AS nation_id,
    trim(`Nation`) AS nation,
    try_cast(`Year` AS INT) AS year,
    try_cast(`Population` AS BIGINT) AS population
  FROM workspace.rearc_data_quest.bronze_datausa_population
  WHERE trim(`Nation ID`) = '01000US'
    AND trim(`Nation`) = 'United States'
),
silver_population_core AS (
  SELECT nation_id, nation, year, population
  FROM workspace.rearc_data_quest.silver_population
),
population_conversion_mismatches AS (
  SELECT bronze.*
  FROM bronze_population_normalized AS bronze
  LEFT ANTI JOIN silver_population_core AS silver
    ON bronze.nation_id <=> silver.nation_id
    AND bronze.nation <=> silver.nation
    AND bronze.year <=> silver.year
    AND bronze.population <=> silver.population
  UNION ALL
  SELECT silver.*
  FROM silver_population_core AS silver
  LEFT ANTI JOIN bronze_population_normalized AS bronze
    ON bronze.nation_id <=> silver.nation_id
    AND bronze.nation <=> silver.nation
    AND bronze.year <=> silver.year
    AND bronze.population <=> silver.population
),
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
    'observation_conversion_mismatches',
    count(*),
    0,
    count(*) = 0,
    'Bronze values must match Silver after the documented trims and casts.'
  FROM observation_conversion_mismatches

  UNION ALL
  SELECT
    'series_conversion_mismatches',
    count(*),
    0,
    count(*) = 0,
    'Bronze series fields must match the corresponding typed Silver fields.'
  FROM series_conversion_mismatches

  UNION ALL
  SELECT
    'population_conversion_mismatches',
    count(*),
    0,
    count(*) = 0,
    'Bronze US population values must match the typed Silver values exactly.'
  FROM population_conversion_mismatches

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
      OR year NOT BETWEEN 1000 AND 9999
      OR period_code NOT IN ('Q01', 'Q02', 'Q03', 'Q04', 'Q05')
      OR source_file IS NULL OR source_path IS NULL OR ingested_at_utc IS NULL
      OR run_id IS NULL OR content_sha256 IS NULL
    ),
    0,
    count_if(
      series_id IS NULL OR year IS NULL OR period_code IS NULL OR value IS NULL
      OR year NOT BETWEEN 1000 AND 9999
      OR period_code NOT IN ('Q01', 'Q02', 'Q03', 'Q04', 'Q05')
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
      OR begin_period NOT IN ('Q01', 'Q02', 'Q03', 'Q04', 'Q05')
      OR end_period NOT IN ('Q01', 'Q02', 'Q03', 'Q04', 'Q05')
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
      OR begin_period NOT IN ('Q01', 'Q02', 'Q03', 'Q04', 'Q05')
      OR end_period NOT IN ('Q01', 'Q02', 'Q03', 'Q04', 'Q05')
      OR source_file IS NULL OR source_path IS NULL OR ingested_at_utc IS NULL
      OR run_id IS NULL OR content_sha256 IS NULL
    ) = 0,
    'Every series requires valid periods, provider-grounded labels, and complete provenance.'
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

