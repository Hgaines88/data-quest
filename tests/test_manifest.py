"""Contract tests for deterministic ingestion-manifest planning."""

from datetime import datetime, timezone
import unittest

from data_quest.ingestion.manifest import (
    ChangeType,
    IncompleteRunError,
    ManifestContractError,
    ManifestEntry,
    ManifestStatus,
    ObservedFile,
    plan_manifest_changes,
)


INGESTED_AT = datetime(2026, 10, 17, 14, 30, tzinfo=timezone.utc)
EARLIER = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
RUN_ID = "20261017T143000Z-7f34a1"
EARLIER_RUN_ID = "20261016T120000Z-498c2e"


def observed(
    relative_path: str,
    digest_character: str,
    *,
    size: int = 100,
    etag: str | None = None,
) -> ObservedFile:
    """Build one valid observed file for a focused test."""

    return ObservedFile(
        source_url=f"https://download.bls.gov/pub/time.series/pr/{relative_path}",
        relative_path=relative_path,
        landed_path=(
            f"/Volumes/test/rearc_data_quest/raw_landing/objects/"
            f"{digest_character * 12}/{relative_path}"
        ),
        source_etag=etag,
        source_last_modified="Fri, 17 Oct 2026 12:00:00 GMT",
        source_content_length=size,
        content_size_bytes=size,
        content_sha256=digest_character * 64,
    )


def active_entry(
    relative_path: str,
    digest_character: str,
    *,
    size: int = 100,
) -> ManifestEntry:
    """Build one current active manifest entry for a focused test."""

    return ManifestEntry.from_observation(
        observed(relative_path, digest_character, size=size),
        ingested_at_utc=EARLIER,
        run_id=EARLIER_RUN_ID,
    )


class PlanManifestChangesTests(unittest.TestCase):
    def test_classifies_new_changed_unchanged_and_removed_files(self) -> None:
        current = [
            active_entry("pr.changed", "a"),
            active_entry("pr.removed", "b"),
            active_entry("pr.unchanged", "c"),
        ]
        inventory = [
            observed("pr.new", "d"),
            observed("pr.changed", "e"),
            observed("pr.unchanged", "c", etag="new-advisory-etag"),
        ]

        changes = plan_manifest_changes(
            inventory,
            current,
            ingested_at_utc=INGESTED_AT,
            run_id=RUN_ID,
        )

        self.assertEqual(
            [(change.relative_path, change.change_type) for change in changes],
            [
                ("pr.changed", ChangeType.CHANGED),
                ("pr.new", ChangeType.NEW),
                ("pr.removed", ChangeType.REMOVED),
                ("pr.unchanged", ChangeType.UNCHANGED),
            ],
        )
        unchanged = changes[-1]
        self.assertIs(unchanged.after, current[-1])
        removed = changes[2]
        self.assertEqual(removed.after.status, ManifestStatus.REMOVED)
        self.assertEqual(removed.after.ingested_at_utc, INGESTED_AT)
        self.assertEqual(removed.after.run_id, RUN_ID)

    def test_same_digest_but_different_size_is_changed(self) -> None:
        changes = plan_manifest_changes(
            [observed("pr.series", "a", size=101)],
            [active_entry("pr.series", "a", size=100)],
            ingested_at_utc=INGESTED_AT,
            run_id=RUN_ID,
        )

        self.assertEqual(changes[0].change_type, ChangeType.CHANGED)

    def test_reappearing_tombstoned_path_is_new(self) -> None:
        previous = active_entry("pr.series", "a")
        tombstone = previous.as_removed(
            removed_at_utc=EARLIER,
            run_id=EARLIER_RUN_ID,
        )

        changes = plan_manifest_changes(
            [observed("pr.series", "a")],
            [tombstone],
            ingested_at_utc=INGESTED_AT,
            run_id=RUN_ID,
        )

        self.assertEqual(changes[0].change_type, ChangeType.NEW)
        self.assertEqual(changes[0].after.status, ManifestStatus.ACTIVE)

    def test_empty_complete_inventory_marks_all_active_files_removed(self) -> None:
        changes = plan_manifest_changes(
            [],
            [active_entry("pr.series", "a")],
            ingested_at_utc=INGESTED_AT,
            run_id=RUN_ID,
        )

        self.assertEqual(changes[0].change_type, ChangeType.REMOVED)

    def test_incomplete_inventory_cannot_publish_a_plan(self) -> None:
        with self.assertRaisesRegex(IncompleteRunError, "inventory"):
            plan_manifest_changes(
                [],
                [active_entry("pr.series", "a")],
                ingested_at_utc=INGESTED_AT,
                run_id=RUN_ID,
                inventory_complete=False,
            )

    def test_partial_download_run_cannot_publish_a_plan(self) -> None:
        with self.assertRaisesRegex(IncompleteRunError, "download"):
            plan_manifest_changes(
                [observed("pr.series", "a")],
                [],
                ingested_at_utc=INGESTED_AT,
                run_id=RUN_ID,
                downloads_complete=False,
            )

    def test_duplicate_observed_paths_are_rejected(self) -> None:
        duplicate = observed("pr.series", "a")

        with self.assertRaisesRegex(ManifestContractError, "duplicate observed"):
            plan_manifest_changes(
                [duplicate, duplicate],
                [],
                ingested_at_utc=INGESTED_AT,
                run_id=RUN_ID,
            )

    def test_duplicate_current_paths_are_rejected(self) -> None:
        duplicate = active_entry("pr.series", "a")

        with self.assertRaisesRegex(ManifestContractError, "duplicate current"):
            plan_manifest_changes(
                [],
                [duplicate, duplicate],
                ingested_at_utc=INGESTED_AT,
                run_id=RUN_ID,
            )

    def test_result_order_does_not_depend_on_input_order(self) -> None:
        changes = plan_manifest_changes(
            [observed("z-file", "a"), observed("a-file", "b")],
            [],
            ingested_at_utc=INGESTED_AT,
            run_id=RUN_ID,
        )

        self.assertEqual(
            [change.relative_path for change in changes],
            ["a-file", "z-file"],
        )


class ManifestValidationTests(unittest.TestCase):
    def test_rejects_unsafe_relative_path(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "relative_path"):
            observed("../outside", "a")

    def test_rejects_noncanonical_relative_path(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "relative_path"):
            observed("folder//file", "a")

    def test_rejects_landed_path_outside_a_databricks_volume(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "landed_path"):
            ObservedFile(
                source_url="https://example.org/file",
                relative_path="file",
                landed_path="/tmp/file",
                source_etag=None,
                source_last_modified=None,
                source_content_length=1,
                content_size_bytes=1,
                content_sha256="a" * 64,
            )

    def test_rejects_invalid_sha256(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "SHA-256"):
            ObservedFile(
                source_url="https://example.org/file",
                relative_path="file",
                landed_path="/Volumes/test/schema/volume/objects/file",
                source_etag=None,
                source_last_modified=None,
                source_content_length=1,
                content_size_bytes=1,
                content_sha256="not-a-digest",
            )

    def test_rejects_naive_ingestion_timestamp(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "UTC-aware"):
            ManifestEntry.from_observation(
                observed("pr.series", "a"),
                ingested_at_utc=datetime(2026, 10, 17, 14, 30),
                run_id=RUN_ID,
            )

    def test_rejects_blank_run_id(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "run_id"):
            ManifestEntry.from_observation(
                observed("pr.series", "a"),
                ingested_at_utc=INGESTED_AT,
                run_id=" ",
            )

    def test_rejects_unsafe_run_id(self) -> None:
        with self.assertRaisesRegex(ManifestContractError, "run_id"):
            ManifestEntry.from_observation(
                observed("pr.series", "a"),
                ingested_at_utc=INGESTED_AT,
                run_id="run/id",
            )


if __name__ == "__main__":
    unittest.main()
