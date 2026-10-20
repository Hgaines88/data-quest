"""Privacy-safe operational records for source landing runs."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from data_quest.ingestion.landing import LandingExecutionResult
from data_quest.ingestion.datausa import PopulationResponseError
from data_quest.ingestion.discovery import SourceRequestError
from data_quest.ingestion.download import DownloadIntegrityError, StagingWriteError
from data_quest.ingestion.manifest import IncompleteRunError


_SAFE_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_OUTCOMES = {"SUCCEEDED", "FAILED"}


@dataclass(frozen=True)
class IngestionRunAudit:
    """One terminal landing-run record with no raw errors or personal data."""

    source: str
    run_id: str
    started_at_utc: datetime
    completed_at_utc: datetime
    outcome: str
    failure_stage: str | None
    error_category: str | None
    discovered_count: int
    downloaded_count: int
    skipped_count: int
    new_count: int
    changed_count: int
    removed_count: int
    failed_file_count: int
    published_transition_count: int

    def __post_init__(self) -> None:
        for field_name in ("source", "run_id"):
            value = getattr(self, field_name)
            if not _SAFE_VALUE.fullmatch(value):
                raise ValueError(f"{field_name} must be a safe operational value")
        if self.outcome not in _OUTCOMES:
            raise ValueError("outcome must be SUCCEEDED or FAILED")
        for field_name in ("started_at_utc", "completed_at_utc"):
            value = getattr(self, field_name)
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError(f"{field_name} must be timezone-aware UTC")
        if self.completed_at_utc < self.started_at_utc:
            raise ValueError("completed_at_utc must not precede started_at_utc")
        if self.outcome == "SUCCEEDED" and (
            self.failure_stage is not None or self.error_category is not None
        ):
            raise ValueError("successful runs cannot contain failure metadata")
        if self.outcome == "FAILED" and (
            self.failure_stage is None or self.error_category is None
        ):
            raise ValueError("failed runs require sanitized failure metadata")
        for field_name in (
            "discovered_count",
            "downloaded_count",
            "skipped_count",
            "new_count",
            "changed_count",
            "removed_count",
            "failed_file_count",
            "published_transition_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a nonnegative integer")
        if self.downloaded_count > self.discovered_count:
            raise ValueError("downloaded_count cannot exceed discovered_count")
        if self.outcome == "SUCCEEDED":
            if self.downloaded_count != self.discovered_count:
                raise ValueError("successful runs must download every discovery")
            if self.failed_file_count != 0:
                raise ValueError("successful runs cannot contain failed files")
            if self.skipped_count + self.new_count + self.changed_count != (
                self.discovered_count
            ):
                raise ValueError("successful file counts must reconcile")
            if self.published_transition_count != (
                self.new_count + self.changed_count + self.removed_count
            ):
                raise ValueError("successful transition counts must reconcile")


def successful_run_audit(
    *,
    source: str,
    run_id: str,
    started_at_utc: datetime,
    completed_at_utc: datetime,
    result: LandingExecutionResult,
) -> IngestionRunAudit:
    """Build the terminal audit row for a fully reconciled landing run."""

    return IngestionRunAudit(
        source=source,
        run_id=run_id,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        outcome="SUCCEEDED",
        failure_stage=None,
        error_category=None,
        discovered_count=result.discovered_count,
        downloaded_count=result.discovered_count,
        skipped_count=(
            result.discovered_count - result.new_count - result.changed_count
        ),
        new_count=result.new_count,
        changed_count=result.changed_count,
        removed_count=result.removed_count,
        failed_file_count=0,
        published_transition_count=result.published_transition_count,
    )


def failed_run_audit(
    *,
    source: str,
    run_id: str,
    started_at_utc: datetime,
    completed_at_utc: datetime,
    failure_stage: str,
    error: Exception,
    discovered_count: int = 0,
    downloaded_count: int = 0,
    failed_file_count: int | None = None,
    result: LandingExecutionResult | None = None,
) -> IngestionRunAudit:
    """Build a failed audit row without persisting exception text."""

    if not _SAFE_VALUE.fullmatch(failure_stage):
        raise ValueError("failure_stage must be a safe operational value")
    error_category = _error_category(error)
    resolved_failed_file_count = (
        int(
            (
                failure_stage not in {"DISCOVERY", "DISCOVERY_CONFIRMATION"}
                and error_category in {"SOURCE_UNAVAILABLE", "FILE_VALIDATION"}
            )
            or (
                failure_stage == "DOWNLOAD_AND_VALIDATE"
                and isinstance(error, StagingWriteError)
            )
        )
        if failed_file_count is None
        else failed_file_count
    )
    return IngestionRunAudit(
        source=source,
        run_id=run_id,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        outcome="FAILED",
        failure_stage=failure_stage,
        error_category=error_category,
        discovered_count=(
            result.discovered_count if result is not None else discovered_count
        ),
        downloaded_count=(
            result.discovered_count if result is not None else downloaded_count
        ),
        skipped_count=(
            result.discovered_count - result.new_count - result.changed_count
            if result is not None
            else 0
        ),
        new_count=result.new_count if result is not None else 0,
        changed_count=result.changed_count if result is not None else 0,
        removed_count=result.removed_count if result is not None else 0,
        failed_file_count=resolved_failed_file_count,
        published_transition_count=(
            result.published_transition_count if result is not None else 0
        ),
    )


def _error_category(error: Exception) -> str:
    """Collapse failures into stable categories without retaining messages."""

    if isinstance(error, (DownloadIntegrityError, PopulationResponseError)) or (
        type(error).__name__ == "ControlledLandingFailure"
    ):
        return "FILE_VALIDATION"
    if isinstance(error, IncompleteRunError):
        return "INVENTORY_SAFETY"
    if isinstance(error, PermissionError) or type(error).__name__ == (
        "SparkSecurityException"
    ):
        return "AUTHORIZATION"
    if isinstance(error, (SourceRequestError, TimeoutError, ConnectionError)):
        return "SOURCE_UNAVAILABLE"
    if isinstance(error, (ValueError, AssertionError)):
        return "CONTRACT_VALIDATION"
    return "UNEXPECTED"
