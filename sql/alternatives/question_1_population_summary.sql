-- Question 1 Spark SQL alternative to the primary PySpark Gold pipeline.
-- A missing or duplicate requested year makes this query return no result row.
WITH requested_population AS (
  SELECT
    year,
    population
  FROM workspace.rearc_data_quest.silver_population
  WHERE nation_id = '01000US'
    AND nation = 'United States'
    AND year BETWEEN 2013 AND 2018
),
summary AS (
  SELECT
    CAST(2013 AS INT) AS start_year,
    CAST(2018 AS INT) AS end_year,
    CAST(COUNT(*) AS INT) AS year_count,
    AVG(CAST(population AS DOUBLE)) AS mean_population,
    STDDEV_POP(CAST(population AS DOUBLE)) AS population_stddev,
    'population' AS stddev_semantics,
    COUNT(DISTINCT year) AS distinct_year_count,
    MIN(year) AS observed_start_year,
    MAX(year) AS observed_end_year
  FROM requested_population
)
SELECT
  start_year,
  end_year,
  year_count,
  mean_population,
  population_stddev,
  stddev_semantics
FROM summary
WHERE year_count = 6
  AND distinct_year_count = 6
  AND observed_start_year = 2013
  AND observed_end_year = 2018;
