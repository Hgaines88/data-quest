-- DQ-26 least-privilege data grants.
-- Precondition: the account group data_quest_readonly_analysts exists and is
-- assigned to the workspace. Run as the object owner or access administrator.

GRANT USE CATALOG ON CATALOG workspace
TO `data_quest_readonly_analysts`;

GRANT USE SCHEMA ON SCHEMA workspace.rearc_data_quest
TO `data_quest_readonly_analysts`;

GRANT SELECT ON TABLE
  workspace.rearc_data_quest.gold_population_summary_2013_2018
TO `data_quest_readonly_analysts`;

GRANT SELECT ON TABLE
  workspace.rearc_data_quest.gold_bls_best_year_by_series
TO `data_quest_readonly_analysts`;

GRANT SELECT ON TABLE
  workspace.rearc_data_quest.gold_bls_q01_population
TO `data_quest_readonly_analysts`;

