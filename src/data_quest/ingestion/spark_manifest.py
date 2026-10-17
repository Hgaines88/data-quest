"""Small Spark adapter for atomic Delta manifest publication."""

from datetime import datetime, timezone
import re
from typing import Any

from data_quest.ingestion.manifest import ManifestEntry, ManifestStatus


_IDENTIFIER_PART = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DATAFRAME_SCHEMA = """
source_url STRING,
relative_path STRING,
landed_path STRING,
source_etag STRING,
source_last_modified STRING,
source_content_length BIGINT,
content_size_bytes BIGINT,
content_sha256 STRING,
ingested_at_utc TIMESTAMP,
run_id STRING,
status STRING
""".strip()


def ensure_manifest_table(spark: Any, table_name: str) -> None:
    """Create the Delta event table idempotently using a validated identifier."""

    safe_table_name = _validated_table_name(table_name)
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {safe_table_name} (
            source_url STRING NOT NULL,
            relative_path STRING NOT NULL,
            landed_path STRING NOT NULL,
            source_etag STRING,
            source_last_modified STRING,
            source_content_length BIGINT,
            content_size_bytes BIGINT NOT NULL,
            content_sha256 STRING NOT NULL,
            ingested_at_utc TIMESTAMP NOT NULL,
            run_id STRING NOT NULL,
            status STRING NOT NULL
        ) USING DELTA
        """
    )


def load_current_manifest(spark: Any, table_name: str) -> list[ManifestEntry]:
    """Load the latest committed transition for every source-relative path."""

    safe_table_name = _validated_table_name(table_name)
    rows = spark.sql(
        f"""
        SELECT
            source_url,
            relative_path,
            landed_path,
            source_etag,
            source_last_modified,
            source_content_length,
            content_size_bytes,
            content_sha256,
            ingested_at_utc,
            run_id,
            status
        FROM (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY relative_path
                    ORDER BY ingested_at_utc DESC, run_id DESC
                ) AS manifest_rank
            FROM {safe_table_name}
        )
        WHERE manifest_rank = 1
        ORDER BY relative_path
        """
    ).collect()

    entries: list[ManifestEntry] = []
    for row in rows:
        values = row.asDict(recursive=False) if hasattr(row, "asDict") else row
        ingested_at = values["ingested_at_utc"]
        if not isinstance(ingested_at, datetime):
            raise ValueError("manifest ingested_at_utc must be a timestamp")
        if ingested_at.tzinfo is None:
            ingested_at = ingested_at.replace(tzinfo=timezone.utc)
        else:
            ingested_at = ingested_at.astimezone(timezone.utc)

        entries.append(
            ManifestEntry(
                source_url=values["source_url"],
                relative_path=values["relative_path"],
                landed_path=values["landed_path"],
                source_etag=values["source_etag"],
                source_last_modified=values["source_last_modified"],
                source_content_length=values["source_content_length"],
                content_size_bytes=values["content_size_bytes"],
                content_sha256=values["content_sha256"],
                ingested_at_utc=ingested_at,
                run_id=values["run_id"],
                status=ManifestStatus(values["status"]),
            )
        )
    return entries


def append_manifest_entries(
    spark: Any,
    table_name: str,
    entries: list[ManifestEntry],
) -> None:
    """Append one run's transitions with a single atomic Delta write."""

    if not entries:
        return
    safe_table_name = _validated_table_name(table_name)
    rows = [
        (
            entry.source_url,
            entry.relative_path,
            entry.landed_path,
            entry.source_etag,
            entry.source_last_modified,
            entry.source_content_length,
            entry.content_size_bytes,
            entry.content_sha256,
            entry.ingested_at_utc,
            entry.run_id,
            entry.status.value,
        )
        for entry in sorted(entries, key=lambda entry: entry.relative_path)
    ]
    dataframe = spark.createDataFrame(rows, schema=_DATAFRAME_SCHEMA)
    dataframe.write.mode("append").saveAsTable(safe_table_name)


def _validated_table_name(table_name: str) -> str:
    parts = table_name.split(".")
    if len(parts) not in {1, 2, 3} or any(
        not _IDENTIFIER_PART.fullmatch(part) for part in parts
    ):
        raise ValueError(
            "table_name must contain one to three safe SQL identifier parts"
        )
    return ".".join(parts)
