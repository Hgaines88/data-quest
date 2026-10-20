-- DQ-26 data-grant teardown. Remove dashboard and warehouse ACLs separately.

REVOKE SELECT ON TABLE
  workspace.rearc_data_quest.gold_population_summary_2013_2018
FROM `data_quest_readonly_analysts`;

REVOKE SELECT ON TABLE
  workspace.rearc_data_quest.gold_bls_best_year_by_series
FROM `data_quest_readonly_analysts`;

REVOKE SELECT ON TABLE
  workspace.rearc_data_quest.gold_bls_q01_population
FROM `data_quest_readonly_analysts`;

REVOKE USE SCHEMA ON SCHEMA workspace.rearc_data_quest
FROM `data_quest_readonly_analysts`;

REVOKE USE CATALOG ON CATALOG workspace
FROM `data_quest_readonly_analysts`;

