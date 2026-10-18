"""Whole-run tests for safe BLS staging, promotion, and publication order."""

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from data_quest.ingestion.discovery import SourceFile, SourceRequestError
from data_quest.ingestion.download import DownloadedFile
from data_quest.ingestion.download import DownloadIntegrityError
from data_quest.ingestion.landing import (
    BLS_REQUIRED_SOURCE_NAMES,
    execute_landing_plan,
    prepare_bls_landing,
    prepare_source_landing,
)
from data_quest.ingestion.manifest import (
    ChangeType,
    ManifestEntry,
    ManifestStatus,
    ObservedFile,
)


USER_AGENT = "data-quest-test/0.1 (contact: owner@example.org)"
VOLUME_ROOT = "/Volumes/workspace/rearc_data_quest/raw_landing/bls/productivity"
RUN_ID = "20261017T160000Z-test"
RUN_TIME = datetime(2026, 10, 17, 16, 0, tzinfo=timezone.utc)


def source(name: str) -> SourceFile:
    return SourceFile(
        name=name,
        url=f"https://download.bls.gov/pub/time.series/pr/{name}",
    )


def current_entry(name: str, body: bytes) -> ManifestEntry:
    digest = hashlib.sha256(body).hexdigest()
    return ManifestEntry.from_observation(
        ObservedFile(
            source_url=source(name).url,
            relative_path=name,
            landed_path=f"{VOLUME_ROOT}/objects/{digest}/{name}",
            source_etag='"old"',
            source_last_modified="Thu, 16 Oct 2026 12:00:00 GMT",
            source_content_length=len(body),
            content_size_bytes=len(body),
            content_sha256=digest,
        ),
        ingested_at_utc=datetime(2026, 10, 16, tzinfo=timezone.utc),
        run_id="20261016T000000Z-old",
    )


def downloader_for(
    bodies: dict[str, bytes],
    *,
    staging_directory: Path,
):
    """Return a deterministic fake downloader with real local staged bytes."""

    def download(
        source_url: str,
        user_agent: str,
        destination: str | Path,
        **_: object,
    ) -> DownloadedFile:
        name = source_url.rsplit("/", 1)[-1]
        body = bodies[name]
        local_path = staging_directory / f"{name}.partial"
        local_path.write_bytes(body)
        return DownloadedFile(
            source_url=source_url,
            staging_path=str(local_path),
            source_etag=f'"{name}-etag"',
            source_last_modified="Fri, 17 Oct 2026 12:00:00 GMT",
            source_content_length=len(body),
            content_size_bytes=len(body),
            content_sha256=hashlib.sha256(body).hexdigest(),
        )

    return download


class PrepareBlsLandingTests(unittest.TestCase):
    def test_stages_complete_inventory_and_plans_all_change_types(self) -> None:
        bodies = {
            "changed": b"new changed bytes",
            "new": b"new file bytes",
            "same": b"same bytes",
        }

        with TemporaryDirectory() as directory:
            plan = prepare_source_landing(
                [source("same"), source("new"), source("changed")],
                [
                    current_entry("changed", b"old changed bytes"),
                    current_entry("removed", b"removed bytes"),
                    current_entry("same", bodies["same"]),
                ],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for(
                    bodies,
                    staging_directory=Path(directory),
                ),
                cleanup_tree=Mock(),
            )

        self.assertEqual(
            [(change.relative_path, change.change_type) for change in plan.changes],
            [
                ("changed", ChangeType.CHANGED),
                ("new", ChangeType.NEW),
                ("removed", ChangeType.REMOVED),
                ("same", ChangeType.UNCHANGED),
            ],
        )
        self.assertEqual(
            [staged.relative_path for staged in plan.staged_files],
            ["changed", "new", "same"],
        )

    def test_failed_download_cleans_the_run_and_produces_no_plan(self) -> None:
        cleanup = Mock()
        successful_body = b"complete"

        def failing_downloader(
            source_url: str,
            user_agent: str,
            destination: str | Path,
            **_: object,
        ) -> DownloadedFile:
            if source_url.endswith("second"):
                raise SourceRequestError("controlled download failure")
            return DownloadedFile(
                source_url=source_url,
                staging_path=str(destination),
                source_etag=None,
                source_last_modified=None,
                source_content_length=len(successful_body),
                content_size_bytes=len(successful_body),
                content_sha256=hashlib.sha256(successful_body).hexdigest(),
            )

        with self.assertRaisesRegex(SourceRequestError, "controlled"):
            prepare_source_landing(
                [source("first"), source("second")],
                [],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=failing_downloader,
                cleanup_tree=cleanup,
            )

        cleanup.assert_called_once_with(f"{VOLUME_ROOT}/_staging/{RUN_ID}")

    def test_duplicate_source_names_fail_before_download(self) -> None:
        downloader = Mock()

        with self.assertRaisesRegex(ValueError, "duplicate source relative_path"):
            prepare_source_landing(
                [source("same"), source("same")],
                [],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader,
                cleanup_tree=Mock(),
            )

        downloader.assert_not_called()


class PrepareBlsInventorySafetyTests(unittest.TestCase):
    def test_missing_required_anchor_fails_before_download(self) -> None:
        downloader = Mock()

        with self.assertRaisesRegex(ValueError, "required BLS source"):
            prepare_bls_landing(
                [source("pr.series")],
                [],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader,
                cleanup_tree=Mock(),
            )

        downloader.assert_not_called()

    def test_removal_requires_second_inventory_confirmation(self) -> None:
        names = [*BLS_REQUIRED_SOURCE_NAMES, "pr.measure"]
        current = [current_entry(name, name.encode()) for name in names]

        with self.assertRaisesRegex(ValueError, "confirmation"):
            prepare_bls_landing(
                [source(name) for name in BLS_REQUIRED_SOURCE_NAMES],
                current,
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=Mock(),
                cleanup_tree=Mock(),
            )

    def test_disagreeing_removal_inventories_fail_before_download(self) -> None:
        current_names = [*BLS_REQUIRED_SOURCE_NAMES, "pr.measure", "pr.sector"]
        current = [current_entry(name, name.encode()) for name in current_names]
        first = [source(name) for name in [*BLS_REQUIRED_SOURCE_NAMES, "pr.measure"]]
        second = [source(name) for name in [*BLS_REQUIRED_SOURCE_NAMES, "pr.sector"]]
        downloader = Mock()

        with self.assertRaisesRegex(ValueError, "inventories do not match"):
            prepare_bls_landing(
                first,
                current,
                confirmed_source_files=second,
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader,
                cleanup_tree=Mock(),
            )

        downloader.assert_not_called()

    def test_partial_two_of_twelve_inventory_cannot_publish_removals(self) -> None:
        current_names = [
            *BLS_REQUIRED_SOURCE_NAMES,
            *(f"pr.lookup.{index}" for index in range(10)),
        ]
        current = [current_entry(name, name.encode()) for name in current_names]
        partial = [source(name) for name in BLS_REQUIRED_SOURCE_NAMES]
        downloader = Mock()

        with self.assertRaisesRegex(ValueError, "mass removal"):
            prepare_bls_landing(
                partial,
                current,
                confirmed_source_files=partial,
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader,
                cleanup_tree=Mock(),
            )

        downloader.assert_not_called()

    def test_explicit_override_allows_confirmed_mass_removal(self) -> None:
        current_names = [
            *BLS_REQUIRED_SOURCE_NAMES,
            *(f"pr.lookup.{index}" for index in range(10)),
        ]
        bodies = {name: name.encode() for name in BLS_REQUIRED_SOURCE_NAMES}
        current = [current_entry(name, name.encode()) for name in current_names]
        confirmed = [source(name) for name in BLS_REQUIRED_SOURCE_NAMES]

        with TemporaryDirectory() as directory:
            plan = prepare_bls_landing(
                confirmed,
                current,
                confirmed_source_files=confirmed,
                allow_mass_removal=True,
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for(
                    bodies,
                    staging_directory=Path(directory),
                ),
                cleanup_tree=Mock(),
            )

        removed = [
            change.relative_path
            for change in plan.changes
            if change.change_type is ChangeType.REMOVED
        ]
        self.assertEqual(len(removed), 10)

    def test_confirmed_single_removal_still_produces_tombstone(self) -> None:
        bodies = {name: name.encode() for name in BLS_REQUIRED_SOURCE_NAMES}
        current = [
            *(current_entry(name, body) for name, body in bodies.items()),
            current_entry("pr.retired", b"retired"),
        ]
        confirmed = [source(name) for name in BLS_REQUIRED_SOURCE_NAMES]

        with TemporaryDirectory() as directory:
            plan = prepare_bls_landing(
                confirmed,
                current,
                confirmed_source_files=confirmed,
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for(
                    bodies,
                    staging_directory=Path(directory),
                ),
                cleanup_tree=Mock(),
            )

        removed = [
            change.relative_path
            for change in plan.changes
            if change.change_type is ChangeType.REMOVED
        ]
        self.assertEqual(removed, ["pr.retired"])


class ExecuteLandingPlanTests(unittest.TestCase):
    def test_publisher_failure_leaves_reusable_unreferenced_object(self) -> None:
        body = b"new immutable bytes"
        digest = hashlib.sha256(body).hexdigest()
        committed: list[ManifestEntry] = []

        with TemporaryDirectory() as directory:
            root = Path(directory)
            landed = root / "objects" / digest / "new"
            first_staging = root / "first"
            second_staging = root / "second"
            first_staging.mkdir()
            second_staging.mkdir()

            def local_landed_path(
                volume_root: str,
                relative_path: str,
                content_sha256: str,
            ) -> str:
                return str(root / "objects" / content_sha256 / relative_path)

            with (
                patch(
                    "data_quest.ingestion.landing.build_versioned_landed_path",
                    side_effect=local_landed_path,
                ),
                patch("data_quest.ingestion.manifest._validate_landed_path"),
            ):
                first_plan = prepare_source_landing(
                    [source("new")],
                    committed,
                    user_agent=USER_AGENT,
                    volume_source_root=VOLUME_ROOT,
                    run_id="20261018T060000Z-first",
                    ingested_at_utc=RUN_TIME,
                    downloader=downloader_for(
                        {"new": body}, staging_directory=first_staging
                    ),
                    cleanup_tree=Mock(),
                )

                with self.assertRaisesRegex(RuntimeError, "manifest unavailable"):
                    execute_landing_plan(
                        first_plan,
                        publisher=Mock(
                            side_effect=RuntimeError("manifest unavailable")
                        ),
                        cleanup_tree=Mock(),
                    )

                self.assertEqual(landed.read_bytes(), body)
                self.assertEqual(committed, [])

                second_plan = prepare_source_landing(
                    [source("new")],
                    committed,
                    user_agent=USER_AGENT,
                    volume_source_root=VOLUME_ROOT,
                    run_id="20261018T060100Z-second",
                    ingested_at_utc=RUN_TIME,
                    downloader=downloader_for(
                        {"new": body}, staging_directory=second_staging
                    ),
                    cleanup_tree=Mock(),
                )
                result = execute_landing_plan(
                    second_plan,
                    publisher=lambda entries: committed.extend(entries),
                    cleanup_tree=Mock(),
                )

            self.assertEqual(landed.read_bytes(), body)

        self.assertEqual([entry.relative_path for entry in committed], ["new"])
        self.assertEqual(result.promoted_count, 0)
        self.assertEqual(result.reused_version_count, 1)
        self.assertEqual(result.published_transition_count, 1)

    def test_retained_removal_tombstone_needs_no_staged_bytes(self) -> None:
        new_body = b"new"
        tombstone = current_entry("retired", b"retired").as_removed(
            removed_at_utc=RUN_TIME,
            run_id=RUN_ID,
        )
        promoter = Mock(return_value=True)
        publisher = Mock()

        with TemporaryDirectory() as directory:
            plan = prepare_source_landing(
                [source("new")],
                [tombstone],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id="20261018T010000Z-test",
                ingested_at_utc=datetime(2026, 10, 18, 1, tzinfo=timezone.utc),
                downloader=downloader_for(
                    {"new": new_body}, staging_directory=Path(directory)
                ),
                cleanup_tree=Mock(),
            )

            result = execute_landing_plan(
                plan,
                promoter=promoter,
                publisher=publisher,
                cleanup_tree=Mock(),
            )

        promoter.assert_called_once()
        publisher.assert_called_once()
        published = publisher.call_args.args[0]
        self.assertEqual([entry.relative_path for entry in published], ["new"])
        retained = next(
            change
            for change in plan.changes
            if change.relative_path == "retired"
        )
        self.assertIs(retained.change_type, ChangeType.UNCHANGED)
        self.assertIs(retained.after.status, ManifestStatus.REMOVED)
        self.assertEqual(result.unchanged_count, 1)

    def test_missing_unchanged_object_is_recovered_without_publication(self) -> None:
        body = b"same"
        publisher = Mock()

        with TemporaryDirectory() as directory:
            root = Path(directory)
            landed = root / "objects" / hashlib.sha256(body).hexdigest() / "same"
            with patch("data_quest.ingestion.manifest._validate_landed_path"):
                current = replace(
                    current_entry("same", body), landed_path=str(landed)
                )
            plan = prepare_source_landing(
                [source("same")],
                [current],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for({"same": body}, staging_directory=root),
                cleanup_tree=Mock(),
            )

            result = execute_landing_plan(
                plan,
                publisher=publisher,
                cleanup_tree=Mock(),
            )

            self.assertEqual(landed.read_bytes(), body)

        publisher.assert_not_called()
        self.assertEqual(result.recovered_count, 1)
        self.assertEqual(result.promoted_count, 0)

    def test_valid_unchanged_object_is_verified_without_rewrite(self) -> None:
        body = b"same"
        publisher = Mock()

        with TemporaryDirectory() as directory:
            root = Path(directory)
            landed = root / "objects" / hashlib.sha256(body).hexdigest() / "same"
            landed.parent.mkdir(parents=True)
            landed.write_bytes(body)
            with patch("data_quest.ingestion.manifest._validate_landed_path"):
                current = replace(
                    current_entry("same", body), landed_path=str(landed)
                )
            plan = prepare_source_landing(
                [source("same")],
                [current],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for({"same": body}, staging_directory=root),
                cleanup_tree=Mock(),
            )

            result = execute_landing_plan(
                plan,
                publisher=publisher,
                cleanup_tree=Mock(),
            )

            self.assertEqual(landed.read_bytes(), body)

        publisher.assert_not_called()
        self.assertEqual(result.recovered_count, 0)
        self.assertEqual(result.reused_version_count, 0)

    def test_corrupt_unchanged_object_fails_without_overwrite(self) -> None:
        body = b"same"
        corrupt = b"corrupt"
        publisher = Mock()

        with TemporaryDirectory() as directory:
            root = Path(directory)
            landed = root / "objects" / hashlib.sha256(body).hexdigest() / "same"
            landed.parent.mkdir(parents=True)
            landed.write_bytes(corrupt)
            with patch("data_quest.ingestion.manifest._validate_landed_path"):
                current = replace(
                    current_entry("same", body), landed_path=str(landed)
                )
            plan = prepare_source_landing(
                [source("same")],
                [current],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for({"same": body}, staging_directory=root),
                cleanup_tree=Mock(),
            )

            with self.assertRaises(DownloadIntegrityError):
                execute_landing_plan(
                    plan,
                    publisher=publisher,
                    cleanup_tree=Mock(),
                )

            self.assertEqual(landed.read_bytes(), corrupt)

        publisher.assert_not_called()

    def test_verifies_all_objects_before_publishing_transitions(self) -> None:
        bodies = {"new": b"new", "same": b"same"}
        events: list[str] = []

        with TemporaryDirectory() as directory:
            plan = prepare_source_landing(
                [source("new"), source("same")],
                [current_entry("same", bodies["same"])],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for(
                    bodies,
                    staging_directory=Path(directory),
                ),
                cleanup_tree=Mock(),
            )

            def promoter(*args: object, **kwargs: object) -> bool:
                events.append(f"promote:{Path(str(args[0])).name}")
                return Path(str(args[0])).name == "new.partial"

            published: list[ManifestEntry] = []

            def publisher(entries: list[ManifestEntry]) -> None:
                events.append("publish")
                published.extend(entries)

            result = execute_landing_plan(
                plan,
                promoter=promoter,
                publisher=publisher,
                cleanup_tree=lambda path: events.append(f"cleanup:{path}"),
            )

        self.assertEqual(events[0], "promote:new.partial")
        self.assertEqual(events[1], "promote:same.partial")
        self.assertEqual(events[2], "publish")
        self.assertTrue(events[3].startswith("cleanup:"))
        self.assertEqual([entry.relative_path for entry in published], ["new"])
        self.assertEqual(result.promoted_count, 1)
        self.assertEqual(result.unchanged_count, 1)

    def test_promotion_failure_prevents_manifest_publication(self) -> None:
        bodies = {"new": b"new"}
        cleanup = Mock()
        publisher = Mock()

        with TemporaryDirectory() as directory:
            plan = prepare_source_landing(
                [source("new")],
                [],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for(
                    bodies,
                    staging_directory=Path(directory),
                ),
                cleanup_tree=Mock(),
            )

            with self.assertRaisesRegex(RuntimeError, "controlled promotion"):
                execute_landing_plan(
                    plan,
                    promoter=Mock(side_effect=RuntimeError("controlled promotion")),
                    publisher=publisher,
                    cleanup_tree=cleanup,
                )

        publisher.assert_not_called()
        cleanup.assert_called_once_with(plan.staging_root)

    def test_unchanged_run_verifies_but_does_not_publish_or_promote(self) -> None:
        bodies = {"same": b"same"}
        promoter = Mock(return_value=False)
        publisher = Mock()
        cleanup = Mock()

        with TemporaryDirectory() as directory:
            plan = prepare_source_landing(
                [source("same")],
                [current_entry("same", bodies["same"])],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id=RUN_ID,
                ingested_at_utc=RUN_TIME,
                downloader=downloader_for(
                    bodies,
                    staging_directory=Path(directory),
                ),
                cleanup_tree=Mock(),
            )

            result = execute_landing_plan(
                plan,
                promoter=promoter,
                publisher=publisher,
                cleanup_tree=cleanup,
            )

        promoter.assert_called_once()
        publisher.assert_not_called()
        cleanup.assert_called_once_with(plan.staging_root)
        self.assertEqual(result.unchanged_count, 1)
        self.assertEqual(result.recovered_count, 0)
        self.assertEqual(result.promoted_count, 0)


if __name__ == "__main__":
    unittest.main()
