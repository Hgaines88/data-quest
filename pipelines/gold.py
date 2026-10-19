# Databricks notebook source
"""Publish governed Gold analytical outputs from validated Silver tables."""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


_START_YEAR = 2013
_END_YEAR = 2018
_EXPECTED_YEAR_COUNT = _END_YEAR - _START_YEAR + 1
_Q01_SERIES_ID = "PRS30006032"
_Q01_PERIOD_CODE = "Q01"


@dp.temporary_view(name="gold_population_summary_2013_2018_candidate")
@dp.expect_or_fail(
    "one_population_row_per_requested_year",
    f"_row_count = {_EXPECTED_YEAR_COUNT} "
    f"AND _distinct_year_count = {_EXPECTED_YEAR_COUNT} "
    f"AND _observed_start_year = {_START_YEAR} "
    f"AND _observed_end_year = {_END_YEAR}",
)
def gold_population_summary_2013_2018_candidate() -> DataFrame:
    """Calculate the requested summary after proving complete year coverage."""

    requested_population = spark.read.table("silver_population").filter(
        (F.col("nation_id") == "01000US")
        & (F.col("nation") == "United States")
        & F.col("year").between(_START_YEAR, _END_YEAR)
    )
    return requested_population.agg(
        F.lit(_START_YEAR).cast("int").alias("start_year"),
        F.lit(_END_YEAR).cast("int").alias("end_year"),
        F.count(F.lit(1)).cast("int").alias("year_count"),
        F.avg(F.col("population").cast("double")).alias("mean_population"),
        F.stddev_pop(F.col("population").cast("double")).alias(
            "population_stddev"
        ),
        F.lit("population").alias("stddev_semantics"),
        F.count(F.lit(1)).alias("_row_count"),
        F.countDistinct("year").alias("_distinct_year_count"),
        F.min("year").alias("_observed_start_year"),
        F.max("year").alias("_observed_end_year"),
    )


@dp.materialized_view(
    name="gold_population_summary_2013_2018",
    comment=(
        "Mean and population standard deviation for annual United States "
        "population from 2013 through 2018."
    ),
)
def gold_population_summary_2013_2018() -> DataFrame:
    return spark.read.table(
        "gold_population_summary_2013_2018_candidate"
    ).select(
        "start_year",
        "end_year",
        "year_count",
        "mean_population",
        "population_stddev",
        "stddev_semantics",
    )


@dp.temporary_view(name="gold_bls_series_metadata_validation")
@dp.expect_or_fail(
    "every_quarterly_observation_has_exactly_one_series_metadata_row",
    "_unresolved_series_count = 0",
)
def gold_bls_series_metadata_validation() -> DataFrame:
    """Fail when retained observations lack unambiguous series metadata."""

    quarterly_series = (
        spark.read.table("silver_bls_observation")
        .filter(F.col("period_code").isin("Q01", "Q02", "Q03", "Q04"))
        .select("series_id")
        .distinct()
    )
    metadata_cardinality = spark.read.table("silver_bls_series").groupBy(
        "series_id"
    ).agg(F.count(F.lit(1)).alias("_metadata_row_count"))
    return (
        quarterly_series.join(metadata_cardinality, "series_id", "left")
        .filter(
            F.coalesce(F.col("_metadata_row_count"), F.lit(0)) != F.lit(1)
        )
        .agg(F.count(F.lit(1)).alias("_unresolved_series_count"))
    )


@dp.temporary_view(name="gold_bls_best_year_by_series_candidate")
@dp.expect_or_fail("one_row_per_expected_series", "_series_row_count = 1")
@dp.expect_or_fail(
    "quarterly_result_is_complete_or_visibly_missing",
    "(has_quarterly_observations AND best_year IS NOT NULL "
    "AND annual_quarterly_sum IS NOT NULL AND quarterly_observation_count > 0) "
    "OR (NOT has_quarterly_observations AND best_year IS NULL "
    "AND annual_quarterly_sum IS NULL AND quarterly_observation_count = 0)",
)
def gold_bls_best_year_by_series_candidate() -> DataFrame:
    """Select each expected series' strongest deterministic quarterly year."""

    metadata_validation = spark.read.table(
        "gold_bls_series_metadata_validation"
    )
    expected_series = spark.read.table("silver_bls_series").select(
        "series_id", "series_label"
    )
    quarterly_annual_sums = (
        spark.read.table("silver_bls_observation")
        .filter(F.col("period_code").isin("Q01", "Q02", "Q03", "Q04"))
        .groupBy("series_id", "year")
        .agg(
            F.sum("value").alias("annual_quarterly_sum"),
            F.count(F.lit(1)).cast("int").alias("quarterly_observation_count"),
        )
    )
    ranking = Window.partitionBy("series_id").orderBy(
        F.col("annual_quarterly_sum").desc(), F.col("year").asc()
    )
    best_years = (
        quarterly_annual_sums.withColumn("_rank", F.row_number().over(ranking))
        .filter(F.col("_rank") == 1)
        .drop("_rank")
    )
    return (
        expected_series.join(best_years, "series_id", "left")
        .crossJoin(metadata_validation)
        .withColumnRenamed("year", "best_year")
        .withColumn(
            "has_quarterly_observations", F.col("best_year").isNotNull()
        )
        .withColumn(
            "quarterly_observation_count",
            F.coalesce(F.col("quarterly_observation_count"), F.lit(0)),
        )
        .withColumn(
            "_series_row_count",
            F.count(F.lit(1)).over(Window.partitionBy("series_id")),
        )
    )


@dp.materialized_view(
    name="gold_bls_best_year_by_series",
    comment=(
        "Best Q01-Q04 annual sum for every expected BLS series, with earliest "
        "year winning ties and missing quarterly histories explicitly flagged."
    ),
)
def gold_bls_best_year_by_series() -> DataFrame:
    return spark.read.table("gold_bls_best_year_by_series_candidate").select(
        "series_id",
        "series_label",
        "best_year",
        "annual_quarterly_sum",
        "quarterly_observation_count",
        "has_quarterly_observations",
    )


@dp.temporary_view(name="gold_bls_q01_population_input_validation")
@dp.expect_or_fail(
    "selected_q01_history_is_nonempty_and_uniquely_keyed",
    "_observation_row_count > 0 "
    "AND _distinct_year_count = _observation_row_count",
)
@dp.expect_or_fail(
    "selected_series_has_exactly_one_metadata_row",
    "_metadata_row_count = 1",
)
def gold_bls_q01_population_input_validation() -> DataFrame:
    """Prove the selected history and its provider metadata are unambiguous."""

    selected_observations = (
        spark.read.table("silver_bls_observation")
        .filter(
            (F.col("series_id") == _Q01_SERIES_ID)
            & (F.col("period_code") == _Q01_PERIOD_CODE)
        )
        .agg(
            F.count(F.lit(1)).alias("_observation_row_count"),
            F.countDistinct("year").alias("_distinct_year_count"),
        )
    )
    selected_metadata = (
        spark.read.table("silver_bls_series")
        .filter(F.col("series_id") == _Q01_SERIES_ID)
        .agg(F.count(F.lit(1)).alias("_metadata_row_count"))
    )
    return selected_observations.crossJoin(selected_metadata)


@dp.temporary_view(name="gold_bls_q01_population_candidate")
@dp.expect_or_fail("one_result_row_per_bls_year", "_year_row_count = 1")
@dp.expect_or_fail(
    "population_match_indicator_is_consistent",
    "(population_match_found AND population IS NOT NULL) "
    "OR (NOT population_match_found AND population IS NULL)",
)
def gold_bls_q01_population_candidate() -> DataFrame:
    """Add nullable US population context without dropping any BLS year."""

    validation = spark.read.table(
        "gold_bls_q01_population_input_validation"
    )
    selected_observations = (
        spark.read.table("silver_bls_observation")
        .filter(
            (F.col("series_id") == _Q01_SERIES_ID)
            & (F.col("period_code") == _Q01_PERIOD_CODE)
        )
        .select(
            "series_id",
            "year",
            F.col("value").alias("q01_value"),
        )
    )
    selected_metadata = (
        spark.read.table("silver_bls_series")
        .filter(F.col("series_id") == _Q01_SERIES_ID)
        .select("series_id", "series_label")
    )
    us_population = (
        spark.read.table("silver_population")
        .filter(
            (F.col("nation_id") == "01000US")
            & (F.col("nation") == "United States")
        )
        .select("year", "population")
    )
    return (
        selected_observations.join(selected_metadata, "series_id", "inner")
        .join(us_population, "year", "left")
        .crossJoin(validation)
        .withColumn(
            "population_match_found", F.col("population").isNotNull()
        )
        .withColumn(
            "_year_row_count",
            F.count(F.lit(1)).over(Window.partitionBy("series_id", "year")),
        )
    )


@dp.materialized_view(
    name="gold_bls_q01_population",
    comment=(
        "Q01 values for BLS series PRS30006032 with nullable annual United "
        "States population context; no causal relationship is implied."
    ),
)
def gold_bls_q01_population() -> DataFrame:
    return (
        spark.read.table("gold_bls_q01_population_candidate")
        .select(
            "series_id",
            "series_label",
            "year",
            "q01_value",
            "population",
            "population_match_found",
        )
        .orderBy("year")
    )
