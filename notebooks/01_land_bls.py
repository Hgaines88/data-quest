# Databricks notebook source
"""Discover, verify, and safely land the complete BLS productivity folder.

Run this notebook from the repository's Databricks Git folder. Re-running it is
expected: unchanged content is verified but is not promoted or republished.
Do not run two copies concurrently; this assessment workflow is single-writer.
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

from data_quest.ingestion.discovery import discover_source_files  # noqa: E402
from data_quest.ingestion.download import verify_file_evidence  # noqa: E402
from data_quest.ingestion.landing import (  # noqa: E402
    execute_landing_plan,
    prepare_bls_landing,
)
from data_quest.ingestion.manifest import ManifestStatus  # noqa: E402
from data_quest.ingestion.spark_manifest import (  # noqa: E402
    append_manifest_entries,
    ensure_manifest_table,
    load_current_manifest,
)

# COMMAND ----------

dbutils.widgets.text("contact_email", "", "BLS request contact email")
dbutils.widgets.text("catalog", "workspace", "Unity Catalog catalog")
dbutils.widgets.text("schema", "rearc_data_quest", "Project schema")
dbutils.widgets.text("volume", "raw_landing", "Raw managed Volume")

contact_email = dbutils.widgets.get("contact_email").strip()
catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()

if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email):
    raise ValueError("Enter a valid contact_email widget value before running")

for name, value in {"catalog": catalog, "schema": schema, "volume": volume}.items():
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"{name} must be a safe SQL identifier")

BLS_DIRECTORY_URL = "https://download.bls.gov/pub/time.series/pr/"
USER_AGENT = f"rearc-data-quest/0.1 (contact: {contact_email})"
VOLUME_SOURCE_ROOT = (
    f"/Volumes/{catalog}/{schema}/{volume}/bls/productivity"
)
MANIFEST_TABLE = f"{catalog}.{schema}.bls_ingestion_manifest"

# COMMAND ----------

# DQ-02 already established these objects. The idempotent statements make the
# notebook reproducible in another authorized workspace.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")
ensure_manifest_table(spark, MANIFEST_TABLE)

# COMMAND ----------

run_time = datetime.now(timezone.utc)
run_id = f"{run_time:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"

source_files = discover_source_files(
    BLS_DIRECTORY_URL,
    USER_AGENT,
    timeout_seconds=30.0,
    max_attempts=3,
    backoff_seconds=1.0,
)
current_manifest = load_current_manifest(spark, MANIFEST_TABLE)

print(f"Run: {run_id}")
print(f"Discovered files: {len(source_files)}")
print(f"Current manifest objects: {len(current_manifest)}")

# COMMAND ----------

landing_plan = prepare_bls_landing(
    source_files,
    current_manifest,
    user_agent=USER_AGENT,
    volume_source_root=VOLUME_SOURCE_ROOT,
    run_id=run_id,
    ingested_at_utc=run_time,
    timeout_seconds=30.0,
    max_attempts=3,
    backoff_seconds=1.0,
)

landing_result = execute_landing_plan(
    landing_plan,
    publisher=lambda entries: append_manifest_entries(
        spark,
        MANIFEST_TABLE,
        entries,
    ),
)

display(spark.createDataFrame([asdict(landing_result)]))

# COMMAND ----------

# Independent post-commit reconciliation: the current active manifest must
# match discovery exactly, and every referenced immutable object must match its
# committed byte count and SHA-256 digest.
committed_manifest = load_current_manifest(spark, MANIFEST_TABLE)
active_entries = [
    entry for entry in committed_manifest if entry.status is ManifestStatus.ACTIVE
]
discovered_paths = {source.name for source in source_files}
active_paths = {entry.relative_path for entry in active_entries}

assert active_paths == discovered_paths, (
    f"active manifest differs from discovery: "
    f"missing={sorted(discovered_paths - active_paths)}, "
    f"unexpected={sorted(active_paths - discovered_paths)}"
)

for entry in active_entries:
    verify_file_evidence(
        entry.landed_path,
        expected_size=entry.content_size_bytes,
        expected_sha256=entry.content_sha256,
    )

reconciliation_rows = [
    {
        "relative_path": entry.relative_path,
        "content_size_bytes": entry.content_size_bytes,
        "sha256_prefix": entry.content_sha256[:12],
        "status": entry.status.value,
        "run_id": entry.run_id,
    }
    for entry in active_entries
]

print(f"Reconciled active files: {len(active_entries)}")
display(spark.createDataFrame(reconciliation_rows).orderBy("relative_path"))
