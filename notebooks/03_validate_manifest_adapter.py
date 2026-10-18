# Databricks notebook source
"""Execute the manifest adapter against a temporary Delta table.

This is a controlled validation notebook, not a production ingestion job. It
proves that the emitted DDL, append, and latest-state ranking execute on the
authorized Databricks runtime, then drops the uniquely named validation table.
"""

# COMMAND ----------

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

from data_quest.ingestion.manifest import (  # noqa: E402
    ManifestEntry,
    ManifestStatus,
)
from data_quest.ingestion.spark_manifest import (  # noqa: E402
    append_manifest_entries,
    ensure_manifest_table,
    load_current_manifest,
)

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace", "Unity Catalog catalog")
dbutils.widgets.text("schema", "rearc_data_quest", "Project schema")

# COMMAND ----------

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()

for name, value in {"catalog": catalog, "schema": schema}.items():
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"{name} must be a safe SQL identifier")

validation_suffix = uuid.uuid4().hex[:12]
VALIDATION_TABLE = (
    f"{catalog}.{schema}.spark_manifest_validation_{validation_suffix}"
)

# COMMAND ----------

EXPECTED_COLUMNS = [
    "source_url",
    "relative_path",
    "landed_path",
    "source_etag",
    "source_last_modified",
    "source_content_length",
    "content_size_bytes",
    "content_sha256",
    "ingested_at_utc",
    "run_id",
    "status",
]


def validation_entry(
    relative_path: str,
    digest_character: str,
    ingested_at_utc: datetime,
    run_id: str,
    status: ManifestStatus,
) -> ManifestEntry:
    """Build one synthetic but contract-valid manifest transition."""

    digest = digest_character * 64
    return ManifestEntry(
        source_url=f"https://validation.invalid/{relative_path}",
        relative_path=relative_path,
        landed_path=(
            f"/Volumes/{catalog}/{schema}/raw_landing/validation/"
            f"objects/{digest}/{relative_path}"
        ),
        source_etag=None,
        source_last_modified=None,
        source_content_length=1,
        content_size_bytes=1,
        content_sha256=digest,
        ingested_at_utc=ingested_at_utc,
        run_id=run_id,
        status=status,
    )


older_time = datetime(2026, 10, 18, 0, 0, tzinfo=timezone.utc)
latest_time = datetime(2026, 10, 18, 1, 0, tzinfo=timezone.utc)
validation_entries = [
    validation_entry(
        "other.txt",
        "b",
        older_time,
        "20261018T000000Z-other",
        ManifestStatus.ACTIVE,
    ),
    validation_entry(
        "ranked.txt",
        "a",
        older_time,
        "z-older-timestamp",
        ManifestStatus.ACTIVE,
    ),
    validation_entry(
        "ranked.txt",
        "a",
        latest_time,
        "20261018T010000Z-a",
        ManifestStatus.ACTIVE,
    ),
    validation_entry(
        "ranked.txt",
        "a",
        latest_time,
        "20261018T010000Z-b",
        ManifestStatus.REMOVED,
    ),
]

# COMMAND ----------

validation_summary = None
try:
    ensure_manifest_table(spark, VALIDATION_TABLE)
    ensure_manifest_table(spark, VALIDATION_TABLE)
    actual_columns = spark.table(VALIDATION_TABLE).columns
    if actual_columns != EXPECTED_COLUMNS:
        raise RuntimeError(
            f"manifest columns differ: {actual_columns} != {EXPECTED_COLUMNS}"
        )

    append_manifest_entries(spark, VALIDATION_TABLE, validation_entries[:2])
    append_manifest_entries(spark, VALIDATION_TABLE, validation_entries[2:])
    inserted_count = spark.table(VALIDATION_TABLE).count()
    if inserted_count != len(validation_entries):
        raise RuntimeError(
            f"manifest append count differs: {inserted_count} != "
            f"{len(validation_entries)}"
        )

    current_entries = load_current_manifest(spark, VALIDATION_TABLE)
    current_paths = [entry.relative_path for entry in current_entries]
    if current_paths != ["other.txt", "ranked.txt"]:
        raise RuntimeError(
            f"latest-state rows differ: {current_paths}"
        )
    current_by_path = {entry.relative_path: entry for entry in current_entries}
    ranked = current_by_path["ranked.txt"]
    if (
        ranked.run_id != "20261018T010000Z-b"
        or ranked.status is not ManifestStatus.REMOVED
    ):
        raise RuntimeError(
            "latest-state ranking did not apply timestamp and run_id ordering"
        )

    validation_summary = {
        "inserted_transition_count": inserted_count,
        "current_path_count": len(current_entries),
        "ranked_run_id": ranked.run_id,
        "ranked_status": ranked.status.value,
        "schema_column_count": len(actual_columns),
    }
finally:
    spark.sql(f"DROP TABLE IF EXISTS {VALIDATION_TABLE}")

if validation_summary is None:
    raise RuntimeError("manifest adapter validation did not complete")

display(spark.createDataFrame([validation_summary]))
