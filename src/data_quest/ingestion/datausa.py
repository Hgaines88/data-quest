"""Validation and landing preparation for the assigned Data USA response."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable

from data_quest.ingestion.discovery import SourceFile
from data_quest.ingestion.download import DownloadedFile, download_to_staging
from data_quest.ingestion.landing import LandingPlan, prepare_source_landing
from data_quest.ingestion.manifest import ManifestEntry


POPULATION_RELATIVE_PATH = "population.json"
REQUIRED_COLUMNS = ("Nation ID", "Nation", "Year", "Population")


class PopulationResponseError(ValueError):
    """Raised when the raw API response violates the expected contract."""


@dataclass(frozen=True)
class PopulationResponseSummary:
    """Small validation result retained without transforming source bytes."""

    record_count: int
    columns: tuple[str, ...]
    minimum_year: int
    maximum_year: int


def validate_population_response(path: str | Path) -> PopulationResponseSummary:
    """Validate the complete assigned JSON envelope without rewriting it."""

    source_path = Path(path)
    try:
        raw_bytes = source_path.read_bytes()
    except OSError as error:
        raise PopulationResponseError(
            f"could not read staged population response: {source_path}"
        ) from error

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PopulationResponseError(
            "population response must be valid UTF-8 JSON"
        ) from error

    if not isinstance(payload, dict):
        raise PopulationResponseError("population response must be a JSON object")

    expected_types = {
        "annotations": dict,
        "columns": list,
        "data": list,
        "page": dict,
    }
    for field_name, expected_type in expected_types.items():
        if not isinstance(payload.get(field_name), expected_type):
            raise PopulationResponseError(
                f"population response field {field_name!r} must be "
                f"{expected_type.__name__}"
            )

    columns = payload["columns"]
    if not all(isinstance(column, str) and column for column in columns):
        raise PopulationResponseError("population columns must be nonempty strings")
    if len(columns) != len(set(columns)):
        raise PopulationResponseError("population columns must be unique")
    missing_columns = set(REQUIRED_COLUMNS) - set(columns)
    if missing_columns:
        raise PopulationResponseError(
            f"population response is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    records = payload["data"]
    if not records:
        raise PopulationResponseError("population response must contain data records")

    years: list[int] = []
    expected_record_keys = set(columns)
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != expected_record_keys:
            raise PopulationResponseError(
                f"population record {index} must match the declared columns"
            )
        if not isinstance(record["Nation ID"], str) or not record["Nation ID"]:
            raise PopulationResponseError(
                f"population record {index} has an invalid Nation ID"
            )
        if not isinstance(record["Nation"], str) or not record["Nation"]:
            raise PopulationResponseError(
                f"population record {index} has an invalid Nation"
            )
        year = record["Year"]
        if isinstance(year, bool) or not isinstance(year, int):
            raise PopulationResponseError(
                f"population record {index} has a non-integer Year"
            )
        population = record["Population"]
        if (
            isinstance(population, bool)
            or not isinstance(population, (int, float))
            or population < 0
        ):
            raise PopulationResponseError(
                f"population record {index} has an invalid Population"
            )
        years.append(year)

    page = payload["page"]
    for field_name in ("limit", "offset", "total"):
        value = page.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PopulationResponseError(
                f"population page field {field_name!r} must be a nonnegative integer"
            )
    if page["offset"] != 0 or page["total"] != len(records):
        raise PopulationResponseError(
            "population response is not the complete first-page result"
        )

    return PopulationResponseSummary(
        record_count=len(records),
        columns=tuple(columns),
        minimum_year=min(years),
        maximum_year=max(years),
    )


def prepare_population_landing(
    endpoint_url: str,
    current_entries: list[ManifestEntry],
    *,
    user_agent: str,
    volume_source_root: str,
    run_id: str,
    ingested_at_utc: datetime,
    timeout_seconds: float = 30.0,
    max_attempts: int = 3,
    backoff_seconds: float = 1.0,
    downloader: Callable[..., DownloadedFile] | None = None,
    cleanup_tree: Callable[[str], None] | None = None,
) -> tuple[LandingPlan, PopulationResponseSummary]:
    """Stage and validate the raw population response before planning publish."""

    population_summary: PopulationResponseSummary | None = None

    def validate_download(downloaded: DownloadedFile) -> None:
        nonlocal population_summary
        population_summary = validate_population_response(downloaded.staging_path)

    selected_downloader = downloader or _download_api_response
    plan = prepare_source_landing(
        [SourceFile(name=POPULATION_RELATIVE_PATH, url=endpoint_url)],
        current_entries,
        user_agent=user_agent,
        volume_source_root=volume_source_root,
        run_id=run_id,
        ingested_at_utc=ingested_at_utc,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        backoff_seconds=backoff_seconds,
        downloader=selected_downloader,
        staged_validator=validate_download,
        cleanup_tree=cleanup_tree,
    )
    if population_summary is None:
        raise AssertionError("population validation did not produce a summary")
    return plan, population_summary


def _download_api_response(
    source_url: str,
    user_agent: str,
    destination: str | Path,
    **kwargs: Any,
) -> DownloadedFile:
    return download_to_staging(
        source_url,
        user_agent,
        destination,
        allow_query=True,
        **kwargs,
    )
