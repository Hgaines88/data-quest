"""Tests for verified streaming into run-scoped raw-ingestion staging."""

from email.message import Message
import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
import unittest
from unittest.mock import Mock, patch

from data_quest.ingestion.download import (
    DownloadIntegrityError,
    DownloadedFile,
    SourceRedirectError,
    build_versioned_landed_path,
    download_to_staging,
    promote_verified_file,
    verify_file_evidence,
)
from data_quest.ingestion.discovery import SourcePolicyError


SOURCE_URL = "https://download.bls.gov/pub/time.series/pr/pr.series"
USER_AGENT = "data-quest-test/0.1 (contact: owner@example.org)"


class FakeResponse:
    """Small urlopen-compatible response that supports chunked reads."""

    def __init__(
        self,
        body: bytes,
        *,
        response_url: str = SOURCE_URL,
        content_length: int | None = None,
        etag: str | None = '"abc123"',
        last_modified: str | None = "Fri, 17 Oct 2026 12:00:00 GMT",
    ) -> None:
        self._body = BytesIO(body)
        self._response_url = response_url
        self.headers = Message()
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)
        if etag is not None:
            self.headers["ETag"] = etag
        if last_modified is not None:
            self.headers["Last-Modified"] = last_modified

    def read(self, size: int = -1) -> bytes:
        return self._body.read(size)

    def geturl(self) -> str:
        return self._response_url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self._body.close()


class DownloadToStagingTests(unittest.TestCase):
    def test_contact_email_is_required_by_default_but_can_be_provider_specific(self) -> None:
        public_user_agent = "rearc-data-quest/0.1 (Data USA population ingestion)"
        opener = Mock(return_value=FakeResponse(b"{}", content_length=2))

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "response.partial"
            with self.assertRaisesRegex(ValueError, "contact email"):
                download_to_staging(
                    SOURCE_URL,
                    public_user_agent,
                    destination,
                    opener=opener,
                )

            result = download_to_staging(
                SOURCE_URL,
                public_user_agent,
                destination,
                require_contact_email=False,
                opener=opener,
            )

        self.assertEqual(result.content_size_bytes, 2)
        self.assertEqual(opener.call_count, 1)

    def test_query_urls_require_explicit_opt_in(self) -> None:
        api_url = "https://api.example.org/data.json?measure=Population"
        opener = Mock(
            return_value=FakeResponse(
                b"{}",
                response_url=api_url,
                content_length=2,
            )
        )

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "response.partial"

            with self.assertRaisesRegex(ValueError, "disallowed query"):
                download_to_staging(
                    api_url,
                    USER_AGENT,
                    destination,
                    opener=opener,
                )

            result = download_to_staging(
                api_url,
                USER_AGENT,
                destination,
                allow_query=True,
                opener=opener,
            )

        self.assertEqual(result.source_url, api_url)
        self.assertEqual(opener.call_count, 1)

    def test_streams_exact_bytes_and_returns_auditable_metadata(self) -> None:
        body = b"series_id\tyear\tvalue\nPRS1\t2025\t1.0\n"
        opener = Mock(return_value=FakeResponse(body, content_length=len(body)))

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "run" / "pr.series.partial"
            result = download_to_staging(
                SOURCE_URL,
                USER_AGENT,
                destination,
                timeout_seconds=12.5,
                chunk_size=7,
                opener=opener,
            )

            self.assertEqual(destination.read_bytes(), body)

        self.assertEqual(
            result,
            DownloadedFile(
                source_url=SOURCE_URL,
                staging_path=str(destination),
                source_etag='"abc123"',
                source_last_modified="Fri, 17 Oct 2026 12:00:00 GMT",
                source_content_length=len(body),
                content_size_bytes=len(body),
                content_sha256=hashlib.sha256(body).hexdigest(),
            ),
        )
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, SOURCE_URL)
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(opener.call_args.kwargs["timeout"], 12.5)

    def test_retries_a_truncated_response_and_replaces_partial_bytes(self) -> None:
        truncated = b"short"
        complete = b"complete-body"
        opener = Mock(
            side_effect=[
                FakeResponse(truncated, content_length=len(truncated) + 3),
                FakeResponse(complete, content_length=len(complete)),
            ]
        )
        sleeper = Mock()

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "file.partial"
            result = download_to_staging(
                SOURCE_URL,
                USER_AGENT,
                destination,
                max_attempts=2,
                backoff_seconds=0.25,
                opener=opener,
                sleeper=sleeper,
            )

            self.assertEqual(destination.read_bytes(), complete)

        self.assertEqual(result.content_size_bytes, len(complete))
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(0.25)

    def test_removes_partial_file_when_all_attempts_fail_integrity(self) -> None:
        opener = Mock(
            side_effect=[
                FakeResponse(b"short", content_length=20),
                FakeResponse(b"short", content_length=20),
            ]
        )

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "file.partial"

            with self.assertRaisesRegex(DownloadIntegrityError, "Content-Length"):
                download_to_staging(
                    SOURCE_URL,
                    USER_AGENT,
                    destination,
                    max_attempts=2,
                    backoff_seconds=0,
                    opener=opener,
                )

            self.assertFalse(destination.exists())

    def test_policy_error_is_not_retried_and_leaves_no_file(self) -> None:
        opener = Mock(
            side_effect=HTTPError(SOURCE_URL, 403, "Forbidden", Message(), None)
        )

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "file.partial"

            with self.assertRaisesRegex(SourcePolicyError, "BLS access policy"):
                download_to_staging(
                    SOURCE_URL,
                    USER_AGENT,
                    destination,
                    max_attempts=3,
                    opener=opener,
                )

            self.assertFalse(destination.exists())

        self.assertEqual(opener.call_count, 1)

    def test_rejects_cross_origin_redirect_before_writing(self) -> None:
        opener = Mock(
            return_value=FakeResponse(
                b"unexpected",
                response_url="https://example.org/pr.series",
                content_length=10,
            )
        )

        with TemporaryDirectory() as directory:
            destination = Path(directory) / "file.partial"

            with self.assertRaisesRegex(SourceRedirectError, "origin"):
                download_to_staging(
                    SOURCE_URL,
                    USER_AGENT,
                    destination,
                    opener=opener,
                )

            self.assertFalse(destination.exists())


class VersionedLandingTests(unittest.TestCase):
    def test_builds_a_deterministic_content_addressed_volume_path(self) -> None:
        digest = "a" * 64

        result = build_versioned_landed_path(
            "/Volumes/workspace/rearc_data_quest/raw_landing/bls/productivity",
            "pr.series",
            digest,
        )

        self.assertEqual(
            result,
            "/Volumes/workspace/rearc_data_quest/raw_landing/bls/productivity/"
            f"objects/{digest}/pr.series",
        )

    def test_rejects_unsafe_relative_source_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "relative_path"):
            build_versioned_landed_path(
                "/Volumes/workspace/rearc_data_quest/raw_landing/bls/productivity",
                "../outside",
                "a" * 64,
            )

    def test_promotes_new_file_without_overwriting_existing_version(self) -> None:
        body = b"verified bytes"
        digest = hashlib.sha256(body).hexdigest()

        with TemporaryDirectory() as directory:
            staging = Path(directory) / "staging" / "file.partial"
            final = Path(directory) / "objects" / digest / "file"
            staging.parent.mkdir(parents=True)
            staging.write_bytes(body)

            promoted = promote_verified_file(
                staging,
                final,
                expected_size=len(body),
                expected_sha256=digest,
            )

            self.assertTrue(promoted)
            self.assertFalse(staging.exists())
            self.assertEqual(final.read_bytes(), body)

            second_staging = Path(directory) / "staging" / "again.partial"
            second_staging.write_bytes(body)
            promoted_again = promote_verified_file(
                second_staging,
                final,
                expected_size=len(body),
                expected_sha256=digest,
            )

            self.assertFalse(promoted_again)
            self.assertFalse(second_staging.exists())
            self.assertEqual(final.read_bytes(), body)

    def test_verifies_the_landed_object_after_promotion(self) -> None:
        body = b"verified after promotion"
        digest = hashlib.sha256(body).hexdigest()

        with TemporaryDirectory() as directory:
            staging = Path(directory) / "staging" / "source.partial"
            landed = Path(directory) / "objects" / digest / "source"
            staging.parent.mkdir(parents=True)
            staging.write_bytes(body)

            with patch(
                "data_quest.ingestion.download._assert_file_evidence"
            ) as verifier:
                promoted = promote_verified_file(
                    staging,
                    landed,
                    expected_size=len(body),
                    expected_sha256=digest,
                )

            self.assertTrue(promoted)
            self.assertEqual(verifier.call_count, 2)
            self.assertEqual(
                verifier.call_args_list[-1].kwargs["description"],
                "promoted landed",
            )

    def test_refuses_existing_content_address_with_different_bytes(self) -> None:
        expected = b"expected"
        unexpected = b"different"
        digest = hashlib.sha256(expected).hexdigest()

        with TemporaryDirectory() as directory:
            staging = Path(directory) / "staging.partial"
            final = Path(directory) / "objects" / digest / "file"
            staging.write_bytes(expected)
            final.parent.mkdir(parents=True)
            final.write_bytes(unexpected)

            with self.assertRaisesRegex(DownloadIntegrityError, "existing"):
                promote_verified_file(
                    staging,
                    final,
                    expected_size=len(expected),
                    expected_sha256=digest,
                )

            self.assertTrue(staging.exists())
            self.assertEqual(final.read_bytes(), unexpected)

    def test_verifies_landed_bytes_against_manifest_evidence(self) -> None:
        body = b"landed and committed"
        digest = hashlib.sha256(body).hexdigest()

        with TemporaryDirectory() as directory:
            landed = Path(directory) / "landed"
            landed.write_bytes(body)

            verify_file_evidence(
                landed,
                expected_size=len(body),
                expected_sha256=digest,
            )

            with self.assertRaisesRegex(DownloadIntegrityError, "landed"):
                verify_file_evidence(
                    landed,
                    expected_size=len(body) + 1,
                    expected_sha256=digest,
                )


if __name__ == "__main__":
    unittest.main()
