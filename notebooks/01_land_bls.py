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
from data_quest.ingestion.download import (  # noqa: E402
    promote_verified_file,
    verify_file_evidence,
)
from data_quest.ingestion.landing import (  # noqa: E402
    execute_landing_plan,
    prepare_bls_landing,
)
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

dbutils.widgets.text("contact_email", "", "BLS request contact email")
dbutils.widgets.text("catalog", "workspace", "Unity Catalog catalog")
dbutils.widgets.text("schema", "rearc_data_quest", "Project schema")
dbutils.widgets.text("volume", "raw_landing", "Raw managed Volume")
dbutils.widgets.dropdown(
    "allow_mass_removal",
    "false",
    ["false", "true"],
    "Allow reviewed BLS mass removal",
)
dbutils.widgets.dropdown(
    "controlled_failure",
    "false",
    ["false", "true"],
    "Controlled pre-publication failure",
)

# COMMAND ----------

contact_email = dbutils.widgets.get("contact_email").strip()
catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()
allow_mass_removal = (
    dbutils.widgets.get("allow_mass_removal").strip().casefold() == "true"
)
controlled_failure = (
    dbutils.widgets.get("controlled_failure").strip().casefold() == "true"
)

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
RUN_AUDIT_TABLE = f"{catalog}.{schema}.ingestion_run_audit"

# COMMAND ----------

# DQ-02 already established these objects. The idempotent statements make the
# notebook reproducible in another authorized workspace.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volume}")
ensure_manifest_table(spark, MANIFEST_TABLE)
ensure_ingestion_run_audit_table(spark, RUN_AUDIT_TABLE)

# COMMAND ----------

run_time = datetime.now(timezone.utc)
run_id = f"{run_time:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"

try:
    source_files = discover_source_files(
        BLS_DIRECTORY_URL,
        USER_AGENT,
        timeout_seconds=30.0,
        max_attempts=3,
        backoff_seconds=1.0,
    )
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="bls",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="DISCOVERY",
            error=error,
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise
try:
    current_manifest = load_current_manifest(spark, MANIFEST_TABLE)
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="bls",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="MANIFEST_READ",
            error=error,
            discovered_count=len(source_files),
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise
active_paths_before = {
    entry.relative_path
    for entry in current_manifest
    if entry.status is ManifestStatus.ACTIVE
}
discovered_paths = {source.name for source in source_files}
removal_candidates = active_paths_before - discovered_paths
confirmed_source_files = None
if removal_candidates:
    try:
        confirmed_source_files = discover_source_files(
            BLS_DIRECTORY_URL,
            USER_AGENT,
            timeout_seconds=30.0,
            max_attempts=3,
            backoff_seconds=1.0,
        )
    except Exception as error:
        audit_written = append_failed_run_audit_best_effort(
            spark,
            RUN_AUDIT_TABLE,
            failed_run_audit(
                source="bls",
                run_id=run_id,
                started_at_utc=run_time,
                completed_at_utc=datetime.now(timezone.utc),
                failure_stage="DISCOVERY_CONFIRMATION",
                error=error,
                discovered_count=len(source_files),
            ),
        )
        if not audit_written:
            print("WARNING: failure audit unavailable; inspect this task run")
        raise

print(f"Run: {run_id}")
print(f"Discovered files: {len(source_files)}")
print(f"Current manifest objects: {len(current_manifest)}")
print(f"Removal candidates: {len(removal_candidates)}")
print(f"Mass-removal override: {allow_mass_removal}")

# COMMAND ----------

try:
    landing_plan = prepare_bls_landing(
        source_files,
        current_manifest,
        confirmed_source_files=confirmed_source_files,
        allow_mass_removal=allow_mass_removal,
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
            source="bls",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="DOWNLOAD_AND_VALIDATE",
            error=error,
            discovered_count=len(source_files),
            downloaded_count=getattr(error, "verified_download_count", 0),
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise


class ControlledLandingFailure(RuntimeError):
    """Operator-requested failure used only for recovery validation."""


def promote_for_run(*args, **kwargs):
    if controlled_failure:
        raise ControlledLandingFailure("controlled pre-publication failure")
    return promote_verified_file(*args, **kwargs)


try:
    landing_result = execute_landing_plan(
        landing_plan,
        publisher=lambda entries: append_manifest_entries(
            spark,
            MANIFEST_TABLE,
            entries,
        ),
        promoter=promote_for_run,
    )
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="bls",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="PUBLICATION",
            error=error,
            discovered_count=len(source_files),
            downloaded_count=len(landing_plan.staged_files),
        ),
    )
    if not audit_written:
        print("WARNING: failure audit unavailable; inspect this task run")
    raise

display(spark.createDataFrame([asdict(landing_result)]))

# COMMAND ----------

# Independent post-commit reconciliation: the current active manifest must
# match discovery exactly, and every referenced immutable object must match its
# committed byte count and SHA-256 digest.
try:
    committed_manifest = load_current_manifest(spark, MANIFEST_TABLE)
    active_entries = [
        entry
        for entry in committed_manifest
        if entry.status is ManifestStatus.ACTIVE
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
except Exception as error:
    audit_written = append_failed_run_audit_best_effort(
        spark,
        RUN_AUDIT_TABLE,
        failed_run_audit(
            source="bls",
            run_id=run_id,
            started_at_utc=run_time,
            completed_at_utc=datetime.now(timezone.utc),
            failure_stage="RECONCILIATION",
            error=error,
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
        source="bls",
        run_id=run_id,
        started_at_utc=run_time,
        completed_at_utc=datetime.now(timezone.utc),
        result=landing_result,
    ),
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
