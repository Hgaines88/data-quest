# Databricks notebook source
"""Publish typed BLS observations and provider-grounded series metadata."""

from pathlib import Path
import sys

from pyspark import pipelines as dp
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def _find_repository_root() -> Path:
    current = Path.cwd()
    for candidate in (current, *current.parents):
        if (candidate / "src" / "data_quest").is_dir():
            return candidate
    raise RuntimeError("could not locate the data-quest repository root")


REPOSITORY_ROOT = _find_repository_root()
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from data_quest.validation.bronze_contract import PipelineSettings  # noqa: E402


SETTINGS = PipelineSettings(
    catalog=spark.conf.get("data_quest.catalog", "workspace"),
    schema=spark.conf.get("data_quest.schema", "rearc_data_quest"),
    volume=spark.conf.get("data_quest.volume", "raw_landing"),
)

_BUSINESS_KEY = ("series_id", "year", "period_code")
_SILVER_COLUMNS = (
    "series_id",
    "year",
    "period_code",
    "value",
    "footnote_codes",
    "source_file",
    "source_path",
    "ingested_at_utc",
    "run_id",
    "content_sha256",
)
_SERIES_COLUMNS = (
    "series_id",
    "series_label",
    "sector_code",
    "sector_name",
    "class_code",
    "class_text",
    "measure_code",
    "measure_text",
    "duration_code",
    "duration_text",
    "seasonal_code",
    "seasonal_text",
    "base_year",
    "begin_year",
    "begin_period",
    "end_year",
    "end_period",
    "footnote_codes",
    "source_file",
    "source_path",
    "ingested_at_utc",
    "run_id",
    "content_sha256",
)
_POPULATION_KEY = ("nation_id", "year")
_POPULATION_COLUMNS = (
    "nation_id",
    "nation",
    "year",
    "population",
    "source_file",
    "source_path",
    "ingested_at_utc",
    "run_id",
    "content_sha256",
)


def _normalized_observations(bronze_table: str) -> DataFrame:
    """Normalize one Bronze observation table and expose explicit validity flags."""

    source = spark.read.table(SETTINGS.table_name(bronze_table))
    normalized = source.select(
        F.trim("series_id").alias("series_id"),
        F.expr("try_cast(trim(year) as int)").alias("year"),
        F.trim("period").alias("period_code"),
        F.expr("try_cast(trim(value) as decimal(20,6))").alias("value"),
        F.when(F.length(F.trim("footnote_codes")) > 0, F.trim("footnote_codes"))
        .otherwise(F.lit(None).cast("string"))
        .alias("footnote_codes"),
        F.col("_source_file").alias("source_file"),
        F.col("_source_path").alias("source_path"),
        F.col("_ingested_at_utc").alias("ingested_at_utc"),
        F.col("_run_id").alias("run_id"),
        F.col("_content_sha256").alias("content_sha256"),
    )
    return (
        normalized.withColumn("_series_id_valid", F.length("series_id") > 0)
        .withColumn("_year_valid", F.col("year").between(1000, 9999))
        .withColumn(
            "_period_valid",
            F.col("period_code").isin("Q01", "Q02", "Q03", "Q04", "Q05"),
        )
        .withColumn("_value_valid", F.col("value").isNotNull())
        .withColumn(
            "_provenance_valid",
            F.col("source_file").isNotNull()
            & F.col("source_path").isNotNull()
            & F.col("ingested_at_utc").isNotNull()
            & F.col("run_id").isNotNull()
            & F.col("content_sha256").isNotNull(),
        )
    )


_VALID_ROW_RULES = {
    "series_id_is_not_blank": "_series_id_valid",
    "year_is_four_digit_integer": "_year_valid",
    "period_is_supported_bls_code": "_period_valid",
    "value_is_decimal": "_value_valid",
    "provenance_is_complete": "_provenance_valid",
}


@dp.temporary_view(name="silver_bls_observation_candidates")
@dp.expect_all_or_drop(_VALID_ROW_RULES)
def silver_bls_observation_candidates() -> DataFrame:
    return _normalized_observations("bronze_bls_observation_all")


@dp.temporary_view(name="unique_silver_bls_observations")
@dp.expect_or_fail("business_key_is_unique", "_business_key_count = 1")
def unique_silver_bls_observations() -> DataFrame:
    key_window = Window.partitionBy(*_BUSINESS_KEY)
    return spark.read.table("silver_bls_observation_candidates").withColumn(
        "_business_key_count",
        F.count(F.lit(1)).over(key_window),
    )


@dp.temporary_view(name="bls_current_consistency")
@dp.expect_or_fail("current_rows_match_all_data", "mismatch_count = 0")
def bls_current_consistency() -> DataFrame:
    current = _normalized_observations("bronze_bls_observation_current").alias(
        "current"
    )
    all_data = spark.read.table("unique_silver_bls_observations").alias("all_data")
    match = current.join(
        all_data,
        [
            F.col(f"current.{column}") == F.col(f"all_data.{column}")
            for column in (*_BUSINESS_KEY, "value")
        ],
        "left",
    )
    current_row_valid = (
        F.col("current._series_id_valid")
        & F.col("current._year_valid")
        & F.col("current._period_valid")
        & F.col("current._value_valid")
        & F.col("current._provenance_valid")
    )
    return match.agg(
        F.count(F.lit(1)).alias("current_row_count"),
        F.coalesce(
            F.sum(
                F.when(
                    (~current_row_valid) | F.col("all_data.series_id").isNull(),
                    F.lit(1),
                ).otherwise(F.lit(0))
            ),
            F.lit(0),
        ).alias("mismatch_count"),
    )


@dp.materialized_view(
    name="silver_bls_observation",
    comment="Typed, uniquely keyed BLS productivity observations from AllData.",
)
def silver_bls_observation() -> DataFrame:
    observations = spark.read.table("unique_silver_bls_observations")
    consistency = spark.read.table("bls_current_consistency")
    return observations.crossJoin(consistency).select(
        *[F.col(column) for column in _SILVER_COLUMNS]
    )


def _lookup(table: str, code: str, description: str) -> DataFrame:
    """Select one trimmed provider code and description lookup."""

    return spark.read.table(SETTINGS.table_name(table)).select(
        F.trim(code).alias(code),
        F.trim(description).alias(description),
    )


@dp.temporary_view(name="silver_bls_series_candidates")
@dp.expect_or_fail(
    "series_metadata_is_complete_and_unique",
    "_series_match_count = 1 AND _all_lookups_matched",
)
def silver_bls_series_candidates() -> DataFrame:
    """Join each provider series to its applicable descriptive lookups."""

    series = spark.read.table(SETTINGS.table_name("bronze_bls_series")).select(
        F.trim("series_id").alias("series_id"),
        F.trim("sector_code").alias("sector_code"),
        F.trim("class_code").alias("class_code"),
        F.trim("measure_code").alias("measure_code"),
        F.trim("duration_code").alias("duration_code"),
        F.trim("seasonal").alias("seasonal_code"),
        F.expr("try_cast(nullif(trim(base_year), '-') as int)").alias("base_year"),
        F.when(F.length(F.trim("footnote_codes")) > 0, F.trim("footnote_codes"))
        .otherwise(F.lit(None).cast("string"))
        .alias("footnote_codes"),
        F.expr("try_cast(trim(begin_year) as int)").alias("begin_year"),
        F.trim("begin_period").alias("begin_period"),
        F.expr("try_cast(trim(end_year) as int)").alias("end_year"),
        F.trim("end_period").alias("end_period"),
        F.col("_source_file").alias("source_file"),
        F.col("_source_path").alias("source_path"),
        F.col("_ingested_at_utc").alias("ingested_at_utc"),
        F.col("_run_id").alias("run_id"),
        F.col("_content_sha256").alias("content_sha256"),
    )
    joined = (
        series.join(
            _lookup("bronze_bls_sector", "sector_code", "sector_name"),
            "sector_code",
            "left",
        )
        .join(
            _lookup("bronze_bls_class", "class_code", "class_text"),
            "class_code",
            "left",
        )
        .join(
            _lookup("bronze_bls_measure", "measure_code", "measure_text"),
            "measure_code",
            "left",
        )
        .join(
            _lookup("bronze_bls_duration", "duration_code", "duration_text"),
            "duration_code",
            "left",
        )
        .join(
            _lookup("bronze_bls_seasonal", "seasonal_code", "seasonal_text"),
            "seasonal_code",
            "left",
        )
    )
    descriptions = (
        "sector_name",
        "class_text",
        "measure_text",
        "duration_text",
        "seasonal_text",
    )
    return (
        joined.withColumn(
            "series_label",
            F.concat_ws(
                " | ",
                *[F.col(column) for column in descriptions],
            ),
        )
        .withColumn(
            "_series_match_count",
            F.count(F.lit(1)).over(Window.partitionBy("series_id")),
        )
        .withColumn(
            "_all_lookups_matched",
            F.lit(True)
            & F.col("series_id").isNotNull()
            & F.col("begin_year").isNotNull()
            & F.col("end_year").isNotNull()
            & F.col("begin_period").isin("Q01", "Q02", "Q03", "Q04", "Q05")
            & F.col("end_period").isin("Q01", "Q02", "Q03", "Q04", "Q05")
            & F.col("source_path").isNotNull()
            & F.col("content_sha256").isNotNull()
            & F.col(descriptions[0]).isNotNull()
            & F.col(descriptions[1]).isNotNull()
            & F.col(descriptions[2]).isNotNull()
            & F.col(descriptions[3]).isNotNull()
            & F.col(descriptions[4]).isNotNull(),
        )
    )


@dp.materialized_view(
    name="silver_bls_series",
    comment="BLS series metadata with provider-grounded descriptive labels.",
)
def silver_bls_series() -> DataFrame:
    return spark.read.table("silver_bls_series_candidates").select(
        *[F.col(column) for column in _SERIES_COLUMNS]
    )


_POPULATION_RULES = {
    "record_is_us_national_total": "_nation_valid",
    "year_is_exact_integer": "_year_valid",
    "population_is_nonnegative_integer": "_population_valid",
    "population_provenance_is_complete": "_provenance_valid",
}


@dp.temporary_view(name="silver_population_candidates")
@dp.expect_all_or_drop(_POPULATION_RULES)
def silver_population_candidates() -> DataFrame:
    """Normalize the reusable US national population history."""

    source = spark.read.table(SETTINGS.table_name("bronze_datausa_population"))
    normalized = source.select(
        F.trim(F.col("Nation ID")).alias("nation_id"),
        F.trim(F.col("Nation")).alias("nation"),
        F.col("Year").alias("_source_year"),
        F.expr("try_cast(`Year` as int)").alias("year"),
        F.col("Population").alias("_source_population"),
        F.expr("try_cast(`Population` as bigint)").alias("population"),
        F.col("_source_file").alias("source_file"),
        F.col("_source_path").alias("source_path"),
        F.col("_ingested_at_utc").alias("ingested_at_utc"),
        F.col("_run_id").alias("run_id"),
        F.col("_content_sha256").alias("content_sha256"),
    )
    return (
        normalized.withColumn(
            "_nation_valid",
            (F.col("nation_id") == "01000US")
            & (F.col("nation") == "United States"),
        )
        .withColumn(
            "_year_valid",
            F.col("year").isNotNull()
            & (F.col("year").cast("long") == F.col("_source_year")),
        )
        .withColumn(
            "_population_valid",
            F.col("population").isNotNull()
            & (F.col("population") >= 0)
            & ~F.isnan("_source_population")
            & (
                F.col("population").cast("double")
                == F.col("_source_population")
            ),
        )
        .withColumn(
            "_provenance_valid",
            F.col("source_file").isNotNull()
            & F.col("source_path").isNotNull()
            & F.col("ingested_at_utc").isNotNull()
            & F.col("run_id").isNotNull()
            & F.col("content_sha256").isNotNull(),
        )
    )


@dp.temporary_view(name="unique_silver_population")
@dp.expect_or_fail("population_business_key_is_unique", "_key_count = 1")
def unique_silver_population() -> DataFrame:
    key_window = Window.partitionBy(*_POPULATION_KEY)
    return spark.read.table("silver_population_candidates").withColumn(
        "_key_count",
        F.count(F.lit(1)).over(key_window),
    )


@dp.materialized_view(
    name="silver_population",
    comment="Typed annual United States national population history.",
)
def silver_population() -> DataFrame:
    return spark.read.table("unique_silver_population").select(
        *[F.col(column) for column in _POPULATION_COLUMNS]
    )
