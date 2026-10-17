"""Safe discovery of files linked from a provider directory page."""

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


class SourceRequestError(RuntimeError):
    """Raised when a source directory cannot be retrieved safely."""


class SourcePolicyError(SourceRequestError):
    """Raised when a provider refuses access for a policy-related reason."""


class DirectoryListingError(ValueError):
    """Raised when a directory page contains no usable source-file links."""


@dataclass(frozen=True, order=True)
class SourceFile:
    """A file discovered inside the configured source directory."""

    name: str
    url: str


class _AnchorParser(HTMLParser):
    """Collect href values without assuming a provider-specific page layout."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.casefold() != "a":
            return

        for name, value in attrs:
            if name.casefold() == "href" and value:
                self.hrefs.append(value)
                break


def fetch_directory_html(
    directory_url: str,
    user_agent: str,
    *,
    timeout_seconds: float = 30.0,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    opener: Callable[..., Any] = urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> str:
    """Retrieve a directory page with identifying and bounded request behavior."""

    _validate_request_options(
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
    )
    request = Request(directory_url, headers={"User-Agent": user_agent})

    for attempt in range(1, max_attempts + 1):
        try:
            with opener(request, timeout=timeout_seconds) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset)
        except HTTPError as error:
            if error.code in {403, 429}:
                raise SourcePolicyError(
                    "the provider refused the request; review the BLS access policy "
                    "and confirm that the User-Agent contains valid owner contact information"
                ) from error
            if error.code == 404:
                raise SourceRequestError(
                    f"the configured source directory was not found: {directory_url}"
                ) from error
            if error.code < 500:
                raise SourceRequestError(
                    f"source directory request failed with HTTP {error.code}"
                ) from error
            last_error: Exception = error
        except (URLError, TimeoutError) as error:
            last_error = error
        except (LookupError, UnicodeError) as error:
            raise SourceRequestError(
                "the source directory response could not be decoded"
            ) from error

        if attempt < max_attempts:
            sleeper(backoff_seconds * attempt)

    raise SourceRequestError(
        f"source directory request failed after {max_attempts} attempts"
    ) from last_error


def discover_source_files(
    directory_url: str,
    user_agent: str,
    *,
    timeout_seconds: float = 30.0,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    opener: Callable[..., Any] = urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> list[SourceFile]:
    """Retrieve and parse the current file inventory for one source directory."""

    html = fetch_directory_html(
        directory_url,
        user_agent,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        opener=opener,
        sleeper=sleeper,
    )
    return discover_file_links(html, directory_url)


def discover_file_links(html: str, directory_url: str) -> list[SourceFile]:
    """Return sorted file links that remain inside one exact HTTP directory.

    Parent links, subdirectories, fragments, alternate origins, and links outside
    the configured directory are excluded. An empty result is treated as an error
    because silently accepting a changed or malformed provider page would make an
    ingestion run appear successful while discovering nothing.
    """

    base = urlsplit(directory_url)
    if base.scheme not in {"http", "https"} or not base.netloc:
        raise ValueError("directory_url must be an absolute HTTP(S) URL")

    directory_path = _normalized_directory_path(base.path)
    canonical_base = urlunsplit(
        (base.scheme.casefold(), base.netloc.casefold(), directory_path, "", "")
    )

    parser = _AnchorParser()
    parser.feed(html)

    discovered: dict[str, SourceFile] = {}
    for href in parser.hrefs:
        candidate = urlsplit(urljoin(canonical_base, href))
        candidate_path = unquote(candidate.path)

        if candidate.scheme.casefold() != base.scheme.casefold():
            continue
        if candidate.netloc.casefold() != base.netloc.casefold():
            continue
        if candidate.query or candidate.fragment or candidate_path.endswith("/"):
            continue

        normalized_path = str(PurePosixPath(candidate_path))
        candidate_parent = str(PurePosixPath(normalized_path).parent) + "/"
        if candidate_parent != directory_path:
            continue

        name = PurePosixPath(normalized_path).name
        if not name or name in {".", ".."}:
            continue

        canonical_url = urlunsplit(
            (
                base.scheme.casefold(),
                base.netloc.casefold(),
                normalized_path,
                "",
                "",
            )
        )
        discovered[canonical_url] = SourceFile(name=name, url=canonical_url)

    if not discovered:
        raise DirectoryListingError(
            "the directory page contained no valid file links inside the configured path"
        )

    return sorted(discovered.values())


def _normalized_directory_path(path: str) -> str:
    """Normalize a URL path and retain its trailing directory separator."""

    normalized = str(PurePosixPath(unquote(path or "/")))
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def _validate_request_options(
    *,
    user_agent: str,
    timeout_seconds: float,
    max_attempts: int,
    backoff_seconds: float,
) -> None:
    """Reject unsafe or ineffective request configuration before network access."""

    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", user_agent, re.I)
    if not email_match or email_match.group(0).casefold() == "your-email@example.com":
        raise ValueError(
            "user_agent must contain a non-placeholder contact email address"
        )
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")
