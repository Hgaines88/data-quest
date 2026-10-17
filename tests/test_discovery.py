"""Tests for provider-directory link discovery."""

from email.message import Message
from io import BytesIO
from urllib.error import HTTPError, URLError
import unittest
from unittest.mock import Mock

from data_quest.ingestion.discovery import (
    DirectoryListingError,
    SourcePolicyError,
    SourceRequestError,
    SourceFile,
    discover_file_links,
    discover_source_files,
    fetch_directory_html,
)


BASE_URL = "https://download.bls.gov/pub/time.series/pr/"
USER_AGENT = "data-quest-test/0.1 (contact: owner@example.org)"


class FakeResponse:
    """Minimal context-managed response used to test without network access."""

    def __init__(self, body: bytes, charset: str = "utf-8") -> None:
        self._body = BytesIO(body)
        self.headers = Message()
        self.headers["Content-Type"] = f"text/html; charset={charset}"

    def read(self) -> bytes:
        return self._body.read()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self._body.close()


class DiscoverFileLinksTests(unittest.TestCase):
    def test_returns_only_files_in_the_exact_configured_directory(self) -> None:
        html = """
        <html><body>
          <a href="../">Parent directory</a>
          <a href="pr.series">Series</a>
          <a href="/pub/time.series/pr/pr.data.1.AllData">All data</a>
          <a href="https://download.bls.gov/pub/time.series/pr/pr.measure">Measure</a>
          <a href="subdirectory/ignored.txt">Nested file</a>
          <a href="/pub/time.series/other/unrelated.txt">Other BLS data</a>
          <a href="https://example.com/pub/time.series/pr/foreign.txt">External</a>
        </body></html>
        """

        result = discover_file_links(html, BASE_URL)

        self.assertEqual(
            result,
            [
                SourceFile(
                    "pr.data.1.AllData",
                    f"{BASE_URL}pr.data.1.AllData",
                ),
                SourceFile("pr.measure", f"{BASE_URL}pr.measure"),
                SourceFile("pr.series", f"{BASE_URL}pr.series"),
            ],
        )

    def test_deduplicates_and_sorts_links_deterministically(self) -> None:
        html = """
        <a href="pr.series">first appearance</a>
        <a href="pr.measure">measure</a>
        <a href="./pr.series">duplicate</a>
        """

        result = discover_file_links(html, BASE_URL)

        self.assertEqual([source.name for source in result], ["pr.measure", "pr.series"])

    def test_ignores_navigation_and_modified_resource_links(self) -> None:
        html = """
        <a href="?C=N;O=D">sort directory</a>
        <a href="#top">page fragment</a>
        <a href="child/">child directory</a>
        <a href="pr.series?download=1">query variant</a>
        <a href="pr.series#preview">fragment variant</a>
        <a href="pr.series">valid file</a>
        """

        result = discover_file_links(html, BASE_URL)

        self.assertEqual(result, [SourceFile("pr.series", f"{BASE_URL}pr.series")])

    def test_rejects_a_listing_with_no_valid_files(self) -> None:
        html = '<a href="../">Parent</a><a href="https://example.com/file">Other</a>'

        with self.assertRaisesRegex(DirectoryListingError, "no valid file links"):
            discover_file_links(html, BASE_URL)

    def test_requires_an_absolute_http_directory_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute HTTP"):
            discover_file_links('<a href="pr.series">Series</a>', "./relative/")

    def test_rejects_ambiguous_directory_url_components(self) -> None:
        for invalid_url, message in [
            (f"{BASE_URL}?sort=name", "query or fragment"),
            (f"{BASE_URL}#listing", "query or fragment"),
            (
                "https://user:password@download.bls.gov/pub/time.series/pr/",
                "embedded credentials",
            ),
        ]:
            with self.subTest(directory_url=invalid_url):
                with self.assertRaisesRegex(ValueError, message):
                    discover_file_links(
                        '<a href="pr.series">Series</a>',
                        invalid_url,
                    )


class FetchDirectoryHtmlTests(unittest.TestCase):
    def test_public_discovery_entry_point_fetches_and_parses(self) -> None:
        opener = Mock(
            return_value=FakeResponse(
                b'<a href="pr.series">Series</a><a href="../">Parent</a>'
            )
        )

        result = discover_source_files(
            BASE_URL,
            USER_AGENT,
            opener=opener,
        )

        self.assertEqual(result, [SourceFile("pr.series", f"{BASE_URL}pr.series")])

    def test_sends_identifying_user_agent_and_timeout(self) -> None:
        opener = Mock(return_value=FakeResponse(b"<html>source listing</html>"))

        result = fetch_directory_html(
            BASE_URL,
            USER_AGENT,
            timeout_seconds=12.5,
            opener=opener,
        )

        self.assertEqual(result, "<html>source listing</html>")
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, BASE_URL)
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(opener.call_args.kwargs["timeout"], 12.5)

    def test_rejects_placeholder_contact_information(self) -> None:
        opener = Mock()

        with self.assertRaisesRegex(ValueError, "non-placeholder contact email"):
            fetch_directory_html(
                BASE_URL,
                "data-quest/0.1 (contact: your-email@example.com)",
                opener=opener,
            )

        opener.assert_not_called()

    def test_rejects_non_http_directory_before_network_access(self) -> None:
        opener = Mock()

        for invalid_url in ["./relative/", "file:///tmp/provider-listing.html"]:
            with self.subTest(directory_url=invalid_url):
                with self.assertRaisesRegex(ValueError, "absolute HTTP"):
                    fetch_directory_html(
                        invalid_url,
                        USER_AGENT,
                        opener=opener,
                    )

        opener.assert_not_called()

    def test_explains_403_without_retrying(self) -> None:
        opener = Mock(
            side_effect=HTTPError(BASE_URL, 403, "Forbidden", Message(), None)
        )

        with self.assertRaisesRegex(SourcePolicyError, "BLS access policy"):
            fetch_directory_html(
                BASE_URL,
                USER_AGENT,
                max_attempts=3,
                opener=opener,
            )

        self.assertEqual(opener.call_count, 1)

    def test_explains_429_without_retrying(self) -> None:
        opener = Mock(
            side_effect=HTTPError(BASE_URL, 429, "Too Many Requests", Message(), None)
        )

        with self.assertRaisesRegex(SourcePolicyError, "BLS access policy"):
            fetch_directory_html(
                BASE_URL,
                USER_AGENT,
                max_attempts=3,
                opener=opener,
            )

        self.assertEqual(opener.call_count, 1)

    def test_retries_a_server_error_then_succeeds(self) -> None:
        opener = Mock(
            side_effect=[
                HTTPError(BASE_URL, 503, "Unavailable", Message(), None),
                FakeResponse(b"<html>server recovered</html>"),
            ]
        )
        sleeper = Mock()

        result = fetch_directory_html(
            BASE_URL,
            USER_AGENT,
            max_attempts=2,
            backoff_seconds=0.25,
            opener=opener,
            sleeper=sleeper,
        )

        self.assertEqual(result, "<html>server recovered</html>")
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(0.25)

    def test_reports_404_without_retrying(self) -> None:
        opener = Mock(
            side_effect=HTTPError(BASE_URL, 404, "Not Found", Message(), None)
        )

        with self.assertRaisesRegex(SourceRequestError, "not found"):
            fetch_directory_html(
                BASE_URL,
                USER_AGENT,
                max_attempts=3,
                opener=opener,
            )

        self.assertEqual(opener.call_count, 1)

    def test_reports_other_client_error_without_retrying(self) -> None:
        opener = Mock(
            side_effect=HTTPError(BASE_URL, 400, "Bad Request", Message(), None)
        )

        with self.assertRaisesRegex(SourceRequestError, "HTTP 400"):
            fetch_directory_html(
                BASE_URL,
                USER_AGENT,
                max_attempts=3,
                opener=opener,
            )

        self.assertEqual(opener.call_count, 1)

    def test_reports_response_decode_failure(self) -> None:
        opener = Mock(return_value=FakeResponse(b"source", charset="unknown-charset"))

        with self.assertRaisesRegex(SourceRequestError, "could not be decoded"):
            fetch_directory_html(BASE_URL, USER_AGENT, opener=opener)

    def test_rejects_invalid_retry_configuration_before_network_access(self) -> None:
        invalid_options = [
            ({"timeout_seconds": 0}, "timeout_seconds"),
            ({"max_attempts": 0}, "max_attempts"),
            ({"backoff_seconds": -0.1}, "backoff_seconds"),
        ]

        for options, message in invalid_options:
            opener = Mock()
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, message):
                    fetch_directory_html(
                        BASE_URL,
                        USER_AGENT,
                        opener=opener,
                        **options,
                    )
            opener.assert_not_called()

    def test_retries_a_transient_network_failure_then_succeeds(self) -> None:
        opener = Mock(
            side_effect=[
                URLError("temporary DNS failure"),
                FakeResponse(b"<html>recovered</html>"),
            ]
        )
        sleeper = Mock()

        result = fetch_directory_html(
            BASE_URL,
            USER_AGENT,
            max_attempts=3,
            backoff_seconds=0.25,
            opener=opener,
            sleeper=sleeper,
        )

        self.assertEqual(result, "<html>recovered</html>")
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(0.25)

    def test_stops_after_the_configured_attempt_limit(self) -> None:
        opener = Mock(side_effect=URLError("network unavailable"))
        sleeper = Mock()

        with self.assertRaisesRegex(SourceRequestError, "after 3 attempts"):
            fetch_directory_html(
                BASE_URL,
                USER_AGENT,
                max_attempts=3,
                backoff_seconds=0.5,
                opener=opener,
                sleeper=sleeper,
            )

        self.assertEqual(opener.call_count, 3)
        self.assertEqual([call.args[0] for call in sleeper.call_args_list], [0.5, 1.0])


if __name__ == "__main__":
    unittest.main()
