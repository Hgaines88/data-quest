# Databricks notebook source
"""Post-submission Spark execution baseline for the Data Quest portfolio.

This notebook uses controlled in-memory records. It does not read or mutate the
submitted assessment's landing, Bronze, Silver, Gold, manifest, or audit state.
"""

# COMMAND ----------

from pyspark.sql import functions as F


BASELINE_ROWS = [
    ("A", 2020, "Q01", 1.0),
    ("A", 2020, "Q02", 2.0),
    ("A", 2020, "Q03", -99.0),
    ("B", 2020, "Q01", 4.0),
    ("B", 2020, "Q02", 6.0),
    ("B", 2020, "Q03", 10.0),
    ("C", 2020, "Q01", -1.0),
]

EXPECTED_RESULTS = {
    "A": {"observation_count": 2, "value_sum": 3.0},
    "B": {"observation_count": 3, "value_sum": 20.0},
}

# Four input partitions keep the example small while still making partitioned
# execution visible in the Spark UI. spark.range stays inside the DataFrame API,
# which also makes the experiment compatible with Databricks serverless compute.
row_index = spark.range(
    start=0,
    end=len(BASELINE_ROWS),
    step=1,
    numPartitions=4,
)


def literal_array(values, data_type):
    """Build a typed literal array for the controlled seven-row fixture."""
    return F.array(*[F.lit(value).cast(data_type) for value in values])


array_index = (F.col("id") + F.lit(1)).cast("int")
source = row_index.select(
    F.element_at(
        literal_array([row[0] for row in BASELINE_ROWS], "string"),
        array_index,
    ).alias("series_id"),
    F.element_at(
        literal_array([row[1] for row in BASELINE_ROWS], "int"),
        array_index,
    ).alias("year"),
    F.element_at(
        literal_array([row[2] for row in BASELINE_ROWS], "string"),
        array_index,
    ).alias("period"),
    F.element_at(
        literal_array([row[3] for row in BASELINE_ROWS], "double"),
        array_index,
    ).alias("value"),
)

print({
    "spark_version": spark.version,
    "compute_interface": "serverless-compatible DataFrame API",
    "configuration_note": (
        "Managed serverless settings are inferred from the physical plan and "
        "query profile; restricted configuration keys are not queried."
    ),
})

# COMMAND ----------

# This filter is a narrow transformation: an output record depends on one input
# partition and no same-key records must be brought together yet.
filtered = source.where(F.col("value") >= F.lit(0.0))

# This aggregation is wide: records sharing a series_id may begin in different
# partitions, so Spark must redistribute them by key before producing totals.
grouped = filtered.groupBy("series_id").agg(
    F.count("*").alias("observation_count"),
    F.sum("value").alias("value_sum"),
)

print("Extended logical and physical plans:")
grouped.explain(mode="extended")

# COMMAND ----------

# Transformations above are lazy. This deliberately small collect is the action
# that asks Spark to execute the plan and return the two aggregate rows to the
# driver. In serverless compute, identify this command in the query profile by
# the notebook name and execution timestamp rather than a SparkContext job group.

result_rows = grouped.collect()
actual_results = {
    row["series_id"]: {
        "observation_count": row["observation_count"],
        "value_sum": row["value_sum"],
    }
    for row in result_rows
}

assert actual_results == EXPECTED_RESULTS, (
    f"baseline result mismatch: expected {EXPECTED_RESULTS}, "
    f"observed {actual_results}"
)

print({
    "validation": "passed",
    "actual_results": actual_results,
    "query_identifier": "05_spark_groupby_baseline / aggregate command",
})

# COMMAND ----------


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


# These are explicit instrumentation actions and therefore create additional
# query-profile entries. They measure observed occupancy; they do not predict a
# fixed task count for every runtime or Adaptive Query Execution decision.
print({
    "source_partition_profile": partition_profile(source),
    "filtered_partition_profile": partition_profile(filtered),
})
