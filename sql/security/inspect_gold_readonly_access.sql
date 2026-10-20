-- Run each SHOW GRANTS statement as an owner or access administrator.
-- Confirm only USE CATALOG, USE SCHEMA, and the three exact SELECT grants are
-- assigned to data_quest_readonly_analysts.

SHOW GRANTS `data_quest_readonly_analysts` ON CATALOG workspace;

SHOW GRANTS `data_quest_readonly_analysts`
ON SCHEMA workspace.rearc_data_quest;

SHOW GRANTS `data_quest_readonly_analysts` ON TABLE
  workspace.rearc_data_quest.gold_population_summary_2013_2018;

SHOW GRANTS `data_quest_readonly_analysts` ON TABLE
  workspace.rearc_data_quest.gold_bls_best_year_by_series;

SHOW GRANTS `data_quest_readonly_analysts` ON TABLE
  workspace.rearc_data_quest.gold_bls_q01_population;

