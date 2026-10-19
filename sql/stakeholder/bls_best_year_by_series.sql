-- DQ-25 dashboard dataset: bls_best_year_by_series
-- Grain: one row per governed BLS series, including series without quarterly history.
SELECT
  series_id,
  series_label,
  best_year,
  annual_quarterly_sum,
  quarterly_observation_count,
  has_quarterly_observations
FROM workspace.rearc_data_quest.gold_bls_best_year_by_series
ORDER BY
  has_quarterly_observations DESC,
  annual_quarterly_sum DESC NULLS LAST,
  series_label,
  series_id;
