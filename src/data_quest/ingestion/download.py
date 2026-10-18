"""Verified streaming and immutable promotion for raw source artifacts."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from data_quest.ingestion.discovery import (
    SameOriginRedirectHandler,
    SourcePolicyError,
    SourceRedirectError,
    SourceRequestError,
)


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class DownloadIntegrityError(SourceRequestError):
    """Raised when downloaded or previously landed bytes fail verification."""


class StagingWriteError(RuntimeError):
    """Raised when verified staging storage cannot be written safely."""


@dataclass(frozen=True)
class DownloadedFile:
    """Audit metadata calculated while streaming one source object."""

    source_url: str
    staging_path: str
    source_etag: str | None
    source_last_modified: str | None
    source_content_length: int | None
    content_size_bytes: int
    content_sha256: str


def download_to_staging(
    source_url: str,
    user_agent: str,
    destination: str | Path,
    *,
    timeout_seconds: float = 30.0,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    chunk_size: int = 64 * 1024,
    allow_query: bool = False,
    require_contact_email: bool = True,
    opener: Callable[..., Any] | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> DownloadedFile:
    """Stream one source object to staging and verify its complete byte count.

    The destination is run-scoped temporary state, never a published raw path.
    A failed attempt is removed before retry or return. HTTP policy errors and
    cross-origin redirects fail immediately rather than being retried.
    """

    source_origin = _validate_download_options(
        source_url=source_url,
        user_agent=user_agent,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        chunk_size=chunk_size,
        allow_query=allow_query,
        require_contact_email=require_contact_email,
    )
    destination_path = Path(destination)
    _remove_if_present(destination_path)
    selected_opener = opener or build_opener(
        SameOriginRedirectHandler(source_url)
    ).open
    request = Request(source_url, headers={"User-Agent": user_agent})
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            with selected_opener(request, timeout=timeout_seconds) as response:
                response_url = response.geturl()
                response_origin = _origin(response_url)
                if response_origin != source_origin:
                    raise SourceRedirectError(
                        "source response redirected outside the configured origin"
                    )

                reported_length = _parse_content_length(
                    response.headers.get("Content-Length")
                )
                digest = hashlib.sha256()
                byte_count = 0

                try:
                    destination_path.parent.mkdir(parents=True, exist_ok=True)
                    with destination_path.open("wb") as destination_file:
                        while True:
                            try:
                                chunk = response.read(chunk_size)
                            except (OSError, TimeoutError, URLError) as error:
                                raise SourceRequestError(
                                    "source response failed while streaming bytes"
                                ) from error
                            if not chunk:
                                break
                            try:
                                destination_file.write(chunk)
                            except OSError as error:
                                raise StagingWriteError(
                                    f"could not write staging file: {destination_path}"
                                ) from error
                            digest.update(chunk)
                            byte_count += len(chunk)
                except StagingWriteError:
                    _remove_if_present(destination_path)
                    raise

                if reported_length is not None and byte_count != reported_length:
                    raise DownloadIntegrityError(
                        "downloaded byte count does not match the HTTP Content-Length "
                        f"({byte_count} != {reported_length})"
                    )

                return DownloadedFile(
                    source_url=source_url,
                    staging_path=str(destination_path),
                    source_etag=response.headers.get("ETag"),
                    source_last_modified=response.headers.get("Last-Modified"),
                    source_content_length=reported_length,
                    content_size_bytes=byte_count,
                    content_sha256=digest.hexdigest(),
                )
        except HTTPError as error:
            _remove_if_present(destination_path)
            try:
                if error.code in {403, 429}:
                    raise SourcePolicyError(
                        "the provider refused the request; review the BLS access policy "
                        "and confirm that the User-Agent contains valid owner contact information"
                    ) from error
                if error.code == 404:
                    raise SourceRequestError(
                        f"the discovered source object was not found: {source_url}"
                    ) from error
                if error.code < 500:
                    raise SourceRequestError(
                        f"source object request failed with HTTP {error.code}"
                    ) from error
                last_error = error
            finally:
                error.close()
        except (SourceRedirectError, StagingWriteError):
            _remove_if_present(destination_path)
            raise
        except (DownloadIntegrityError, SourceRequestError, URLError, TimeoutError) as error:
            _remove_if_present(destination_path)
            last_error = error

        if attempt < max_attempts:
            sleeper(backoff_seconds * attempt)

    _remove_if_present(destination_path)
    if isinstance(last_error, DownloadIntegrityError):
        raise last_error
    raise SourceRequestError(
        f"source object request failed after {max_attempts} attempts"
    ) from last_error


def build_versioned_landed_path(
    volume_source_root: str,
    relative_path: str,
    content_sha256: str,
) -> str:
    """Return the immutable Volume path for one verified content version."""

    root = PurePosixPath(volume_source_root)
    relative = PurePosixPath(relative_path)
    if (
        not root.is_absolute()
        or not str(root).startswith("/Volumes/")
        or str(root) != volume_source_root.rstrip("/")
    ):
        raise ValueError("volume_source_root must be a canonical /Volumes path")
    if (
        not relative_path
        or relative.is_absolute()
        or str(relative) != relative_path
        or relative_path.endswith("/")
        or any(part in {".", ".."} for part in relative.parts)
    ):
        raise ValueError("relative_path must be a canonical safe relative file path")
    if not _SHA256_PATTERN.fullmatch(content_sha256):
        raise ValueError("content_sha256 must be a lowercase 64-character digest")

    return str(root / "objects" / content_sha256 / relative)


def promote_verified_file(
    staging_path: str | Path,
    landed_path: str | Path,
    *,
    expected_size: int,
    expected_sha256: str,
) -> bool:
    """Promote verified staged bytes without overwriting an existing version.

    Returns ``True`` when a new immutable object is promoted and ``False`` when
    the exact verified object already exists. A conflicting existing object is
    left untouched and fails visibly.
    """

    if expected_size < 0:
        raise ValueError("expected_size cannot be negative")
    if not _SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be a lowercase 64-character digest")

    staging = Path(staging_path)
    landed = Path(landed_path)
    _assert_file_evidence(
        staging,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
        description="staging",
    )

    if landed.exists():
        _assert_file_evidence(
            landed,
            expected_size=expected_size,
            expected_sha256=expected_sha256,
            description="existing landed",
        )
        staging.unlink()
        return False

    landed.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, landed)
    _assert_file_evidence(
        landed,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
        description="promoted landed",
    )
    return True


def verify_file_evidence(
    path: str | Path,
    *,
    expected_size: int,
    expected_sha256: str,
) -> None:
    """Fail visibly unless a landed file matches its manifest evidence."""

    if expected_size < 0:
        raise ValueError("expected_size cannot be negative")
    if not _SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("expected_sha256 must be a lowercase 64-character digest")
    _assert_file_evidence(
        Path(path),
        expected_size=expected_size,
        expected_sha256=expected_sha256,
        description="landed",
    )


def _assert_file_evidence(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    description: str,
) -> None:
    if not path.is_file():
        raise DownloadIntegrityError(f"{description} file does not exist: {path}")

    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as source_file:
        while chunk := source_file.read(64 * 1024):
            digest.update(chunk)
            byte_count += len(chunk)

    if byte_count != expected_size or digest.hexdigest() != expected_sha256:
        raise DownloadIntegrityError(
            f"{description} file does not match its expected size and SHA-256"
        )


def _validate_download_options(
    *,
    source_url: str,
    user_agent: str,
    timeout_seconds: float,
    max_attempts: int,
    backoff_seconds: float,
    chunk_size: int,
    allow_query: bool,
    require_contact_email: bool,
) -> tuple[str, str, int | None]:
    parsed = urlsplit(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an absolute HTTP(S) URL")
    if (
        parsed.username
        or parsed.password
        or (parsed.query and not allow_query)
        or parsed.fragment
    ):
        raise ValueError(
            "source_url must not contain credentials, a disallowed query, "
            "or a fragment"
        )
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", user_agent, re.I)
    if require_contact_email and (
        not email_match
        or email_match.group(0).casefold() == "your-email@example.com"
    ):
        raise ValueError(
            "user_agent must contain a non-placeholder contact email address"
        )
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least one")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds cannot be negative")
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least one byte")
    return _origin(source_url)


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.casefold()
    default_port = {"http": 80, "https": 443}.get(scheme)
    try:
        port = parsed.port if parsed.port is not None else default_port
    except ValueError as error:
        raise ValueError("source URL contains an invalid port") from error
    return scheme, (parsed.hostname or "").casefold(), port


def _parse_content_length(raw_value: str | None) -> int | None:
    if raw_value is None:
        return None
    try:
        value = int(raw_value)
    except ValueError as error:
        raise DownloadIntegrityError(
            "HTTP Content-Length must be a nonnegative integer"
        ) from error
    if value < 0:
        raise DownloadIntegrityError(
            "HTTP Content-Length must be a nonnegative integer"
        )
    return value


def _remove_if_present(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return
