-- DQ-25 dashboard dataset: q01_population_context
-- Grain: one row per selected BLS series and year; population remains nullable.
SELECT
  series_id,
  series_label,
  year,
  q01_value,
  population,
  population_match_found
FROM workspace.rearc_data_quest.gold_bls_q01_population
ORDER BY series_id, year;
