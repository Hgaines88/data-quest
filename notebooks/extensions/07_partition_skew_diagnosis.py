# Databricks notebook source
"""Post-submission experiment for observing and mitigating Spark partition skew.

This controlled notebook does not read or mutate the submitted assessment's
landing, Bronze, Silver, Gold, manifest, or audit state.
"""

# COMMAND ----------

from pyspark.sql import functions as F


BALANCED_EXPECTED_COUNTS = {"0": 30, "1": 30, "2": 30, "3": 30}
SKEWED_EXPECTED_COUNTS = {"0": 108, "1": 4, "2": 4, "3": 4}
HOT_KEY_SALT_EXPECTED_COUNTS = {"0": 27, "1": 27, "2": 27, "3": 27}
SUMMARY_EXPECTED = {
    "0": {"row_count": 108, "record_id_sum": 5778},
    "1": {"row_count": 4, "record_id_sum": 450},
    "2": {"row_count": 4, "record_id_sum": 454},
    "3": {"row_count": 4, "record_id_sum": 458},
}


balanced = spark.range(start=0, end=120, step=1, numPartitions=4).select(
    F.col("id").alias("record_id"),
    F.pmod(F.col("id"), F.lit(4)).cast("string").alias("group_key"),
    F.spark_partition_id().alias("source_partition_id"),
)

skewed = spark.range(start=0, end=120, step=1, numPartitions=4).select(
    F.col("id").alias("record_id"),
    F.when(F.col("id") < F.lit(108), F.lit("0"))
    .otherwise((F.pmod(F.col("id") - F.lit(108), F.lit(3)) + F.lit(1)).cast("string"))
    .alias("group_key"),
    F.spark_partition_id().alias("source_partition_id"),
)


def key_counts(frame):
    """Return deterministic key counts from a deliberately small result."""
    return {
        row["group_key"]: row["row_count"]
        for row in frame.groupBy("group_key")
        .agg(F.count("*").alias("row_count"))
        .orderBy("group_key")
        .collect()
    }


balanced_counts = key_counts(balanced)
skewed_counts = key_counts(skewed)

assert balanced_counts == BALANCED_EXPECTED_COUNTS, (
    f"balanced distribution mismatch: expected {BALANCED_EXPECTED_COUNTS}, "
    f"observed {balanced_counts}"
)
assert skewed_counts == SKEWED_EXPECTED_COUNTS, (
    f"skewed distribution mismatch: expected {SKEWED_EXPECTED_COUNTS}, "
    f"observed {skewed_counts}"
)

print({
    "validation": "passed",
    "balanced_counts": balanced_counts,
    "skewed_counts": skewed_counts,
})

# COMMAND ----------


def partition_profile(frame):
    """Return observed non-empty partition occupancy via DataFrame APIs."""
    return [
        row.asDict()
        for row in frame.select(F.spark_partition_id().alias("partition_id"))
        .groupBy("partition_id")
        .agg(F.count("*").alias("row_count"))
        .orderBy("partition_id")
        .collect()
    ]


def summary(frame):
    """Collect a deliberately small, deterministic aggregation result."""
    return {
        row["group_key"]: {
            "row_count": row["row_count"],
            "record_id_sum": row["record_id_sum"],
        }
        for row in frame.orderBy("group_key").collect()
    }


# Repartitioning only by the skewed key sends the 108 hot-key records to the
# same hash partition. This is the deliberately unmitigated comparison path.
skewed_by_key = skewed.repartition(4, "group_key")
unsalted_aggregate = skewed_by_key.groupBy("group_key").agg(
    F.count("*").alias("row_count"),
    F.sum("record_id").alias("record_id_sum"),
)

# Deterministic salting divides only the hot key into four partial groups. The
# second aggregation recombines those partials to preserve the public result.
salted = skewed.withColumn(
    "salt_bucket",
    F.when(
        F.col("group_key") == F.lit("0"),
        F.pmod(F.col("record_id"), F.lit(4)).cast("string"),
    ).otherwise(F.lit("0")),
)
salted_by_key_and_bucket = salted.repartition(4, "group_key", "salt_bucket")
salted_partial = salted_by_key_and_bucket.groupBy("group_key", "salt_bucket").agg(
    F.count("*").alias("partial_count"),
    F.sum("record_id").alias("partial_record_id_sum"),
)
mitigated_aggregate = salted_partial.groupBy("group_key").agg(
    F.sum("partial_count").alias("row_count"),
    F.sum("partial_record_id_sum").alias("record_id_sum"),
)

hot_key_salt_counts = {
    row["salt_bucket"]: row["row_count"]
    for row in salted.where(F.col("group_key") == F.lit("0"))
    .groupBy("salt_bucket")
    .agg(F.count("*").alias("row_count"))
    .orderBy("salt_bucket")
    .collect()
}
unsalted_summary = summary(unsalted_aggregate)
mitigated_summary = summary(mitigated_aggregate)

assert hot_key_salt_counts == HOT_KEY_SALT_EXPECTED_COUNTS, (
    f"hot-key salt distribution mismatch: expected {HOT_KEY_SALT_EXPECTED_COUNTS}, "
    f"observed {hot_key_salt_counts}"
)
assert unsalted_summary == SUMMARY_EXPECTED, (
    f"unsalted summary mismatch: expected {SUMMARY_EXPECTED}, "
    f"observed {unsalted_summary}"
)
assert mitigated_summary == unsalted_summary, (
    f"mitigation changed the result: unsalted {unsalted_summary}, "
    f"mitigated {mitigated_summary}"
)

print({
    "skewed_by_key_partition_profile": partition_profile(skewed_by_key),
    "salted_partition_profile": partition_profile(salted_by_key_and_bucket),
    "hot_key_salt_counts": hot_key_salt_counts,
})

print("Unmitigated aggregation plan:")
unsalted_aggregate.explain(mode="extended")
print("Salted two-stage aggregation plan:")
mitigated_aggregate.explain(mode="extended")

print({
    "validation": "passed",
    "unsalted_summary": unsalted_summary,
    "mitigated_summary": mitigated_summary,
    "result_parity": True,
})
