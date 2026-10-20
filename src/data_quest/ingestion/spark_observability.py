"""Spark adapter for append-only ingestion run audit records."""

from typing import Any

from data_quest.ingestion.observability import IngestionRunAudit
from data_quest.ingestion.spark_manifest import _validated_table_name


_AUDIT_SCHEMA = """
source STRING,
run_id STRING,
started_at_utc TIMESTAMP,
completed_at_utc TIMESTAMP,
outcome STRING,
failure_stage STRING,
error_category STRING,
discovered_count BIGINT,
downloaded_count BIGINT,
skipped_count BIGINT,
new_count BIGINT,
changed_count BIGINT,
removed_count BIGINT,
failed_file_count BIGINT,
published_transition_count BIGINT
""".strip()


def ensure_ingestion_run_audit_table(spark: Any, table_name: str) -> None:
    """Create the append-only operational table with a validated identifier."""

    safe_table_name = _validated_table_name(table_name)
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {safe_table_name} (
            source STRING NOT NULL,
            run_id STRING NOT NULL,
            started_at_utc TIMESTAMP NOT NULL,
            completed_at_utc TIMESTAMP NOT NULL,
            outcome STRING NOT NULL,
            failure_stage STRING,
            error_category STRING,
            discovered_count BIGINT NOT NULL,
            downloaded_count BIGINT NOT NULL,
            skipped_count BIGINT NOT NULL,
            new_count BIGINT NOT NULL,
            changed_count BIGINT NOT NULL,
            removed_count BIGINT NOT NULL,
            failed_file_count BIGINT NOT NULL,
            published_transition_count BIGINT NOT NULL
        ) USING DELTA
        """
    )


def append_ingestion_run_audit(
    spark: Any,
    table_name: str,
    audit: IngestionRunAudit,
) -> None:
    """Append exactly one sanitized terminal run record."""

    safe_table_name = _validated_table_name(table_name)
    row = (
        audit.source,
        audit.run_id,
        audit.started_at_utc,
        audit.completed_at_utc,
        audit.outcome,
        audit.failure_stage,
        audit.error_category,
        audit.discovered_count,
        audit.downloaded_count,
        audit.skipped_count,
        audit.new_count,
        audit.changed_count,
        audit.removed_count,
        audit.failed_file_count,
        audit.published_transition_count,
    )
    dataframe = spark.createDataFrame([row], schema=_AUDIT_SCHEMA)
    dataframe.write.mode("append").saveAsTable(safe_table_name)


def append_failed_run_audit_best_effort(
    spark: Any,
    table_name: str,
    audit: IngestionRunAudit,
) -> bool:
    """Try to retain a failure row without masking the primary exception."""

    if audit.outcome != "FAILED":
        raise ValueError("best-effort audit is restricted to failed runs")
    try:
        append_ingestion_run_audit(spark, table_name, audit)
    except Exception:
        return False
    return True
