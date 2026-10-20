"""Controlled tests for the Spark ingestion-audit adapter."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from data_quest.ingestion.observability import IngestionRunAudit
from data_quest.ingestion.spark_observability import (
    append_failed_run_audit_best_effort,
    append_ingestion_run_audit,
    ensure_ingestion_run_audit_table,
)
from tests.test_spark_manifest import FakeSpark


TABLE_NAME = "workspace.rearc_data_quest.ingestion_run_audit"


def audit_record() -> IngestionRunAudit:
    started = datetime(2026, 10, 20, tzinfo=timezone.utc)
    return IngestionRunAudit(
        source="bls",
        run_id="20261020T000000Z-test",
        started_at_utc=started,
        completed_at_utc=started + timedelta(seconds=3),
        outcome="SUCCEEDED",
        failure_stage=None,
        error_category=None,
        discovered_count=12,
        downloaded_count=12,
        skipped_count=12,
        new_count=0,
        changed_count=0,
        removed_count=0,
        failed_file_count=0,
        published_transition_count=0,
    )


class SparkObservabilityTests(unittest.TestCase):
    def test_emits_append_only_audit_table_contract(self) -> None:
        spark = FakeSpark()

        ensure_ingestion_run_audit_table(spark, TABLE_NAME)

        statement = spark.sql_calls[0]
        self.assertIn(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME}", statement)
        self.assertIn("failed_file_count BIGINT NOT NULL", statement)
        self.assertIn("error_category STRING", statement)
        self.assertNotIn("error_message", statement)
        self.assertIn("USING DELTA", statement)

    def test_appends_one_typed_terminal_record(self) -> None:
        spark = FakeSpark()

        append_ingestion_run_audit(spark, TABLE_NAME, audit_record())

        self.assertEqual(len(spark.created_rows), 1)
        self.assertIn("completed_at_utc TIMESTAMP", spark.created_schema)
        self.assertEqual(spark.dataframe.write.mode_name, "append")
        self.assertEqual(spark.dataframe.write.table_name, TABLE_NAME)

    def test_rejects_unsafe_table_identifier(self) -> None:
        spark = FakeSpark()

        with self.assertRaisesRegex(ValueError, "table_name"):
            ensure_ingestion_run_audit_table(spark, "audit; DROP TABLE x")

        self.assertEqual(spark.sql_calls, [])

    def test_best_effort_failure_audit_does_not_mask_primary_failure(self) -> None:
        spark = FakeSpark()
        spark.dataframe.write.saveAsTable = lambda name: (_ for _ in ()).throw(
            RuntimeError("audit unavailable")
        )
        failed = replace(
            audit_record(),
            outcome="FAILED",
            failure_stage="PUBLICATION",
            error_category="UNEXPECTED",
        )

        written = append_failed_run_audit_best_effort(spark, TABLE_NAME, failed)

        self.assertFalse(written)

    def test_best_effort_path_rejects_success_records(self) -> None:
        with self.assertRaisesRegex(ValueError, "failed runs"):
            append_failed_run_audit_best_effort(
                FakeSpark(), TABLE_NAME, audit_record()
            )


if __name__ == "__main__":
    unittest.main()
