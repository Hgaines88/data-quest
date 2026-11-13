# Databricks notebook source
"""Post-submission comparison of repartition and coalesce behavior.

This controlled experiment uses generated records. It does not read or mutate the
submitted assessment's landing, Bronze, Silver, Gold, manifest, or audit state.
"""

from pyspark.sql import functions as F


EXPECTED_RESULTS = {
    "0": {"row_count": 40, "value_sum": 2380.0},
    "1": {"row_count": 40, "value_sum": 2420.0},
    "2": {"row_count": 40, "value_sum": 2460.0},
}


def partition_profile(frame):
    """Return observed non-empty partition occupancy using DataFrame APIs."""
    rows = (
        frame.select(F.spark_partition_id().alias("partition_id"))
        .groupBy("partition_id")
        .agg(F.count("*").alias("row_count"))
        .orderBy("partition_id")
        .collect()
    )
    return [row.asDict() for row in rows]


def summarize(frame):
    """Return the shared deterministic result used to reconcile all paths."""
    return (
        frame.groupBy("group_key")
        .agg(
            F.count("*").alias("row_count"),
            F.sum("value").alias("value_sum"),
        )
        .orderBy("group_key")
    )


def normalize(rows):
    """Convert collected results into a stable comparison object."""
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

# repartition requests a key-based redistribution through a shuffle. coalesce
# reduces adjacent partitions without a full redistribution of the records.
repartitioned = source.repartition(2, "group_key")
coalesced = source.coalesce(2)

# COMMAND ----------

source_profile = partition_profile(source)
repartitioned_profile = partition_profile(repartitioned)
coalesced_profile = partition_profile(coalesced)

print(
    {
        "source_partition_profile": source_profile,
        "repartitioned_partition_profile": repartitioned_profile,
        "coalesced_partition_profile": coalesced_profile,
    }
)

assert sum(row["row_count"] for row in source_profile) == 120
assert sum(row["row_count"] for row in repartitioned_profile) == 120
assert sum(row["row_count"] for row in coalesced_profile) == 120
assert len(source_profile) == 4
assert 1 <= len(repartitioned_profile) <= 2
assert 1 <= len(coalesced_profile) <= 2

# COMMAND ----------

print("Repartition extended logical and physical plans:")
repartitioned.explain(mode="extended")

print("Coalesce extended logical and physical plans:")
coalesced.explain(mode="extended")

# COMMAND ----------

source_results = normalize(summarize(source).collect())
repartitioned_results = normalize(summarize(repartitioned).collect())
coalesced_results = normalize(summarize(coalesced).collect())

assert source_results == EXPECTED_RESULTS
assert repartitioned_results == EXPECTED_RESULTS
assert coalesced_results == EXPECTED_RESULTS
assert source_results == repartitioned_results == coalesced_results

print(
    {
        "validation": "passed",
        "requested_source_partitions": 4,
        "requested_repartition_partitions": 2,
        "requested_coalesce_partitions": 2,
        "observed_source_partition_profile": source_profile,
        "observed_repartitioned_partition_profile": repartitioned_profile,
        "observed_coalesced_partition_profile": coalesced_profile,
        "result_parity": True,
        "evidence_note": (
            "Partition occupancy and plans are runtime observations; equal requested "
            "partition counts do not imply equal record distribution."
        ),
    }
)
