# Databricks notebook source
"""Post-submission comparison of repeated Spark work with and without caching.

This controlled experiment uses generated records. It does not read or mutate the
submitted assessment's landing, Bronze, Silver, Gold, manifest, or audit state.
"""

from time import perf_counter

from pyspark import StorageLevel
from pyspark.sql import functions as F


EXPECTED_RESULTS = {
    "0": {"row_count": 20, "value_sum": 1220.0},
    "1": {"row_count": 20, "value_sum": 1180.0},
    "2": {"row_count": 20, "value_sum": 1260.0},
}


def deterministic_input(frame):
    """Return the reusable filtered input shared by both experiment paths."""
    return frame.where(F.pmod(F.col("record_id"), F.lit(2)) == F.lit(1))


def summarize(frame):
    """Apply the same deterministic aggregation to either input path."""
    return (
        frame.groupBy("group_key")
        .agg(
            F.count("*").alias("row_count"),
            F.sum("value").alias("value_sum"),
        )
        .orderBy("group_key")
    )


def normalize(rows):
    """Convert collected summary rows into a deterministic comparison object."""
    return {
        row["group_key"]: {
            "row_count": row["row_count"],
            "value_sum": row["value_sum"],
        }
        for row in rows
    }


source = spark.range(start=0, end=120, step=1, numPartitions=4).select(
    F.col("id").alias("record_id"),
    F.pmod(F.col("id"), F.lit(3)).cast("string").alias("group_key"),
    (F.col("id") + F.lit(1)).cast("double").alias("value"),
)

# COMMAND ----------

# The uncached path executes the same logical result twice without persistence.
uncached_result = summarize(deterministic_input(source))
print("Uncached extended logical and physical plans:")
uncached_result.explain(mode="extended")

uncached_start_1 = perf_counter()
uncached_run_1 = normalize(uncached_result.collect())
uncached_seconds_1 = perf_counter() - uncached_start_1

uncached_start_2 = perf_counter()
uncached_run_2 = normalize(uncached_result.collect())
uncached_seconds_2 = perf_counter() - uncached_start_2

assert uncached_run_1 == EXPECTED_RESULTS
assert uncached_run_2 == EXPECTED_RESULTS

# COMMAND ----------

# Persisting is lazy. count() is the explicit materialization action that fills
# the cache before the repeated summary actions are observed.
cached_source = deterministic_input(source).persist(StorageLevel.MEMORY_AND_DISK)

try:
    cached_row_count = cached_source.count()
    assert cached_row_count == 60

    cached_result = summarize(cached_source)
    print("Cached extended logical and physical plans:")
    cached_result.explain(mode="extended")

    cached_start_1 = perf_counter()
    cached_run_1 = normalize(cached_result.collect())
    cached_seconds_1 = perf_counter() - cached_start_1

    cached_start_2 = perf_counter()
    cached_run_2 = normalize(cached_result.collect())
    cached_seconds_2 = perf_counter() - cached_start_2

    assert cached_run_1 == EXPECTED_RESULTS
    assert cached_run_2 == EXPECTED_RESULTS
    assert uncached_run_1 == cached_run_1

    print(
        {
            "validation": "passed",
            "storage_level": str(cached_source.storageLevel),
            "materialized_row_count": cached_row_count,
            "uncached_run_1_seconds": uncached_seconds_1,
            "uncached_run_2_seconds": uncached_seconds_2,
            "cached_run_1_seconds": cached_seconds_1,
            "cached_run_2_seconds": cached_seconds_2,
            "result_parity": True,
            "runtime_note": (
                "These single-run observations support inspection; they are not "
                "a performance benchmark or a claim that caching is faster."
            ),
        }
    )
finally:
    # Cleanup is part of the experiment contract so cached state does not linger.
    cached_source.unpersist(blocking=True)
