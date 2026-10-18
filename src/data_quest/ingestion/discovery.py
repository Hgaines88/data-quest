"""Safe discovery of files linked from a provider directory page."""

from dataclasses import dataclass
from html.parser import HTMLParser
from http.client import HTTPException, InvalidURL
from pathlib import PurePosixPath
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import SplitResult, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SourceRequestError(RuntimeError):
    """Raised when a source directory cannot be retrieved safely."""


class SourcePolicyError(SourceRequestError):
    """Raised when a provider refuses access for a policy-related reason."""


class SourceRedirectError(SourceRequestError):
    """Raised before a source request follows an unsafe redirect."""


class SameOriginRedirectHandler(HTTPRedirectHandler):
    """Allow redirects only when scheme, host, and effective port are unchanged."""

    def __init__(self, source_url: str) -> None:
        super().__init__()
        self._source_origin = _origin(source_url)

    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        if _origin(newurl) != self._source_origin:
            raise SourceRedirectError(
                "source redirect would leave the configured origin"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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
    opener: Callable[..., Any] | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> str:
    """Retrieve a directory page with identifying and bounded request behavior."""

    _validate_directory_url(directory_url)
    _validate_request_options(
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
    )
    source_origin = _origin(directory_url)
    selected_opener = opener or build_opener(
        SameOriginRedirectHandler(directory_url)
    ).open
    request = Request(directory_url, headers={"User-Agent": user_agent})

    for attempt in range(1, max_attempts + 1):
        try:
            with selected_opener(request, timeout=timeout_seconds) as response:
                if _origin(response.geturl()) != source_origin:
                    raise SourceRedirectError(
                        "source response redirected outside the configured origin"
                    )
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
        except SourceRedirectError:
            raise
        except InvalidURL as error:
            raise SourceRequestError(
                "source directory request contains an invalid URL"
            ) from error
        except (HTTPException, URLError, TimeoutError) as error:
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
    opener: Callable[..., Any] | None = None,
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

    base = _validate_directory_url(directory_url)

    directory_path = _normalized_directory_path(base.path)
    encoded_directory_path = _normalized_encoded_directory_path(base.path)
    canonical_base = urlunsplit(
        (
            base.scheme.casefold(),
            base.netloc.casefold(),
            encoded_directory_path,
            "",
            "",
        )
    )

    parser = _AnchorParser()
    parser.feed(html)

    discovered: dict[str, SourceFile] = {}
    for href in parser.hrefs:
        candidate = urlsplit(urljoin(canonical_base, href))
        encoded_path = candidate.path
        candidate_path = unquote(encoded_path)

        if candidate.scheme.casefold() != base.scheme.casefold():
            continue
        if candidate.netloc.casefold() != base.netloc.casefold():
            continue
        if any(
            character.isspace() or ord(character) < 32
            for character in encoded_path
        ):
            continue
        if candidate.query or candidate.fragment or candidate_path.endswith("/"):
            continue

        encoded_name = PurePosixPath(encoded_path).name
        name = unquote(encoded_name)
        if not _is_safe_decoded_name(name):
            continue

        normalized_path = str(PurePosixPath(candidate_path))
        candidate_parent = str(PurePosixPath(normalized_path).parent) + "/"
        if candidate_parent != directory_path:
            continue

        canonical_url = urlunsplit(
            (
                base.scheme.casefold(),
                base.netloc.casefold(),
                encoded_path,
                "",
                "",
            )
        )
        candidate_source = SourceFile(name=name, url=canonical_url)
        existing = discovered.get(name)
        if existing is None or _url_alias_order(candidate_source.url) < _url_alias_order(
            existing.url
        ):
            discovered[name] = candidate_source

    if not discovered:
        raise DirectoryListingError(
            "the directory page contained no valid file links inside the configured path"
        )

    return sorted(discovered.values())


def _is_safe_decoded_name(name: str) -> bool:
    """Reject decoded names whose URL or manifest identity is ambiguous."""

    return bool(name) and name not in {".", ".."} and not any(
        character in {"%", "/", "\\"}
        or ord(character) < 32
        or ord(character) == 127
        for character in name
    )


def _url_alias_order(url: str) -> tuple[int, str]:
    """Prefer the least encoded spelling, then make the choice deterministic."""

    return url.count("%"), url


def _origin(url: str) -> tuple[str, str, int | None]:
    """Return a normalized network origin with default ports made explicit."""

    parsed = urlsplit(url)
    scheme = parsed.scheme.casefold()
    default_port = {"http": 80, "https": 443}.get(scheme)
    try:
        port = parsed.port if parsed.port is not None else default_port
    except ValueError as error:
        raise ValueError("source URL contains an invalid port") from error
    return scheme, (parsed.hostname or "").casefold(), port


def _normalized_directory_path(path: str) -> str:
    """Normalize a URL path and retain its trailing directory separator."""

    normalized = str(PurePosixPath(unquote(path or "/")))
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def _normalized_encoded_directory_path(path: str) -> str:
    """Normalize URL structure without decoding provider path octets."""

    normalized = str(PurePosixPath(path or "/"))
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def _validate_directory_url(directory_url: str) -> SplitResult:
    """Return a parsed absolute HTTP directory URL with no ambiguous components."""

    parsed = urlsplit(directory_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("directory_url must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("directory_url must not contain embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("directory_url must not contain a query or fragment")
    return parsed


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
