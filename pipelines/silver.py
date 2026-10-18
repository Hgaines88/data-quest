# Databricks notebook source
"""Publish typed, uniquely keyed BLS observations from validated Bronze tables."""

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


def _normalized_observations(bronze_table: str) -> DataFrame:
    """Normalize one Bronze observation table and expose explicit validity flags."""

    source = spark.read.table(SETTINGS.table_name(bronze_table))
    normalized = source.select(
        F.trim("series_id").alias("series_id"),
        F.trim("year").cast("int").alias("year"),
        F.trim("period").alias("period_code"),
        F.trim("value").cast("decimal(20,6)").alias("value"),
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
