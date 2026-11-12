# Databricks notebook source
"""Export deterministic, read-only snapshots of the three governed Gold contracts.

The output is presentation data for the public portfolio application. It does
not become a new source of truth and does not mutate any Gold, manifest, audit,
or pipeline object.
"""

# COMMAND ----------

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import functions as F


dbutils.widgets.text("catalog", "workspace", "Catalog")
dbutils.widgets.text("schema", "rearc_data_quest", "Schema")
dbutils.widgets.text("volume", "raw_landing", "Managed Volume")
dbutils.widgets.text(
    "export_subdir", "_public_portfolio_exports", "Export subdirectory"
)

catalog = dbutils.widgets.get("catalog").strip()
schema = dbutils.widgets.get("schema").strip()
volume = dbutils.widgets.get("volume").strip()
export_subdir = dbutils.widgets.get("export_subdir").strip().strip("/")

identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
for label, value in {
    "catalog": catalog,
    "schema": schema,
    "volume": volume,
    "export_subdir": export_subdir,
}.items():
    if not identifier_pattern.fullmatch(value):
        raise ValueError(f"{label} must be a simple identifier")

snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
export_root = Path(
    f"/Volumes/{catalog}/{schema}/{volume}/{export_subdir}/{snapshot_id}"
)
export_root.mkdir(parents=True, exist_ok=False)

# COMMAND ----------

contracts = {
    "gold_population_summary_2013_2018": {
        "columns": [
            "start_year",
            "end_year",
            "year_count",
            "mean_population",
            "population_stddev",
            "stddev_semantics",
        ],
        "order_by": ["start_year"],
        "expected_rows": 1,
    },
    "gold_bls_best_year_by_series": {
        "columns": [
            "series_id",
            "series_label",
            "best_year",
            "annual_quarterly_sum",
            "quarterly_observation_count",
            "has_quarterly_observations",
        ],
        "order_by": ["series_id"],
        "expected_rows": 282,
    },
    "gold_bls_q01_population": {
        "columns": [
            "series_id",
            "series_label",
            "year",
            "q01_value",
            "population",
            "population_match_found",
        ],
        "order_by": ["series_id", "year"],
        "expected_rows": 39,
    },
}


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def deterministic_csv(frame, columns, order_by):
    selected = frame.select(*columns).orderBy(*order_by)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    for row in selected.collect():
        writer.writerow([csv_value(row[column]) for column in columns])
    return buffer.getvalue()


manifest = {
    "snapshot_id": snapshot_id,
    "exported_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_catalog": catalog,
    "source_schema": schema,
    "purpose": "read-only public portfolio presentation",
    "authoritative_system": "Databricks governed Gold contracts",
    "contracts": {},
}

for table_name, contract in contracts.items():
    table_identifier = f"`{catalog}`.`{schema}`.`{table_name}`"
    frame = spark.read.table(table_identifier)
    actual_columns = frame.columns
    if actual_columns != contract["columns"]:
        raise ValueError(
            f"{table_name} ordered schema mismatch: "
            f"expected {contract['columns']}, observed {actual_columns}"
        )

    actual_rows = frame.count()
    if actual_rows != contract["expected_rows"]:
        raise ValueError(
            f"{table_name} row-count mismatch: "
            f"expected {contract['expected_rows']}, observed {actual_rows}"
        )

    content = deterministic_csv(
        frame, contract["columns"], contract["order_by"]
    )
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    output_name = f"{table_name}.csv"
    (export_root / output_name).write_text(content, encoding="utf-8")
    manifest["contracts"][table_name] = {
        "file": output_name,
        "row_count": actual_rows,
        "columns": contract["columns"],
        "order_by": contract["order_by"],
        "sha256": digest,
    }

# Question-specific integrity gates that prevent a plausible but wrong export.
q2 = spark.read.table(f"`{catalog}`.`{schema}`.`gold_bls_best_year_by_series`")
if q2.select("series_id").distinct().count() != 282:
    raise ValueError("Question 2 must contain 282 unique series_id keys")

q3 = spark.read.table(f"`{catalog}`.`{schema}`.`gold_bls_q01_population`")
q3_integrity = q3.agg(
    F.countDistinct(F.struct("series_id", "year")).alias("distinct_keys"),
    F.sum(F.col("population_match_found").cast("int")).alias("matches"),
).first()
if q3_integrity["distinct_keys"] != 39 or q3_integrity["matches"] != 11:
    raise ValueError(
        "Question 3 must contain 39 unique keys and 11 population matches"
    )

manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
(export_root / "snapshot_manifest.json").write_text(
    manifest_text, encoding="utf-8"
)

print(f"Export complete: {export_root}")
display(spark.createDataFrame([
    (name, details["row_count"], details["sha256"])
    for name, details in manifest["contracts"].items()
], ["contract", "row_count", "sha256"]))

