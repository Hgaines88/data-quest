# Databricks notebook source
"""Validate and safely land the assigned Data USA population response.

Run this notebook from the repository's Databricks Git folder. The original API
response bytes are preserved unchanged. Do not run two copies concurrently;
this assessment workflow is single-writer.
"""

# COMMAND ----------

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import uuid


def find_repository_root() -> Path:
    """Locate the repository root without assuming one notebook working path."""

    current = Path.cwd()
    for candidate in (current, *current.parents):
        if (candidate / "src" / "data_quest").is_dir():
            return candidate
    raise RuntimeError(
        "Run this notebook from the cloned data-quest Databricks Git folder"
    )


REPOSITORY_ROOT = find_repository_root()
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from data_quest.ingestion.datausa import (  # noqa: E402
    DATAUSA_USER_AGENT,
    POPULATION_RELATIVE_PATH,
    prepare_population_landing,
    validate_population_response,
)
from data_quest.ingestion.download import verify_file_evidence  # noqa: E402
from data_quest.ingestion.landing import execute_landing_plan  # noqa: E402
from data_quest.ingestion.manifest import ManifestStatus  # noqa: E402
from data_quest.ingestion.observability import (  # noqa: E402
    failed_run_audit,
    successful_run_audit,
)
from data_quest.ingestion.spark_manifest import (  # noqa: E402
    append_manifest_entries,
    ensure_manifest_table,
    load_current_manifest,
)
from data_quest.ingestion.spark_observability import (  # noqa: E402
    append_failed_run_audit_best_effort,
    append_ingestion_run_audit,
    ensure_ingestion_run_audit_table,
)

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace", "Unity Catalog catalog")
dbutils.widgets.text("schema", "rearc_data_quest", "Project schema")
dbutils.widgets.text("volume", "raw_landing", "Raw managed Volume")

# COMMAND ----------

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()

for name, value in {"catalog": catalog, "schema": schema, "volume": volume}.items():
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"{name} must be a safe SQL identifier")

DATAUSA_ENDPOINT = (
    "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?"
    "cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&"
    "measures=Population"
)
USER_AGENT = DATAUSA_USER_AGENT
VOLUME_SOURCE_ROOT = (
    f"/Volumes/{catalog}/{schema}/{volume}/datausa/population"
)
MANIFEST_TABLE = f"{catalog}.{schema}.datausa_ingestion_manifest"
RUN_AUDIT_TABLE = f"{catalog}.{schema}.ingestion_run_audit"

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")
ensure_manifest_table(spark, MANIFEST_TABLE)
ensure_ingestion_run_audit_table(spark, RUN_AUDIT_TABLE)

# COMMAND ----------

run_time = datetime.now(timezone.utc)
run_id = f"{run_time:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
current_manifest = load_current_manifest(spark, MANIFEST_TABLE)

print(f"Run: {run_id}")
print(f"Current manifest objects: {len(current_manifest)}")

# COMMAND ----------

try:
    landing_plan, response_summary = prepare_population_landing(
        DATAUSA_ENDPOINT,
        current_manifest,
        user_agent=USER_AGENT,
        volume_source_root=VOLUME_SOURCE_ROOT,
        run_id=run_id,
        ingested_at_utc=run_time,
        timeout_seconds=30.0,
        max_attempts=3,
        backoff_seconds=1.0,
    )
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="datausa",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="DOWNLOAD_AND_VALIDATE",
            error=error,
            discovered_count=1,
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise

try:
    landing_result = execute_landing_plan(
        landing_plan,
        publisher=lambda entries: append_manifest_entries(
            spark,
            MANIFEST_TABLE,
            entries,
        ),
    )
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="datausa",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="PUBLICATION",
            error=error,
            discovered_count=1,
            downloaded_count=len(landing_plan.staged_files),
            failed_file_count=1,
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise

display(
    spark.createDataFrame(
        [
            {
                **asdict(landing_result),
                **asdict(response_summary),
            }
        ]
    )
)

# COMMAND ----------

try:
    committed_manifest = load_current_manifest(spark, MANIFEST_TABLE)
    active_entries = [
        entry
        for entry in committed_manifest
        if entry.status is ManifestStatus.ACTIVE
    ]
    active_paths = {entry.relative_path for entry in active_entries}

    assert active_paths == {POPULATION_RELATIVE_PATH}, (
        f"active Data USA manifest paths are unexpected: {sorted(active_paths)}"
    )
    entry = active_entries[0]
    verify_file_evidence(
        entry.landed_path,
        expected_size=entry.content_size_bytes,
        expected_sha256=entry.content_sha256,
    )
    committed_summary = validate_population_response(entry.landed_path)
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="datausa",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="RECONCILIATION",
            error=error,
            failed_file_count=1,
            result=landing_result,
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise

append_ingestion_run_audit(
    spark,
    RUN_AUDIT_TABLE,
    successful_run_audit(
        source="datausa",
        run_id=run_id,
        started_at_utc=run_time,
        completed_at_utc=datetime.now(timezone.utc),
        result=landing_result,
    ),
)

print(f"Reconciled active files: {len(active_entries)}")
display(
    spark.createDataFrame(
        [
            {
                "relative_path": entry.relative_path,
                "content_size_bytes": entry.content_size_bytes,
                "sha256_prefix": entry.content_sha256[:12],
                "status": entry.status.value,
                "run_id": entry.run_id,
                **asdict(committed_summary),
            }
        ]
    )
)
