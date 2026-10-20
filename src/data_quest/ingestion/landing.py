"""Whole-run orchestration for verified BLS raw landing."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
import re
import shutil
from typing import Any, Callable

from data_quest.ingestion.discovery import SourceFile
from data_quest.ingestion.download import (
    DownloadedFile,
    build_versioned_landed_path,
    download_to_staging,
    promote_verified_file,
)
from data_quest.ingestion.manifest import (
    ChangeType,
    IncompleteRunError,
    ManifestChange,
    ManifestEntry,
    ManifestStatus,
    ObservedFile,
    plan_manifest_changes,
)


_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
BLS_REQUIRED_SOURCE_NAMES = ("pr.data.1.AllData", "pr.series")
DEFAULT_MAX_REMOVAL_FRACTION = 0.5


@dataclass(frozen=True)
class StagedSourceFile:
    """One fully downloaded source object awaiting publication."""

    relative_path: str
    staging_path: str
    observation: ObservedFile


@dataclass(frozen=True)
class LandingPlan:
    """Complete, deterministic plan produced before any raw publication."""

    run_id: str
    staging_root: str
    staged_files: tuple[StagedSourceFile, ...]
    changes: tuple[ManifestChange, ...]


@dataclass(frozen=True)
class LandingExecutionResult:
    """Counts from one successfully executed landing plan."""

    discovered_count: int
    promoted_count: int
    recovered_count: int
    reused_version_count: int
    new_count: int
    changed_count: int
    unchanged_count: int
    removed_count: int
    published_transition_count: int


def prepare_source_landing(
    source_files: list[SourceFile],
    current_entries: list[ManifestEntry],
    *,
    user_agent: str,
    volume_source_root: str,
    run_id: str,
    ingested_at_utc: datetime,
    timeout_seconds: float = 30.0,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    downloader: Callable[..., DownloadedFile] = download_to_staging,
    staged_validator: Callable[[DownloadedFile], None] | None = None,
    cleanup_tree: Callable[[str], None] | None = None,
) -> LandingPlan:
    """Stage and verify a complete BLS inventory, then create its manifest plan.

    No immutable object is promoted and no manifest transition is published by
    this function. If any download fails, the run-scoped staging tree is cleaned
    and no plan is returned.
    """

    cleanup = cleanup_tree or _cleanup_tree
    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id contains unsafe path characters")

    sorted_sources = sorted(source_files, key=lambda source: source.name)
    _validate_unique_source_paths(sorted_sources)
    for source in sorted_sources:
        build_versioned_landed_path(
            volume_source_root,
            source.name,
            "0" * 64,
        )

    staging_root = str(PurePosixPath(volume_source_root) / "_staging" / run_id)
    staged_files: list[StagedSourceFile] = []
    try:
        for source in sorted_sources:
            staging_path = str(
                PurePosixPath(staging_root) / f"{source.name}.partial"
            )
            downloaded = downloader(
                source.url,
                user_agent,
                staging_path,
                timeout_seconds=timeout_seconds,
                max_attempts=max_attempts,
                backoff_seconds=backoff_seconds,
            )
            if downloaded.source_url != source.url:
                raise ValueError(
                    "downloader returned metadata for a different source URL"
                )
            if staged_validator is not None:
                staged_validator(downloaded)

            landed_path = build_versioned_landed_path(
                volume_source_root,
                source.name,
                downloaded.content_sha256,
            )
            observation = ObservedFile(
                source_url=source.url,
                relative_path=source.name,
                landed_path=landed_path,
                source_etag=downloaded.source_etag,
                source_last_modified=downloaded.source_last_modified,
                source_content_length=downloaded.source_content_length,
                content_size_bytes=downloaded.content_size_bytes,
                content_sha256=downloaded.content_sha256,
            )
            staged_files.append(
                StagedSourceFile(
                    relative_path=source.name,
                    staging_path=downloaded.staging_path,
                    observation=observation,
                )
            )

        changes = plan_manifest_changes(
            [staged.observation for staged in staged_files],
            current_entries,
            ingested_at_utc=ingested_at_utc,
            run_id=run_id,
            inventory_complete=True,
            downloads_complete=True,
        )
    except Exception as error:
        # Preserve privacy-safe progress without wrapping the original error,
        # so downstream classification can still use its concrete type.
        try:
            error.verified_download_count = len(staged_files)
        except (AttributeError, TypeError):
            pass
        cleanup(staging_root)
        raise

    return LandingPlan(
        run_id=run_id,
        staging_root=staging_root,
        staged_files=tuple(staged_files),
        changes=tuple(changes),
    )


def prepare_bls_landing(
    source_files: list[SourceFile],
    current_entries: list[ManifestEntry],
    *,
    confirmed_source_files: list[SourceFile] | None = None,
    max_removal_fraction: float = DEFAULT_MAX_REMOVAL_FRACTION,
    allow_mass_removal: bool = False,
    **kwargs: Any,
) -> LandingPlan:
    """Validate BLS inventory completeness before staging and planning changes.

    The complete inventory remains dynamic. Only sources required by the
    assignment are fixed prerequisites. Any proposed removal needs a second,
    identical discovery, while an unusually large removal additionally needs
    an explicit operator override.
    """

    _validate_bls_inventory_safety(
        source_files,
        current_entries,
        confirmed_source_files=confirmed_source_files,
        max_removal_fraction=max_removal_fraction,
        allow_mass_removal=allow_mass_removal,
    )

    return prepare_source_landing(source_files, current_entries, **kwargs)


def _validate_bls_inventory_safety(
    source_files: list[SourceFile],
    current_entries: list[ManifestEntry],
    *,
    confirmed_source_files: list[SourceFile] | None,
    max_removal_fraction: float,
    allow_mass_removal: bool,
) -> None:
    if (
        isinstance(max_removal_fraction, bool)
        or not isinstance(max_removal_fraction, (int, float))
        or not 0 <= max_removal_fraction <= 1
    ):
        raise ValueError("max_removal_fraction must be between zero and one")
    if not isinstance(allow_mass_removal, bool):
        raise ValueError("allow_mass_removal must be a boolean")

    first_inventory = _source_inventory(source_files)
    missing_required = set(BLS_REQUIRED_SOURCE_NAMES) - set(first_inventory)
    if missing_required:
        raise IncompleteRunError(
            "required BLS source files are missing from discovery: "
            f"{sorted(missing_required)}"
        )

    active_paths = {
        entry.relative_path
        for entry in current_entries
        if entry.status is ManifestStatus.ACTIVE
    }
    removal_candidates = active_paths - set(first_inventory)
    if not removal_candidates:
        return

    if confirmed_source_files is None:
        raise IncompleteRunError(
            "BLS removal candidates require a second inventory confirmation"
        )

    confirmed_inventory = _source_inventory(confirmed_source_files)
    if confirmed_inventory != first_inventory:
        raise IncompleteRunError(
            "independent BLS removal inventories do not match"
        )

    removal_fraction = len(removal_candidates) / len(active_paths)
    if removal_fraction > max_removal_fraction and not allow_mass_removal:
        raise IncompleteRunError(
            "BLS mass removal exceeds the configured safety threshold; "
            "an explicit operator override is required"
        )


def _source_inventory(source_files: list[SourceFile]) -> dict[str, str]:
    _validate_unique_source_paths(source_files)
    return {source.name: source.url for source in source_files}


def execute_landing_plan(
    plan: LandingPlan,
    *,
    publisher: Callable[[list[ManifestEntry]], None],
    promoter: Callable[..., bool] = promote_verified_file,
    cleanup_tree: Callable[[str], None] | None = None,
) -> LandingExecutionResult:
    """Promote every required object before publishing one manifest batch.

    The publisher must commit its entire list atomically. New and changed files
    are immutable, so a failure before that commit can leave only unreferenced
    content versions; it cannot alter the previously committed manifest truth.
    """

    cleanup = cleanup_tree or _cleanup_tree
    staged_by_path = {
        staged.relative_path: staged for staged in plan.staged_files
    }
    promoted_count = 0
    recovered_count = 0
    reused_count = 0
    publish_entries: list[ManifestEntry] = []

    try:
        for change in plan.changes:
            needs_immutable_object = change.change_type in {
                ChangeType.NEW,
                ChangeType.CHANGED,
            } or (
                change.change_type is ChangeType.UNCHANGED
                and change.after.status is ManifestStatus.ACTIVE
            )
            if needs_immutable_object:
                staged = staged_by_path.get(change.relative_path)
                if staged is None:
                    raise ValueError(
                        f"no staged bytes exist for {change.change_type.value} "
                        f"object: {change.relative_path}"
                    )
                promoted = promoter(
                    staged.staging_path,
                    change.after.landed_path,
                    expected_size=change.after.content_size_bytes,
                    expected_sha256=change.after.content_sha256,
                )
                if change.change_type is ChangeType.UNCHANGED:
                    if promoted:
                        recovered_count += 1
                elif promoted:
                    promoted_count += 1
                else:
                    reused_count += 1

            if change.change_type is not ChangeType.UNCHANGED:
                publish_entries.append(change.after)

        if publish_entries:
            publisher(publish_entries)
    finally:
        cleanup(plan.staging_root)

    counts = {
        change_type: sum(
            change.change_type is change_type for change in plan.changes
        )
        for change_type in ChangeType
    }
    return LandingExecutionResult(
        discovered_count=len(plan.staged_files),
        promoted_count=promoted_count,
        recovered_count=recovered_count,
        reused_version_count=reused_count,
        new_count=counts[ChangeType.NEW],
        changed_count=counts[ChangeType.CHANGED],
        unchanged_count=counts[ChangeType.UNCHANGED],
        removed_count=counts[ChangeType.REMOVED],
        published_transition_count=len(publish_entries),
    )


def _validate_unique_source_paths(source_files: list[SourceFile]) -> None:
    seen: set[str] = set()
    for source in source_files:
        if source.name in seen:
            raise ValueError(f"duplicate source relative_path: {source.name}")
        seen.add(source.name)


def _cleanup_tree(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
