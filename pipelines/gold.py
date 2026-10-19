# Databricks notebook source
"""Publish governed Gold analytical outputs from validated Silver tables."""

from pyspark import pipelines as dp
from pyspark.sql import DataFrame
from pyspark.sql import functions as F


_START_YEAR = 2013
_END_YEAR = 2018
_EXPECTED_YEAR_COUNT = _END_YEAR - _START_YEAR + 1


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
