# Databricks notebook source
"""Post-submission comparison of ordinary and explicit broadcast joins.

This controlled experiment does not read or mutate the submitted assessment's
landing, Bronze, Silver, Gold, manifest, or audit state.
"""

# COMMAND ----------

from pyspark.sql import functions as F


STANDARD_EXPECTED_RESULTS = {
    "0": {"series_name": "Series A", "row_count": 40, "amount_sum": 2380.0},
    "1": {"series_name": "Series B", "row_count": 40, "amount_sum": 2420.0},
    "2": {"series_name": "Series C", "row_count": 40, "amount_sum": 2460.0},
}

# The fact side is intentionally larger and begins in four partitions.
facts = spark.range(start=0, end=120, step=1, numPartitions=4).select(
    F.col("id").alias("fact_id"),
    F.pmod(F.col("id"), F.lit(3)).cast("string").alias("series_id"),
    (F.col("id") + F.lit(1)).cast("double").alias("amount"),
)

# The dimension side has three rows in two requested partitions.
dimension = spark.range(start=0, end=3, step=1, numPartitions=2).select(
    F.col("id").cast("string").alias("series_id"),
    F.element_at(
        F.array(F.lit("Series A"), F.lit("Series B"), F.lit("Series C")),
        (F.col("id") + F.lit(1)).cast("int"),
    ).alias("series_name"),
)


def partition_profile(frame):
    """Observe non-empty partition occupancy through serverless-safe APIs."""
    rows = (
        frame.select(F.spark_partition_id().alias("partition_id"))
        .groupBy("partition_id")
        .agg(F.count("*").alias("row_count"))
        .orderBy("partition_id")
        .collect()
    )
    return [row.asDict() for row in rows]


facts_profile = partition_profile(facts)
dimension_profile = partition_profile(dimension)
print({
    "spark_version": spark.version,
    "facts": {
        "row_count": sum(row["row_count"] for row in facts_profile),
        "partition_profile": facts_profile,
    },
    "dimension": {
        "row_count": sum(row["row_count"] for row in dimension_profile),
        "partition_profile": dimension_profile,
    },
})

# COMMAND ----------

# Spark chooses the strategy for this path from the available statistics and
# runtime rules. A tiny dimension may already be selected for broadcasting.
standard_join = facts.join(dimension, on="series_id", how="left")

# This path explicitly supplies the engineering judgment that the dimension is
# small enough to replicate to workers.
broadcast_join = facts.join(
    F.broadcast(dimension),
    on="series_id",
    how="left",
)

print("Standard join: extended logical and physical plans")
standard_join.explain(mode="extended")

print("Explicit broadcast join: extended logical and physical plans")
broadcast_join.explain(mode="extended")

# COMMAND ----------


def summarize(frame):
    """Return a deterministic, small summary for result reconciliation."""
    rows = (
        frame.groupBy("series_id", "series_name")
        .agg(
            F.count("*").alias("row_count"),
            F.sum("amount").alias("amount_sum"),
        )
        .orderBy("series_id")
        .collect()
    )
    return {
        row["series_id"]: {
            "series_name": row["series_name"],
            "row_count": row["row_count"],
            "amount_sum": row["amount_sum"],
        }
        for row in rows
    }


standard_results = summarize(standard_join)
broadcast_results = summarize(broadcast_join)

assert standard_results == STANDARD_EXPECTED_RESULTS, (
    f"standard join mismatch: expected {STANDARD_EXPECTED_RESULTS}, "
    f"observed {standard_results}"
)
assert broadcast_results == STANDARD_EXPECTED_RESULTS, (
    f"broadcast join mismatch: expected {STANDARD_EXPECTED_RESULTS}, "
    f"observed {broadcast_results}"
)
assert standard_results == broadcast_results, (
    "ordinary and explicit broadcast paths produced different summaries"
)

print({
    "validation": "passed",
    "standard_results": standard_results,
    "broadcast_results": broadcast_results,
    "result_parity": True,
})
