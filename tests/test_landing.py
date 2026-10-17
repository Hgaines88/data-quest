"""Whole-run tests for safe BLS staging, promotion, and publication order."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from data_quest.ingestion.discovery import SourceFile, SourceRequestError
from data_quest.ingestion.download import DownloadedFile
from data_quest.ingestion.landing import (
    execute_landing_plan,
    prepare_bls_landing,
)
from data_quest.ingestion.manifest import (
    ChangeType,
    ManifestEntry,
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
            plan = prepare_bls_landing(
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
            prepare_bls_landing(
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
            prepare_bls_landing(
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


class ExecuteLandingPlanTests(unittest.TestCase):
    def test_promotes_before_publishing_and_skips_unchanged_bytes(self) -> None:
        bodies = {"new": b"new", "same": b"same"}
        events: list[str] = []

        with TemporaryDirectory() as directory:
            plan = prepare_bls_landing(
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
                return True

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
        self.assertEqual(events[1], "publish")
        self.assertTrue(events[2].startswith("cleanup:"))
        self.assertEqual([entry.relative_path for entry in published], ["new"])
        self.assertEqual(result.promoted_count, 1)
        self.assertEqual(result.unchanged_count, 1)

    def test_promotion_failure_prevents_manifest_publication(self) -> None:
        bodies = {"new": b"new"}
        cleanup = Mock()
        publisher = Mock()

        with TemporaryDirectory() as directory:
            plan = prepare_bls_landing(
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

    def test_unchanged_run_does_not_publish_or_promote(self) -> None:
        bodies = {"same": b"same"}
        promoter = Mock()
        publisher = Mock()
        cleanup = Mock()

        with TemporaryDirectory() as directory:
            plan = prepare_bls_landing(
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

        promoter.assert_not_called()
        publisher.assert_not_called()
        cleanup.assert_called_once_with(plan.staging_root)
        self.assertEqual(result.unchanged_count, 1)


if __name__ == "__main__":
    unittest.main()
