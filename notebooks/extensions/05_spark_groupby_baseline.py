# Databricks notebook source
"""Post-submission Spark execution baseline for the Data Quest portfolio.

This notebook uses controlled in-memory records. It does not read or mutate the
submitted assessment's landing, Bronze, Silver, Gold, manifest, or audit state.
"""

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)


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

schema = StructType([
    StructField("series_id", StringType(), nullable=False),
    StructField("year", IntegerType(), nullable=False),
    StructField("period", StringType(), nullable=False),
    StructField("value", DoubleType(), nullable=False),
])

# Four input partitions keep the example small while still making partitioned
# execution visible in the Spark UI.
source = spark.createDataFrame(
    spark.sparkContext.parallelize(BASELINE_ROWS, 4),
    schema=schema,
)

print({
    "spark_version": spark.version,
    "spark_master": spark.sparkContext.master,
    "adaptive_execution_enabled": spark.conf.get(
        "spark.sql.adaptive.enabled", "not-set"
    ),
    "shuffle_partitions": spark.conf.get(
        "spark.sql.shuffle.partitions", "not-set"
    ),
    "source_partitions": source.rdd.getNumPartitions(),
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

print({
    "filtered_partitions": filtered.rdd.getNumPartitions(),
    "grouped_partitions_before_action": grouped.rdd.getNumPartitions(),
})

print("Extended logical and physical plans:")
grouped.explain(mode="extended")

# COMMAND ----------

# Transformations above are lazy. This deliberately small collect is the action
# that asks Spark to execute the plan and return the two aggregate rows to the
# driver. The job-group label makes the run easier to locate in the Spark UI.
spark.sparkContext.setJobGroup(
    "data-quest-spark-baseline",
    "Data Quest post-submission groupBy execution baseline",
)

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
    "spark_ui_job_group": "data-quest-spark-baseline",
})
