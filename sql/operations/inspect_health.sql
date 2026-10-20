-- DQ-27: privacy-safe source, Gold, and landing-run health.
-- Read only. Thresholds measure operational refresh recency, not the provider's
-- business-period cadence: WARN after 24 hours and FAIL after 48 hours.

WITH expected_sources(source) AS (
  VALUES ('bls'), ('datausa')
),
latest_source_run AS (
  SELECT *
  FROM workspace.rearc_data_quest.ingestion_run_audit
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY source ORDER BY completed_at_utc DESC, run_id DESC
  ) = 1
)
SELECT
  expected_sources.source,
  completed_at_utc AS last_completed_at_utc,
  outcome,
  TIMESTAMPDIFF(HOUR, completed_at_utc, CURRENT_TIMESTAMP()) AS age_hours,
  CASE
    WHEN completed_at_utc IS NULL THEN 'FAIL'
    WHEN outcome = 'FAILED' THEN 'FAIL'
    WHEN completed_at_utc < CURRENT_TIMESTAMP() - INTERVAL 48 HOURS THEN 'FAIL'
    WHEN completed_at_utc < CURRENT_TIMESTAMP() - INTERVAL 24 HOURS THEN 'WARN'
    ELSE 'HEALTHY'
  END AS health_status,
  discovered_count,
  downloaded_count,
  skipped_count,
  new_count,
  changed_count,
  removed_count,
  failed_file_count,
  published_transition_count
FROM expected_sources
LEFT JOIN latest_source_run USING (source)
ORDER BY expected_sources.source;

-- One Gold materialized view exposes the shared Gold pipeline event log. The
-- latest terminal update is the authoritative pipeline-refresh signal.
WITH gold_events AS (
  SELECT * FROM event_log(
    TABLE(workspace.rearc_data_quest.gold_population_summary_2013_2018)
  )
),
latest_gold_update AS (
  SELECT
    timestamp AS completed_at_utc,
    FROM_JSON(
      details,
      'struct<update_progress:struct<state:string>>'
    ).update_progress.state AS update_state
  FROM gold_events
  WHERE event_type = 'update_progress'
    AND FROM_JSON(
      details,
      'struct<update_progress:struct<state:string>>'
    ).update_progress.state IN ('COMPLETED', 'FAILED', 'CANCELED')
  ORDER BY timestamp DESC
  LIMIT 1
)
SELECT
  'GOLD_PIPELINE' AS object_name,
  completed_at_utc,
  update_state,
  TIMESTAMPDIFF(HOUR, completed_at_utc, CURRENT_TIMESTAMP()) AS age_hours,
  CASE
    WHEN update_state <> 'COMPLETED' THEN 'FAIL'
    WHEN completed_at_utc < CURRENT_TIMESTAMP() - INTERVAL 48 HOURS THEN 'FAIL'
    WHEN completed_at_utc < CURRENT_TIMESTAMP() - INTERVAL 24 HOURS THEN 'WARN'
    ELSE 'HEALTHY'
  END AS health_status
FROM latest_gold_update;

-- Exact contract counts make incomplete Gold publication immediately visible.
SELECT 'gold_population_summary_2013_2018' AS object_name,
       COUNT(*) AS row_count, 1 AS expected_row_count,
       COUNT(*) = 1 AS passed
FROM workspace.rearc_data_quest.gold_population_summary_2013_2018
UNION ALL
SELECT 'gold_bls_best_year_by_series', COUNT(*), 282, COUNT(*) = 282
FROM workspace.rearc_data_quest.gold_bls_best_year_by_series
UNION ALL
SELECT 'gold_bls_q01_population', COUNT(*), 39, COUNT(*) = 39
FROM workspace.rearc_data_quest.gold_bls_q01_population
ORDER BY object_name;

-- Failure details are deliberately categorical: no exception message, URL,
-- contact address, workspace ID, or credential is stored in this table.
SELECT
  source,
  run_id,
  completed_at_utc,
  failure_stage,
  error_category,
  discovered_count,
  downloaded_count,
  failed_file_count,
  published_transition_count
FROM workspace.rearc_data_quest.ingestion_run_audit
WHERE outcome = 'FAILED'
  AND completed_at_utc >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
ORDER BY completed_at_utc DESC;
