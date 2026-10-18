"""Tests for validating and preparing the raw Data USA response."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from data_quest.ingestion import datausa

from data_quest.ingestion.datausa import (
    DATAUSA_USER_AGENT,
    PopulationResponseError,
    prepare_population_landing,
    validate_population_response,
)
from data_quest.ingestion.download import DownloadedFile
from data_quest.ingestion.manifest import ChangeType


ENDPOINT = (
    "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?"
    "cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&"
    "measures=Population"
)
USER_AGENT = "data-quest-test/0.1 (contact: owner@example.org)"
VOLUME_ROOT = "/Volumes/workspace/rearc_data_quest/raw_landing/datausa/population"
RUN_TIME = datetime(2026, 10, 17, 20, 0, tzinfo=timezone.utc)


def valid_payload() -> dict[str, object]:
    return {
        "annotations": {"source_name": "Census Bureau"},
        "page": {"limit": 0, "offset": 0, "total": 2},
        "columns": ["Nation ID", "Nation", "Year", "Population"],
        "data": [
            {
                "Nation ID": "01000US",
                "Nation": "United States",
                "Year": 2013,
                "Population": 316128839.0,
            },
            {
                "Nation ID": "01000US",
                "Nation": "United States",
                "Year": 2014,
                "Population": 318857056.0,
            },
        ],
    }


class PopulationValidationTests(unittest.TestCase):
    def test_rejects_nonstandard_json_numeric_constants(self) -> None:
        for constant in ["NaN", "Infinity", "-Infinity"]:
            with self.subTest(constant=constant):
                payload = valid_payload()
                payload["annotations"] = {"source_name": float(constant)}

                with TemporaryDirectory() as directory:
                    path = Path(directory) / "population.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")

                    with self.assertRaisesRegex(
                        PopulationResponseError, "valid UTF-8 JSON"
                    ):
                        validate_population_response(path)

    def test_datausa_user_agent_contains_no_contact_email(self) -> None:
        self.assertNotIn("@", DATAUSA_USER_AGENT)
        self.assertIn("Data USA", DATAUSA_USER_AGENT)

    def test_validates_expected_envelope_without_modifying_bytes(self) -> None:
        original = json.dumps(valid_payload(), indent=2).encode("utf-8") + b"\n"

        with TemporaryDirectory() as directory:
            path = Path(directory) / "population.json"
            path.write_bytes(original)

            result = validate_population_response(path)

            self.assertEqual(path.read_bytes(), original)

        self.assertEqual(result.record_count, 2)
        self.assertEqual(result.minimum_year, 2013)
        self.assertEqual(result.maximum_year, 2014)

    def test_rejects_invalid_utf8_or_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "population.json"
            path.write_bytes(b"\xffnot-json")

            with self.assertRaisesRegex(PopulationResponseError, "UTF-8 JSON"):
                validate_population_response(path)

    def test_rejects_missing_required_column(self) -> None:
        payload = valid_payload()
        payload["columns"] = ["Nation ID", "Nation", "Year"]

        with TemporaryDirectory() as directory:
            path = Path(directory) / "population.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(PopulationResponseError, "Population"):
                validate_population_response(path)

    def test_rejects_partial_page(self) -> None:
        payload = valid_payload()
        payload["page"] = {"limit": 1, "offset": 0, "total": 2}
        payload["data"] = payload["data"][:1]

        with TemporaryDirectory() as directory:
            path = Path(directory) / "population.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(PopulationResponseError, "complete"):
                validate_population_response(path)


class PopulationLandingPreparationTests(unittest.TestCase):
    def test_api_downloader_explicitly_disables_contact_email_requirement(self) -> None:
        downloaded = Mock(spec=DownloadedFile)
        with patch.object(datausa, "download_to_staging", return_value=downloaded) as call:
            result = datausa._download_api_response(
                ENDPOINT,
                DATAUSA_USER_AGENT,
                "/tmp/population.partial",
            )

        self.assertIs(result, downloaded)
        call.assert_called_once_with(
            ENDPOINT,
            DATAUSA_USER_AGENT,
            "/tmp/population.partial",
            allow_query=True,
            require_contact_email=False,
        )

    def test_stages_valid_raw_bytes_and_plans_one_new_object(self) -> None:
        body = json.dumps(valid_payload()).encode("utf-8")

        with TemporaryDirectory() as directory:
            staged = Path(directory) / "population.partial"

            def downloader(
                source_url: str,
                user_agent: str,
                destination: str | Path,
                **_: object,
            ) -> DownloadedFile:
                staged.write_bytes(body)
                return DownloadedFile(
                    source_url=source_url,
                    staging_path=str(staged),
                    source_etag='"population"',
                    source_last_modified=None,
                    source_content_length=len(body),
                    content_size_bytes=len(body),
                    content_sha256=hashlib.sha256(body).hexdigest(),
                )

            plan, summary = prepare_population_landing(
                ENDPOINT,
                [],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id="20261017T200000Z-test",
                ingested_at_utc=RUN_TIME,
                downloader=downloader,
                cleanup_tree=Mock(),
            )

        self.assertEqual(summary.record_count, 2)
        self.assertEqual(len(plan.changes), 1)
        self.assertIs(plan.changes[0].change_type, ChangeType.NEW)
        self.assertEqual(plan.changes[0].relative_path, "population.json")

    def test_invalid_response_cleans_staging_and_returns_no_plan(self) -> None:
        cleanup = Mock()

        with TemporaryDirectory() as directory:
            staged = Path(directory) / "population.partial"

            def downloader(
                source_url: str,
                user_agent: str,
                destination: str | Path,
                **_: object,
            ) -> DownloadedFile:
                body = b"not json"
                staged.write_bytes(body)
                return DownloadedFile(
                    source_url=source_url,
                    staging_path=str(staged),
                    source_etag=None,
                    source_last_modified=None,
                    source_content_length=len(body),
                    content_size_bytes=len(body),
                    content_sha256=hashlib.sha256(body).hexdigest(),
                )

            with self.assertRaisesRegex(PopulationResponseError, "UTF-8 JSON"):
                prepare_population_landing(
                    ENDPOINT,
                    [],
                    user_agent=USER_AGENT,
                    volume_source_root=VOLUME_ROOT,
                    run_id="20261017T200000Z-test",
                    ingested_at_utc=RUN_TIME,
                    downloader=downloader,
                    cleanup_tree=cleanup,
                )

        cleanup.assert_called_once_with(
            f"{VOLUME_ROOT}/_staging/20261017T200000Z-test"
        )

    def test_same_verified_response_is_unchanged_on_rerun(self) -> None:
        body = json.dumps(valid_payload()).encode("utf-8")

        with TemporaryDirectory() as directory:
            staged = Path(directory) / "population.partial"

            def downloader(
                source_url: str,
                user_agent: str,
                destination: str | Path,
                **_: object,
            ) -> DownloadedFile:
                staged.write_bytes(body)
                return DownloadedFile(
                    source_url=source_url,
                    staging_path=str(staged),
                    source_etag=None,
                    source_last_modified=None,
                    source_content_length=len(body),
                    content_size_bytes=len(body),
                    content_sha256=hashlib.sha256(body).hexdigest(),
                )

            first_plan, _ = prepare_population_landing(
                ENDPOINT,
                [],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id="20261017T200000Z-first",
                ingested_at_utc=RUN_TIME,
                downloader=downloader,
                cleanup_tree=Mock(),
            )
            second_plan, _ = prepare_population_landing(
                ENDPOINT,
                [first_plan.changes[0].after],
                user_agent=USER_AGENT,
                volume_source_root=VOLUME_ROOT,
                run_id="20261017T200100Z-second",
                ingested_at_utc=datetime(
                    2026, 10, 17, 20, 1, tzinfo=timezone.utc
                ),
                downloader=downloader,
                cleanup_tree=Mock(),
            )

        self.assertIs(second_plan.changes[0].change_type, ChangeType.UNCHANGED)



if __name__ == "__main__":
    unittest.main()
