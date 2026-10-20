-- Run as a dedicated non-admin member of data_quest_readonly_analysts.
-- Each statement must succeed and return one row.

SELECT COUNT(*) AS population_summary_rows
FROM workspace.rearc_data_quest.gold_population_summary_2013_2018;

SELECT COUNT(*) AS best_year_series_rows
FROM workspace.rearc_data_quest.gold_bls_best_year_by_series;

SELECT COUNT(*) AS q01_population_context_rows
FROM workspace.rearc_data_quest.gold_bls_q01_population;

