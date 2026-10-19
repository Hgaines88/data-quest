-- Question 2 Spark SQL alternative to the primary PySpark Gold pipeline.
-- Q05 is deliberately excluded because BLS defines it as an annual average.
WITH quarterly_annual_sums AS (
  SELECT
    series_id,
    year,
    SUM(value) AS annual_quarterly_sum,
    CAST(COUNT(*) AS INT) AS quarterly_observation_count
  FROM workspace.rearc_data_quest.silver_bls_observation
  WHERE period_code IN ('Q01', 'Q02', 'Q03', 'Q04')
  GROUP BY series_id, year
),
metadata_cardinality AS (
  SELECT
    series_id,
    COUNT(*) AS metadata_row_count
  FROM workspace.rearc_data_quest.silver_bls_series
  GROUP BY series_id
),
unresolved_quarterly_series AS (
  SELECT DISTINCT quarterly.series_id
  FROM quarterly_annual_sums AS quarterly
  LEFT JOIN metadata_cardinality AS metadata
    ON quarterly.series_id = metadata.series_id
  WHERE COALESCE(metadata.metadata_row_count, 0) <> 1
),
metadata_validation AS (
  SELECT
    CASE
      WHEN COUNT(*) = 0 THEN TRUE
      ELSE RAISE_ERROR(
        CONCAT(
          'Quarterly observations lack exactly one metadata row for ',
          CAST(COUNT(*) AS STRING),
          ' series_id value(s).'
        )
      )
    END AS metadata_is_valid
  FROM unresolved_quarterly_series
),
ranked_years AS (
  SELECT
    series_id,
    year AS best_year,
    annual_quarterly_sum,
    quarterly_observation_count,
    ROW_NUMBER() OVER (
      PARTITION BY series_id
      ORDER BY annual_quarterly_sum DESC, year ASC
    ) AS result_rank
  FROM quarterly_annual_sums
)
SELECT
  series.series_id,
  series.series_label,
  ranked.best_year,
  ranked.annual_quarterly_sum,
  COALESCE(ranked.quarterly_observation_count, 0)
    AS quarterly_observation_count,
  ranked.best_year IS NOT NULL AS has_quarterly_observations
FROM workspace.rearc_data_quest.silver_bls_series AS series
LEFT JOIN ranked_years AS ranked
  ON series.series_id = ranked.series_id
 AND ranked.result_rank = 1
INNER JOIN metadata_validation AS validation
  ON validation.metadata_is_valid
ORDER BY series.series_id;
