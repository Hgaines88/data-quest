-- Run as a dedicated non-admin member of data_quest_readonly_analysts.
-- Run ONE statement at a time. Do not run this file as a batch: execution
-- normally stops at the first failure.

-- The deployed Gold contract is a view, so this write must fail structurally
-- with EXPECT_TABLE_NOT_VIEW. This proves non-writability, but it is
-- not an authorization-denial test. The remaining four statements fail because
-- the analyst lacks the required privilege.
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

