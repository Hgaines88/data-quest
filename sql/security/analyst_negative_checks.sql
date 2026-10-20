-- Run as a dedicated non-admin member of data_quest_readonly_analysts.
-- Run ONE statement at a time. Every statement must fail with an authorization
-- error. Do not run this file as a batch: execution stops at the first denial.

-- Gold write must be denied even though SELECT is allowed.
UPDATE workspace.rearc_data_quest.gold_population_summary_2013_2018
SET mean_population = mean_population
WHERE false;

-- Lower-layer reads must be denied.
SELECT *
FROM workspace.rearc_data_quest.bronze_bls_observation_all
LIMIT 1;

SELECT *
FROM workspace.rearc_data_quest.silver_bls_observation
LIMIT 1;

-- Raw provider artifacts must be denied.
LIST '/Volumes/workspace/rearc_data_quest/raw_landing';

-- Schema object creation must be denied.
CREATE TABLE workspace.rearc_data_quest.dq26_unauthorized_probe (
  probe_id INT
);

