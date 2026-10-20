-- DQ-27: latest-update expectation metrics from the Databricks event log.
-- Run as the materialized-view owner. Each statement is intentionally
-- independent so an unavailable layer cannot hide the other layers' evidence.

WITH events AS (
  SELECT * FROM event_log(
    TABLE(workspace.rearc_data_quest.bronze_datausa_population)
  )
),
latest_update AS (
  SELECT origin:update_id::STRING AS update_id
  FROM events
  WHERE event_type = 'create_update'
  ORDER BY timestamp DESC
  LIMIT 1
),
expectations AS (
  SELECT EXPLODE(FROM_JSON(
    details:flow_progress.data_quality.expectations,
    'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
  )) AS expectation
  FROM events CROSS JOIN latest_update
  WHERE event_type = 'flow_progress'
    AND origin:update_id::STRING = latest_update.update_id
)
SELECT
  'BRONZE' AS layer,
  expectation.dataset AS dataset,
  expectation.name AS expectation,
  SUM(expectation.passed_records) AS passed_records,
  SUM(expectation.failed_records) AS rejected_or_blocking_records,
  SUM(expectation.failed_records) = 0 AS passed
FROM expectations
GROUP BY expectation.dataset, expectation.name
ORDER BY dataset, expectation;

WITH events AS (
  SELECT * FROM event_log(
    TABLE(workspace.rearc_data_quest.silver_population)
  )
),
latest_update AS (
  SELECT origin:update_id::STRING AS update_id
  FROM events
  WHERE event_type = 'create_update'
  ORDER BY timestamp DESC
  LIMIT 1
),
expectations AS (
  SELECT EXPLODE(FROM_JSON(
    details:flow_progress.data_quality.expectations,
    'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
  )) AS expectation
  FROM events CROSS JOIN latest_update
  WHERE event_type = 'flow_progress'
    AND origin:update_id::STRING = latest_update.update_id
)
SELECT
  'SILVER' AS layer,
  expectation.dataset AS dataset,
  expectation.name AS expectation,
  SUM(expectation.passed_records) AS passed_records,
  SUM(expectation.failed_records) AS rejected_or_blocking_records,
  SUM(expectation.failed_records) = 0 AS passed
FROM expectations
GROUP BY expectation.dataset, expectation.name
ORDER BY dataset, expectation;

WITH events AS (
  SELECT * FROM event_log(
    TABLE(workspace.rearc_data_quest.gold_population_summary_2013_2018)
  )
),
latest_update AS (
  SELECT origin:update_id::STRING AS update_id
  FROM events
  WHERE event_type = 'create_update'
  ORDER BY timestamp DESC
  LIMIT 1
),
expectations AS (
  SELECT EXPLODE(FROM_JSON(
    details:flow_progress.data_quality.expectations,
    'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
  )) AS expectation
  FROM events CROSS JOIN latest_update
  WHERE event_type = 'flow_progress'
    AND origin:update_id::STRING = latest_update.update_id
)
SELECT
  'GOLD' AS layer,
  expectation.dataset AS dataset,
  expectation.name AS expectation,
  SUM(expectation.passed_records) AS passed_records,
  SUM(expectation.failed_records) AS rejected_or_blocking_records,
  SUM(expectation.failed_records) = 0 AS passed
FROM expectations
GROUP BY expectation.dataset, expectation.name
ORDER BY dataset, expectation;
