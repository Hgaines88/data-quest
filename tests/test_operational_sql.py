"""Static safety and coverage checks for reviewer-facing operational SQL."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ROOT / "sql" / "operations"


class OperationalSqlTests(unittest.TestCase):
    def test_health_query_surfaces_required_metrics_and_thresholds(self) -> None:
        sql = (OPERATIONS / "inspect_health.sql").read_text()

        for field in (
            "discovered_count",
            "downloaded_count",
            "skipped_count",
            "changed_count",
            "removed_count",
            "failed_file_count",
            "completed_at_utc",
            "health_status",
        ):
            self.assertIn(field, sql)
        self.assertIn("INTERVAL 24 HOURS", sql)
        self.assertIn("INTERVAL 48 HOURS", sql)
        self.assertIn("VALUES ('bls'), ('datausa')", sql)
        self.assertIn("WHEN completed_at_utc IS NULL THEN 'FAIL'", sql)
        self.assertIn("VALUES ('GOLD_PIPELINE')", sql)
        self.assertIn("LEFT JOIN latest_gold_update ON TRUE", sql)

    def test_notebooks_delegate_failed_file_count_to_error_classification(self) -> None:
        notebooks = (
            ROOT / "notebooks" / "01_land_bls.py",
            ROOT / "notebooks" / "02_land_datausa_population.py",
        )

        for notebook in notebooks:
            source = notebook.read_text()
            self.assertNotIn("failed_file_count=1", source)
            self.assertIn('failure_stage="MANIFEST_READ"', source)
            self.assertIn(
                'downloaded_count=getattr(error, "verified_download_count", 0)',
                source,
            )

    def test_expectation_query_uses_stable_event_log_contract(self) -> None:
        sql = (OPERATIONS / "inspect_pipeline_expectations.sql").read_text()

        self.assertEqual(sql.count("event_log("), 3)
        self.assertIn("event_type = 'flow_progress'", sql)
        self.assertIn("passed_records", sql)
        self.assertIn("failed_records", sql)
        self.assertIn("rejected_or_blocking_records", sql)
        self.assertIn("update_state", sql)
        self.assertIn("LEFT JOIN expectation_summary ON TRUE", sql)

    def test_operational_queries_are_read_only_and_contain_no_identity(self) -> None:
        sql = "\n".join(path.read_text() for path in OPERATIONS.glob("*.sql"))
        forbidden_statements = re.compile(
            r"(?im)^\s*(INSERT|UPDATE|DELETE|MERGE|CREATE|ALTER|DROP|TRUNCATE|COPY|GRANT|REVOKE)\b"
        )

        self.assertIsNone(forbidden_statements.search(sql))
        self.assertNotIn("@", sql)
        self.assertNotRegex(sql, r"\b[0-9]{16}\b")


if __name__ == "__main__":
    unittest.main()
