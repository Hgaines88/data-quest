"""Tests for privacy-safe ingestion observability records."""

from datetime import datetime, timedelta, timezone
import unittest

from data_quest.ingestion.landing import LandingExecutionResult
from data_quest.ingestion.observability import (
    failed_run_audit,
    successful_run_audit,
)


STARTED = datetime(2026, 10, 20, tzinfo=timezone.utc)
COMPLETED = STARTED + timedelta(seconds=5)


class SourceRequestError(RuntimeError):
    pass


class ObservabilityRecordTests(unittest.TestCase):
    def test_success_maps_downloaded_and_skipped_counts(self) -> None:
        result = LandingExecutionResult(
            discovered_count=11,
            promoted_count=1,
            recovered_count=0,
            reused_version_count=0,
            new_count=1,
            changed_count=2,
            unchanged_count=8,
            removed_count=1,
            published_transition_count=4,
        )

        audit = successful_run_audit(
            source="bls",
            run_id="20261020T000000Z-test",
            started_at_utc=STARTED,
            completed_at_utc=COMPLETED,
            result=result,
        )

        self.assertEqual(audit.downloaded_count, 11)
        self.assertEqual(audit.skipped_count, 8)
        self.assertEqual(audit.failed_file_count, 0)
        self.assertEqual(audit.outcome, "SUCCEEDED")

    def test_failure_persists_category_but_never_exception_text(self) -> None:
        secret_message = "token=secret person@example.org"

        audit = failed_run_audit(
            source="bls",
            run_id="20261020T000000Z-test",
            started_at_utc=STARTED,
            completed_at_utc=COMPLETED,
            failure_stage="DOWNLOAD_AND_VALIDATE",
            error=SourceRequestError(secret_message),
            discovered_count=12,
            failed_file_count=1,
        )

        self.assertEqual(audit.error_category, "SOURCE_UNAVAILABLE")
        self.assertNotIn(secret_message, repr(audit))
        self.assertNotIn("@", repr(audit))
        self.assertEqual(audit.published_transition_count, 0)

    def test_rejects_unsafe_operational_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "source"):
            failed_run_audit(
                source="bls; DROP TABLE audit",
                run_id="20261020T000000Z-test",
                started_at_utc=STARTED,
                completed_at_utc=COMPLETED,
                failure_stage="DISCOVERY",
                error=RuntimeError("failure"),
            )

    def test_rejects_naive_operational_timestamps(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware UTC"):
            failed_run_audit(
                source="bls",
                run_id="20261020T000000Z-test",
                started_at_utc=STARTED.replace(tzinfo=None),
                completed_at_utc=COMPLETED.replace(tzinfo=None),
                failure_stage="DISCOVERY",
                error=RuntimeError("failure"),
            )

    def test_rejects_success_counts_that_do_not_reconcile(self) -> None:
        result = LandingExecutionResult(
            discovered_count=2,
            promoted_count=0,
            recovered_count=0,
            reused_version_count=0,
            new_count=0,
            changed_count=0,
            unchanged_count=1,
            removed_count=0,
            published_transition_count=1,
        )

        with self.assertRaisesRegex(ValueError, "transition counts must reconcile"):
            successful_run_audit(
                source="bls",
                run_id="20261020T000000Z-test",
                started_at_utc=STARTED,
                completed_at_utc=COMPLETED,
                result=result,
            )


if __name__ == "__main__":
    unittest.main()
