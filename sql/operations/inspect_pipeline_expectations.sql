-- DQ-27: latest-update status and expectation metrics from the Databricks event log.
-- Run as the materialized-view owner. Each statement is intentionally
-- independent so an unavailable layer cannot hide the other layers' evidence.
-- A status-only row retains failed-update evidence when fail-fast expectations
-- emit no metric array; null counts never mean zero rejected records.

WITH events AS (
  SELECT * FROM event_log(TABLE(workspace.rearc_data_quest.bronze_datausa_population))
),
latest_update AS (
  SELECT origin.update_id AS update_id FROM events
  WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1
),
terminal_updates AS (
  SELECT
    FROM_JSON(details, 'struct<update_progress:struct<state:string>>').update_progress.state AS update_state,
    ROW_NUMBER() OVER (ORDER BY timestamp DESC) AS recency
  FROM events CROSS JOIN latest_update
  WHERE event_type = 'update_progress'
    AND origin.update_id = latest_update.update_id
    AND FROM_JSON(details, 'struct<update_progress:struct<state:string>>').update_progress.state
      IN ('COMPLETED', 'FAILED', 'CANCELED')
),
update_status AS (
  SELECT latest_update.update_id, terminal_updates.update_state
  FROM latest_update LEFT JOIN terminal_updates ON terminal_updates.recency = 1
),
expectation_summary AS (
  SELECT expectation.dataset AS dataset, expectation.name AS expectation,
    SUM(expectation.passed_records) AS passed_records,
    SUM(expectation.failed_records) AS rejected_or_blocking_records
  FROM events CROSS JOIN latest_update
  LATERAL VIEW EXPLODE(FROM_JSON(
    details:flow_progress.data_quality.expectations,
    'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
  )) exploded AS expectation
  WHERE event_type = 'flow_progress' AND origin.update_id = latest_update.update_id
  GROUP BY expectation.dataset, expectation.name
)
SELECT 'BRONZE' AS layer, update_status.update_id, update_status.update_state,
  expectation_summary.dataset, expectation_summary.expectation,
  expectation_summary.passed_records, expectation_summary.rejected_or_blocking_records,
  CASE
    WHEN update_status.update_state <> 'COMPLETED' OR update_status.update_state IS NULL THEN false
    WHEN expectation_summary.expectation IS NULL THEN NULL
    ELSE expectation_summary.rejected_or_blocking_records = 0
  END AS passed
FROM update_status LEFT JOIN expectation_summary ON TRUE
ORDER BY dataset, expectation;

WITH events AS (
  SELECT * FROM event_log(TABLE(workspace.rearc_data_quest.silver_population))
),
latest_update AS (
  SELECT origin.update_id AS update_id FROM events
  WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1
),
terminal_updates AS (
  SELECT
    FROM_JSON(details, 'struct<update_progress:struct<state:string>>').update_progress.state AS update_state,
    ROW_NUMBER() OVER (ORDER BY timestamp DESC) AS recency
  FROM events CROSS JOIN latest_update
  WHERE event_type = 'update_progress'
    AND origin.update_id = latest_update.update_id
    AND FROM_JSON(details, 'struct<update_progress:struct<state:string>>').update_progress.state
      IN ('COMPLETED', 'FAILED', 'CANCELED')
),
update_status AS (
  SELECT latest_update.update_id, terminal_updates.update_state
  FROM latest_update LEFT JOIN terminal_updates ON terminal_updates.recency = 1
),
expectation_summary AS (
  SELECT expectation.dataset AS dataset, expectation.name AS expectation,
    SUM(expectation.passed_records) AS passed_records,
    SUM(expectation.failed_records) AS rejected_or_blocking_records
  FROM events CROSS JOIN latest_update
  LATERAL VIEW EXPLODE(FROM_JSON(
    details:flow_progress.data_quality.expectations,
    'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
  )) exploded AS expectation
  WHERE event_type = 'flow_progress' AND origin.update_id = latest_update.update_id
  GROUP BY expectation.dataset, expectation.name
)
SELECT 'SILVER' AS layer, update_status.update_id, update_status.update_state,
  expectation_summary.dataset, expectation_summary.expectation,
  expectation_summary.passed_records, expectation_summary.rejected_or_blocking_records,
  CASE
    WHEN update_status.update_state <> 'COMPLETED' OR update_status.update_state IS NULL THEN false
    WHEN expectation_summary.expectation IS NULL THEN NULL
    ELSE expectation_summary.rejected_or_blocking_records = 0
  END AS passed
FROM update_status LEFT JOIN expectation_summary ON TRUE
ORDER BY dataset, expectation;

WITH events AS (
  SELECT * FROM event_log(TABLE(workspace.rearc_data_quest.gold_population_summary_2013_2018))
),
latest_update AS (
  SELECT origin.update_id AS update_id FROM events
  WHERE event_type = 'create_update' ORDER BY timestamp DESC LIMIT 1
),
terminal_updates AS (
  SELECT
    FROM_JSON(details, 'struct<update_progress:struct<state:string>>').update_progress.state AS update_state,
    ROW_NUMBER() OVER (ORDER BY timestamp DESC) AS recency
  FROM events CROSS JOIN latest_update
  WHERE event_type = 'update_progress'
    AND origin.update_id = latest_update.update_id
    AND FROM_JSON(details, 'struct<update_progress:struct<state:string>>').update_progress.state
      IN ('COMPLETED', 'FAILED', 'CANCELED')
),
update_status AS (
  SELECT latest_update.update_id, terminal_updates.update_state
  FROM latest_update LEFT JOIN terminal_updates ON terminal_updates.recency = 1
),
expectation_summary AS (
  SELECT expectation.dataset AS dataset, expectation.name AS expectation,
    SUM(expectation.passed_records) AS passed_records,
    SUM(expectation.failed_records) AS rejected_or_blocking_records
  FROM events CROSS JOIN latest_update
  LATERAL VIEW EXPLODE(FROM_JSON(
    details:flow_progress.data_quality.expectations,
    'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>'
  )) exploded AS expectation
  WHERE event_type = 'flow_progress' AND origin.update_id = latest_update.update_id
  GROUP BY expectation.dataset, expectation.name
)
SELECT 'GOLD' AS layer, update_status.update_id, update_status.update_state,
  expectation_summary.dataset, expectation_summary.expectation,
  expectation_summary.passed_records, expectation_summary.rejected_or_blocking_records,
  CASE
    WHEN update_status.update_state <> 'COMPLETED' OR update_status.update_state IS NULL THEN false
    WHEN expectation_summary.expectation IS NULL THEN NULL
    ELSE expectation_summary.rejected_or_blocking_records = 0
  END AS passed
FROM update_status LEFT JOIN expectation_summary ON TRUE
ORDER BY dataset, expectation;
