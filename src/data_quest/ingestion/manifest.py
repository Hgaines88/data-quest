"""Deterministic contract for planning raw-ingestion manifest changes.

This module is deliberately free of network, filesystem, and Databricks calls.
It describes the state that a later ingestion runner may publish only after a
complete inventory has been discovered and every required download has landed
and passed its byte-count and SHA-256 checks.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from pathlib import PurePosixPath
import re
from typing import TypeVar
from urllib.parse import urlsplit


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_ManifestRecord = TypeVar("_ManifestRecord", bound="ObservedFile | ManifestEntry")


class ManifestContractError(ValueError):
    """Raised when a manifest value or state violates the published contract."""


class IncompleteRunError(ManifestContractError):
    """Raised when a partial run attempts to create a publishable state plan."""


class ManifestStatus(str, Enum):
    """Lifecycle state of one source path in the current manifest snapshot."""

    ACTIVE = "active"
    REMOVED = "removed"


class ChangeType(str, Enum):
    """Relationship between a complete source inventory and current manifest."""

    NEW = "new"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
    REMOVED = "removed"


@dataclass(frozen=True)
class ObservedFile:
    """Verified metadata for a source file staged during the current run.

    Provider metadata is retained for provenance but is advisory. The actual
    downloaded byte count and SHA-256 digest determine content equality.
    """

    source_url: str
    relative_path: str
    landed_path: str
    source_etag: str | None
    source_last_modified: str | None
    source_content_length: int | None
    content_size_bytes: int
    content_sha256: str

    def __post_init__(self) -> None:
        _validate_source_url(self.source_url)
        _validate_relative_path(self.relative_path)
        _validate_landed_path(self.landed_path)
        _validate_optional_size(
            self.source_content_length,
            field_name="source_content_length",
        )
        if self.content_size_bytes < 0:
            raise ManifestContractError("content_size_bytes cannot be negative")
        if not _SHA256_PATTERN.fullmatch(self.content_sha256):
            raise ManifestContractError(
                "content_sha256 must be a lowercase 64-character SHA-256 digest"
            )


@dataclass(frozen=True)
class ManifestEntry:
    """One current manifest record, including append-only removal tombstones."""

    source_url: str
    relative_path: str
    landed_path: str
    source_etag: str | None
    source_last_modified: str | None
    source_content_length: int | None
    content_size_bytes: int
    content_sha256: str
    ingested_at_utc: datetime
    run_id: str
    status: ManifestStatus

    def __post_init__(self) -> None:
        _validate_source_url(self.source_url)
        _validate_relative_path(self.relative_path)
        _validate_landed_path(self.landed_path)
        _validate_optional_size(
            self.source_content_length,
            field_name="source_content_length",
        )
        if self.content_size_bytes < 0:
            raise ManifestContractError("content_size_bytes cannot be negative")
        if not _SHA256_PATTERN.fullmatch(self.content_sha256):
            raise ManifestContractError(
                "content_sha256 must be a lowercase 64-character SHA-256 digest"
            )
        if (
            self.ingested_at_utc.tzinfo is None
            or self.ingested_at_utc.utcoffset() != timedelta(0)
        ):
            raise ManifestContractError("ingested_at_utc must be UTC-aware")
        _validate_run_id(self.run_id)
        if not isinstance(self.status, ManifestStatus):
            raise ManifestContractError("status must be a ManifestStatus value")

    @classmethod
    def from_observation(
        cls,
        observation: ObservedFile,
        *,
        ingested_at_utc: datetime,
        run_id: str,
    ) -> "ManifestEntry":
        """Create an active entry after a staged file has passed verification."""

        return cls(
            source_url=observation.source_url,
            relative_path=observation.relative_path,
            landed_path=observation.landed_path,
            source_etag=observation.source_etag,
            source_last_modified=observation.source_last_modified,
            source_content_length=observation.source_content_length,
            content_size_bytes=observation.content_size_bytes,
            content_sha256=observation.content_sha256,
            ingested_at_utc=ingested_at_utc,
            run_id=run_id,
            status=ManifestStatus.ACTIVE,
        )

    def as_removed(
        self,
        *,
        removed_at_utc: datetime,
        run_id: str,
    ) -> "ManifestEntry":
        """Return a tombstone while retaining the last verified content evidence."""

        return replace(
            self,
            ingested_at_utc=removed_at_utc,
            run_id=run_id,
            status=ManifestStatus.REMOVED,
        )


@dataclass(frozen=True)
class ManifestChange:
    """One deterministic transition proposed for a complete ingestion run."""

    relative_path: str
    change_type: ChangeType
    before: ManifestEntry | None
    after: ManifestEntry


def plan_manifest_changes(
    observed_files: list[ObservedFile],
    current_entries: list[ManifestEntry],
    *,
    ingested_at_utc: datetime,
    run_id: str,
    inventory_complete: bool = True,
    downloads_complete: bool = True,
) -> list[ManifestChange]:
    """Compare verified observations with current state in stable path order.

    The function returns a plan; it does not persist state. A caller must stage
    downloads outside the published raw path and publish the complete manifest
    snapshot atomically. If discovery or downloading was incomplete, no plan is
    returned, so a partial run cannot mark valid source files as removed.
    """

    _validate_utc_timestamp(ingested_at_utc)
    _validate_run_id(run_id)
    if not inventory_complete:
        raise IncompleteRunError(
            "source inventory is incomplete; the manifest plan cannot be published"
        )
    if not downloads_complete:
        raise IncompleteRunError(
            "one or more downloads are incomplete; the manifest plan cannot be published"
        )

    observed_by_path = _index_unique(
        observed_files,
        collection_name="observed",
    )
    current_by_path = _index_unique(
        current_entries,
        collection_name="current",
    )

    changes: list[ManifestChange] = []
    for relative_path in sorted(observed_by_path.keys() | current_by_path.keys()):
        observation = observed_by_path.get(relative_path)
        current = current_by_path.get(relative_path)

        if observation is None:
            if current is None:  # Defensive guard for static type narrowing.
                raise AssertionError("manifest key disappeared during planning")
            if current.status is ManifestStatus.REMOVED:
                changes.append(
                    ManifestChange(
                        relative_path,
                        ChangeType.UNCHANGED,
                        current,
                        current,
                    )
                )
            else:
                changes.append(
                    ManifestChange(
                        relative_path,
                        ChangeType.REMOVED,
                        current,
                        current.as_removed(
                            removed_at_utc=ingested_at_utc,
                            run_id=run_id,
                        ),
                    )
                )
            continue

        candidate = ManifestEntry.from_observation(
            observation,
            ingested_at_utc=ingested_at_utc,
            run_id=run_id,
        )
        if current is None or current.status is ManifestStatus.REMOVED:
            changes.append(
                ManifestChange(
                    relative_path,
                    ChangeType.NEW,
                    current,
                    candidate,
                )
            )
        elif _same_content(observation, current):
            changes.append(
                ManifestChange(
                    relative_path,
                    ChangeType.UNCHANGED,
                    current,
                    current,
                )
            )
        else:
            changes.append(
                ManifestChange(
                    relative_path,
                    ChangeType.CHANGED,
                    current,
                    candidate,
                )
            )

    return changes


def _same_content(observation: ObservedFile, current: ManifestEntry) -> bool:
    """Compare verified content evidence rather than advisory HTTP metadata."""

    return (
        observation.content_size_bytes == current.content_size_bytes
        and observation.content_sha256 == current.content_sha256
    )


def _index_unique(
    records: list[_ManifestRecord],
    *,
    collection_name: str,
) -> dict[str, _ManifestRecord]:
    """Index one current record per stable relative path or fail visibly."""

    indexed: dict[str, _ManifestRecord] = {}
    for record in records:
        if record.relative_path in indexed:
            raise ManifestContractError(
                f"duplicate {collection_name} relative_path: {record.relative_path}"
            )
        indexed[record.relative_path] = record
    return indexed


def _validate_source_url(source_url: str) -> None:
    parsed = urlsplit(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ManifestContractError("source_url must be an absolute HTTP(S) URL")


def _validate_relative_path(relative_path: str) -> None:
    path = PurePosixPath(relative_path)
    if (
        not relative_path
        or path.is_absolute()
        or str(path) != relative_path
        or relative_path.endswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ManifestContractError(
            "relative_path must identify a safe file below the source root"
        )


def _validate_landed_path(landed_path: str) -> None:
    path = PurePosixPath(landed_path)
    if (
        not landed_path
        or not path.is_absolute()
        or str(path) != landed_path
        or not landed_path.startswith("/Volumes/")
        or landed_path.endswith("/")
        or any(part in {".", ".."} for part in path.parts)
    ):
        raise ManifestContractError(
            "landed_path must be a canonical absolute path to verified raw bytes"
        )


def _validate_optional_size(value: int | None, *, field_name: str) -> None:
    if value is not None and value < 0:
        raise ManifestContractError(f"{field_name} cannot be negative")


def _validate_utc_timestamp(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ManifestContractError("ingested_at_utc must be UTC-aware")


def _validate_run_id(run_id: str) -> None:
    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ManifestContractError(
            "run_id must contain 1-128 safe alphanumeric, dot, underscore, colon, "
            "or hyphen characters"
        )
