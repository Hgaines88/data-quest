"""Controlled tests for the Spark-backed BLS manifest adapter."""

from datetime import datetime, timezone
import unittest

from data_quest.ingestion.manifest import ManifestEntry, ManifestStatus
from data_quest.ingestion.spark_manifest import (
    append_manifest_entries,
    ensure_manifest_table,
    load_current_manifest,
)


TABLE_NAME = "workspace.rearc_data_quest.bls_ingestion_manifest"


def manifest_entry() -> ManifestEntry:
    return ManifestEntry(
        source_url="https://download.bls.gov/pub/time.series/pr/pr.series",
        relative_path="pr.series",
        landed_path=(
            "/Volumes/workspace/rearc_data_quest/raw_landing/bls/productivity/"
            f"objects/{'a' * 64}/pr.series"
        ),
        source_etag='"etag"',
        source_last_modified="Fri, 17 Oct 2026 12:00:00 GMT",
        source_content_length=10,
        content_size_bytes=10,
        content_sha256="a" * 64,
        ingested_at_utc=datetime(2026, 10, 17, 16, 0, tzinfo=timezone.utc),
        run_id="20261017T160000Z-test",
        status=ManifestStatus.ACTIVE,
    )


class FakeQueryResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def collect(self) -> list[dict[str, object]]:
        return self._rows


class FakeWriter:
    def __init__(self) -> None:
        self.mode_name: str | None = None
        self.table_name: str | None = None

    def mode(self, name: str) -> "FakeWriter":
        self.mode_name = name
        return self

    def saveAsTable(self, name: str) -> None:  # noqa: N802 - Spark API spelling
        self.table_name = name


class FakeDataFrame:
    def __init__(self) -> None:
        self.write = FakeWriter()


class FakeSpark:
    def __init__(self, query_rows: list[dict[str, object]] | None = None) -> None:
        self.query_rows = query_rows or []
        self.sql_calls: list[str] = []
        self.created_rows: list[tuple[object, ...]] | None = None
        self.created_schema: str | None = None
        self.dataframe = FakeDataFrame()

    def sql(self, statement: str) -> FakeQueryResult:
        self.sql_calls.append(statement)
        return FakeQueryResult(self.query_rows)

    def createDataFrame(  # noqa: N802 - Spark API spelling
        self,
        rows: list[tuple[object, ...]],
        schema: str,
    ) -> FakeDataFrame:
        self.created_rows = rows
        self.created_schema = schema
        return self.dataframe


class SparkManifestTests(unittest.TestCase):
    def test_emits_delta_manifest_ddl_with_contract_fields(self) -> None:
        spark = FakeSpark()

        ensure_manifest_table(spark, TABLE_NAME)

        statement = spark.sql_calls[0]
        self.assertIn(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}", statement)
        self.assertIn("source_url STRING NOT NULL", statement)
        self.assertIn("landed_path STRING NOT NULL", statement)
        self.assertIn("content_sha256 STRING NOT NULL", statement)
        self.assertIn("run_id STRING NOT NULL", statement)
        self.assertIn("USING DELTA", statement)

    def test_maps_latest_state_query_result_to_typed_entries(self) -> None:
        entry = manifest_entry()
        row = {
            "source_url": entry.source_url,
            "relative_path": entry.relative_path,
            "landed_path": entry.landed_path,
            "source_etag": entry.source_etag,
            "source_last_modified": entry.source_last_modified,
            "source_content_length": entry.source_content_length,
            "content_size_bytes": entry.content_size_bytes,
            "content_sha256": entry.content_sha256,
            "ingested_at_utc": entry.ingested_at_utc.replace(tzinfo=None),
            "run_id": entry.run_id,
            "status": entry.status.value,
        }
        spark = FakeSpark([row])

        result = load_current_manifest(spark, TABLE_NAME)

        self.assertEqual(result, [entry])
        self.assertIn("ROW_NUMBER() OVER", spark.sql_calls[0])
        self.assertIn("PARTITION BY relative_path", spark.sql_calls[0])
        self.assertIn("WHERE manifest_rank = 1", spark.sql_calls[0])

    def test_builds_transition_dataframe_and_requests_append(self) -> None:
        spark = FakeSpark()
        entry = manifest_entry()

        append_manifest_entries(spark, TABLE_NAME, [entry])

        self.assertEqual(len(spark.created_rows), 1)
        self.assertIn("source_url STRING", spark.created_schema)
        self.assertEqual(spark.dataframe.write.mode_name, "append")
        self.assertEqual(spark.dataframe.write.table_name, TABLE_NAME)

    def test_empty_transition_list_does_not_write(self) -> None:
        spark = FakeSpark()

        append_manifest_entries(spark, TABLE_NAME, [])

        self.assertIsNone(spark.created_rows)
        self.assertIsNone(spark.dataframe.write.table_name)

    def test_rejects_unsafe_table_identifier_before_spark_execution(self) -> None:
        spark = FakeSpark()

        with self.assertRaisesRegex(ValueError, "table_name"):
            ensure_manifest_table(
                spark,
                "workspace.rearc_data_quest.manifest; DROP TABLE x",
            )

        self.assertEqual(spark.sql_calls, [])


if __name__ == "__main__":
    unittest.main()
