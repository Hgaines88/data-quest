"""Pure configuration and source contracts for Bronze pipeline datasets."""

from dataclasses import dataclass
import re


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class BlsBronzeSpec:
    """One analytical BLS artifact and its source-shaped Bronze contract."""

    relative_path: str
    table_name: str
    columns: tuple[str, ...]
    required_nonblank: tuple[str, ...]
    source_columns: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.relative_path or "/" in self.relative_path:
            raise ValueError("relative_path must be one canonical BLS filename")
        if not _IDENTIFIER.fullmatch(self.table_name):
            raise ValueError("table_name must be a safe SQL identifier")
        if not self.columns or len(self.columns) != len(set(self.columns)):
            raise ValueError("columns must be nonempty and unique")
        if self.source_columns is not None and len(self.source_columns) != len(
            self.columns
        ):
            raise ValueError("source_columns must match the projected column count")
        if not self.required_nonblank or not set(self.required_nonblank) <= set(
            self.columns
        ):
            raise ValueError("required_nonblank must name declared columns")

    @property
    def expected_source_columns(self) -> tuple[str, ...]:
        """Return the provider's exact ordered header for validation."""

        return self.source_columns or self.columns


_OBSERVATION_COLUMNS = (
    "series_id",
    "year",
    "period",
    "value",
    "footnote_codes",
)
_OBSERVATION_REQUIRED = ("series_id", "year", "period", "value")


BLS_BRONZE_SPECS = (
    BlsBronzeSpec(
        relative_path="pr.class",
        table_name="bronze_bls_class",
        columns=(
            "class_code",
            "class_text",
            "display_level",
            "selectable",
            "sort_sequence",
        ),
        required_nonblank=("class_code", "class_text"),
    ),
    BlsBronzeSpec(
        relative_path="pr.data.0.Current",
        table_name="bronze_bls_observation_current",
        columns=_OBSERVATION_COLUMNS,
        required_nonblank=_OBSERVATION_REQUIRED,
    ),
    BlsBronzeSpec(
        relative_path="pr.data.1.AllData",
        table_name="bronze_bls_observation_all",
        columns=_OBSERVATION_COLUMNS,
        required_nonblank=_OBSERVATION_REQUIRED,
    ),
    BlsBronzeSpec(
        relative_path="pr.duration",
        table_name="bronze_bls_duration",
        columns=(
            "duration_code",
            "duration_text",
            "display_level",
            "selectable",
            "sort_sequence",
        ),
        required_nonblank=("duration_code", "duration_text"),
    ),
    BlsBronzeSpec(
        relative_path="pr.footnote",
        table_name="bronze_bls_footnote",
        columns=("footnote_code", "footnote_text"),
        required_nonblank=("footnote_code", "footnote_text"),
    ),
    BlsBronzeSpec(
        relative_path="pr.measure",
        table_name="bronze_bls_measure",
        columns=(
            "measure_code",
            "measure_text",
            "display_level",
            "selectable",
            "sort_sequence",
        ),
        required_nonblank=("measure_code", "measure_text"),
    ),
    BlsBronzeSpec(
        relative_path="pr.period",
        table_name="bronze_bls_period",
        columns=("period", "period_abbr", "period_name"),
        required_nonblank=("period", "period_name"),
    ),
    BlsBronzeSpec(
        relative_path="pr.seasonal",
        table_name="bronze_bls_seasonal",
        columns=("seasonal_code", "seasonal_text"),
        required_nonblank=("seasonal_code", "seasonal_text"),
        source_columns=("Seasonal_code", "Seasonal_text"),
    ),
    BlsBronzeSpec(
        relative_path="pr.sector",
        table_name="bronze_bls_sector",
        columns=(
            "sector_code",
            "sector_name",
            "display_level",
            "selectable",
            "sort_sequence",
        ),
        required_nonblank=("sector_code", "sector_name"),
    ),
    BlsBronzeSpec(
        relative_path="pr.series",
        table_name="bronze_bls_series",
        columns=(
            "series_id",
            "sector_code",
            "class_code",
            "measure_code",
            "duration_code",
            "seasonal",
            "base_year",
            "footnote_codes",
            "begin_year",
            "begin_period",
            "end_year",
            "end_period",
        ),
        required_nonblank=(
            "series_id",
            "sector_code",
            "class_code",
            "measure_code",
            "duration_code",
            "seasonal",
            "base_year",
            "begin_year",
            "begin_period",
            "end_year",
            "end_period",
        ),
    ),
)


@dataclass(frozen=True)
class PipelineSettings:
    """Validated Unity Catalog identifiers used to derive pipeline inputs."""

    catalog: str
    schema: str
    volume: str

    def __post_init__(self) -> None:
        for field_name in ("catalog", "schema", "volume"):
            if not _IDENTIFIER.fullmatch(getattr(self, field_name)):
                raise ValueError(f"{field_name} must be a safe SQL identifier")

    @property
    def bls_manifest_table(self) -> str:
        return f"{self.catalog}.{self.schema}.bls_ingestion_manifest"

    @property
    def datausa_manifest_table(self) -> str:
        return f"{self.catalog}.{self.schema}.datausa_ingestion_manifest"

    @property
    def bls_object_glob(self) -> str:
        return (
            f"/Volumes/{self.catalog}/{self.schema}/{self.volume}/"
            "bls/productivity/objects/*/*"
        )

    @property
    def datausa_object_glob(self) -> str:
        return (
            f"/Volumes/{self.catalog}/{self.schema}/{self.volume}/"
            "datausa/population/objects/*/*"
        )
