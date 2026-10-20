-- DQ-25 dashboard dataset: population_summary
-- Grain: one row for the inclusive 2013-2018 United States range.
SELECT
  start_year,
  end_year,
  year_count,
  mean_population,
  population_stddev,
  stddev_semantics
FROM workspace.rearc_data_quest.gold_population_summary_2013_2018;
