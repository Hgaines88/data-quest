# Databricks notebook source
"""Publish source-shaped Bronze tables from governed raw landing objects.

The pipeline deliberately resolves immutable objects through the latest active
manifest state.  It never treats every object below the Volume as current.
Configure ``data_quest.catalog``, ``data_quest.schema``, and
``data_quest.volume`` on the pipeline when the deployment differs from the
project defaults.
"""

from pathlib import Path
import sys

from pyspark import pipelines as dp
from pyspark.sql import Column, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T


def _find_repository_root() -> Path:
    current = Path.cwd()
    for candidate in (current, *current.parents):
        if (candidate / "src" / "data_quest").is_dir():
            return candidate
    raise RuntimeError("could not locate the data-quest repository root")


REPOSITORY_ROOT = _find_repository_root()
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from data_quest.validation.bronze_contract import (  # noqa: E402
    BLS_BRONZE_SPECS,
    BlsBronzeSpec,
    PipelineSettings,
)


SETTINGS = PipelineSettings(
    catalog=spark.conf.get("data_quest.catalog", "workspace"),
    schema=spark.conf.get("data_quest.schema", "rearc_data_quest"),
    volume=spark.conf.get("data_quest.volume", "raw_landing"),
)

_AUDIT_COLUMNS = (
    "source_file",
    "active_object_valid",
    "schema_valid",
    "content_nonempty",
)


def _latest_active_manifest(table_name: str) -> DataFrame:
    """Return one deterministic latest active state per logical source path."""

    ordering = Window.partitionBy("relative_path").orderBy(
        F.col("ingested_at_utc").desc(),
        F.col("run_id").desc(),
        F.col("content_sha256").desc(),
    )
    return (
        spark.read.table(table_name)
        .withColumn("_manifest_rank", F.row_number().over(ordering))
        .where((F.col("_manifest_rank") == 1) & (F.col("status") == "active"))
        .drop("_manifest_rank")
    )


def _active_objects(manifest_table: str, object_glob: str) -> DataFrame:
    """Enumerate provider objects, then retain exact active manifest paths."""

    manifest = _latest_active_manifest(manifest_table).select(
        "relative_path",
        "landed_path",
        "content_sha256",
        "content_size_bytes",
        "ingested_at_utc",
        "run_id",
    )
    objects = (
        spark.read.format("binaryFile")
        .load(object_glob)
        .select(
            F.regexp_replace("path", r"^dbfs:", "").alias("_physical_path"),
            F.col("length").alias("_physical_size_bytes"),
            "content",
        )
    )
    return (
        F.broadcast(manifest)
        .join(
            objects,
            F.regexp_replace(manifest.landed_path, r"^dbfs:", "")
            == objects._physical_path,
            "left",
        )
        .withColumn(
            "_object_valid",
            F.col("content").isNotNull()
            & (F.col("_physical_size_bytes") == F.col("content_size_bytes"))
            & (F.sha2("content", 256) == F.col("content_sha256")),
        )
    )


def _bls_rows(spec: BlsBronzeSpec) -> DataFrame:
    source = (
        spark.read.table("verified_bls_sources")
        .where(F.col("relative_path") == spec.relative_path)
        .select(
            "relative_path",
            "landed_path",
            "content_sha256",
            "content_size_bytes",
            "ingested_at_utc",
            "run_id",
            "_object_valid",
            "_header_valid",
            F.posexplode("_lines").alias("_line_number", "_line"),
        )
        .where((F.col("_line_number") > 0) & (F.length(F.col("_line")) > 0))
        .withColumn("_fields", F.split("_line", "\t", -1))
        .withColumn("_field_count_valid", F.size("_fields") == len(spec.columns))
    )

    projected = [
        F.element_at("_fields", position).alias(column)
        for position, column in enumerate(spec.columns, start=1)
    ]
    return rows_with_provenance(
        source,
        projected,
        source_file=spec.relative_path,
    )


def rows_with_provenance(
    source: DataFrame,
    projected: list[Column],
    *,
    source_file: str | Column,
) -> DataFrame:
    """Project source fields while retaining structural gates and provenance."""

    source_file_column = (
        F.lit(source_file) if isinstance(source_file, str) else source_file
    )
    return source.select(
        *projected,
        source_file_column.alias("_source_file"),
        F.col("landed_path").alias("_source_path"),
        F.col("ingested_at_utc").alias("_ingested_at_utc"),
        F.col("run_id").alias("_run_id"),
        F.col("content_sha256").alias("_content_sha256"),
        "_object_valid",
        "_header_valid",
        "_field_count_valid",
    )


def _register_bls_table(spec: BlsBronzeSpec) -> None:
    fail_rules = {
        "active_object_exists_and_matches_manifest": "_object_valid",
        "ordered_header_matches_contract": "_header_valid",
        "row_width_matches_header": "_field_count_valid",
    }
    drop_rules = {
        f"required_{column}_is_not_blank": f"trim(`{column}`) <> ''"
        for column in spec.required_nonblank
    }

    @dp.materialized_view(
        name=spec.table_name,
        comment=f"Source-shaped Bronze records from {spec.relative_path}.",
    )
    @dp.expect_all_or_fail(fail_rules)
    @dp.expect_all_or_drop(drop_rules)
    def bls_table(specification: BlsBronzeSpec = spec) -> DataFrame:
        return _bls_rows(specification)


_DATAUSA_RECORD_TYPE = T.ArrayType(
    T.MapType(T.StringType(), T.StringType(), valueContainsNull=True)
)
_DATAUSA_COLUMNS_TYPE = T.ArrayType(T.StringType())
_DATAUSA_PAGE_TYPE = T.MapType(T.StringType(), T.LongType(), valueContainsNull=True)
_DATAUSA_ANNOTATIONS_TYPE = T.MapType(
    T.StringType(), T.StringType(), valueContainsNull=True
)
_DATAUSA_TOP_LEVEL_KEYS = ("annotations", "columns", "data", "page")
_DATAUSA_COLUMNS = ("Nation ID", "Nation", "Year", "Population")


def _verified_bls_source_rows() -> DataFrame:
    expected = spark.createDataFrame(
        [
            (spec.relative_path, list(spec.columns))
            for spec in BLS_BRONZE_SPECS
        ],
        "relative_path STRING, expected_columns ARRAY<STRING>",
    )
    active = _active_objects(
        SETTINGS.bls_manifest_table,
        SETTINGS.bls_object_glob,
    )
    return (
        expected.join(active, "relative_path", "left")
        .withColumn("_text", F.decode("content", "UTF-8"))
        .withColumn(
            "_lines",
            F.split(F.regexp_replace("_text", "\\r\\n?", "\n"), "\n", -1),
        )
        .withColumn(
            "_data_lines",
            F.filter(
                F.slice("_lines", 2, F.greatest(F.size("_lines") - 1, F.lit(0))),
                lambda line: F.length(line) > 0,
            ),
        )
        .withColumn(
            "_object_valid",
            F.coalesce("_object_valid", F.lit(False)),
        )
        .withColumn(
            "_header_valid",
            F.transform(
                F.split(F.element_at("_lines", 1), "\t", -1),
                lambda value: F.trim(value),
            )
            == F.col("expected_columns"),
        )
        .withColumn(
            "_content_nonempty",
            F.coalesce(F.size("_data_lines") > 0, F.lit(False)),
        )
    )


def _verified_datausa_source_rows() -> DataFrame:
    expected = spark.createDataFrame([("population.json",)], "relative_path STRING")
    active = _active_objects(
        SETTINGS.datausa_manifest_table,
        SETTINGS.datausa_object_glob,
    ).where(F.col("relative_path") == "population.json")
    return (
        expected.join(active, "relative_path", "left")
        .withColumn("_text", F.decode("content", "UTF-8"))
        .withColumn("_keys", F.array_sort(F.json_object_keys("_text")))
        .withColumn(
            "_columns",
            F.from_json(F.get_json_object("_text", "$.columns"), _DATAUSA_COLUMNS_TYPE),
        )
        .withColumn(
            "_annotations",
            F.from_json(
                F.get_json_object("_text", "$.annotations"),
                _DATAUSA_ANNOTATIONS_TYPE,
            ),
        )
        .withColumn(
            "_records",
            F.from_json(F.get_json_object("_text", "$.data"), _DATAUSA_RECORD_TYPE),
        )
        .withColumn(
            "_page",
            F.from_json(F.get_json_object("_text", "$.page"), _DATAUSA_PAGE_TYPE),
        )
        .withColumn(
            "_record_keys_valid",
            F.expr(
                "forall(_records, record -> "
                "array_sort(map_keys(record)) = "
                "array('Nation', 'Nation ID', 'Population', 'Year'))"
            ),
        )
        .withColumn(
            "_page_valid",
            (
                F.array_sort(F.map_keys("_page"))
                == F.array(F.lit("limit"), F.lit("offset"), F.lit("total"))
            )
            & (F.element_at("_page", "offset") == 0)
            & (F.element_at("_page", "total") == F.size("_records"))
            & (
                (F.element_at("_page", "limit") == 0)
                | (F.element_at("_page", "limit") >= F.size("_records"))
            ),
        )
        .withColumn(
            "_object_valid",
            F.coalesce("_object_valid", F.lit(False)),
        )
        .withColumn(
            "_header_valid",
            (
                F.col("_keys")
                == F.array(*[F.lit(key) for key in _DATAUSA_TOP_LEVEL_KEYS])
            )
            & F.col("_annotations").isNotNull()
            & (
                F.col("_columns")
                == F.array(*[F.lit(column) for column in _DATAUSA_COLUMNS])
            )
            & F.col("_record_keys_valid")
            & F.col("_page_valid"),
        )
        .withColumn(
            "_content_nonempty",
            F.coalesce(F.size("_records") > 0, F.lit(False)),
        )
    )


@dp.temporary_view(name="verified_bls_sources")
@dp.expect_all_or_fail(
    {
        "active_object_exists_and_matches_manifest": "_object_valid",
        "ordered_header_matches_contract": "_header_valid",
        "source_contains_records": "_content_nonempty",
    }
)
def verified_bls_sources() -> DataFrame:
    return _verified_bls_source_rows()


@dp.temporary_view(name="verified_datausa_source")
@dp.expect_all_or_fail(
    {
        "active_object_exists_and_matches_manifest": "_object_valid",
        "json_contract_matches": "_header_valid",
        "source_contains_records": "_content_nonempty",
    }
)
def verified_datausa_source() -> DataFrame:
    return _verified_datausa_source_rows()


for _specification in BLS_BRONZE_SPECS:
    _register_bls_table(_specification)


@dp.materialized_view(
    name="bronze_source_contract_audit",
    comment="One structural quality result for every required Bronze source.",
)
def bronze_source_contract_audit() -> DataFrame:
    bls = spark.read.table("verified_bls_sources").select(
        F.col("relative_path").alias("source_file"),
        F.col("_object_valid").alias("active_object_valid"),
        F.col("_header_valid").alias("schema_valid"),
        F.col("_content_nonempty").alias("content_nonempty"),
    )
    datausa = spark.read.table("verified_datausa_source").select(
        F.col("relative_path").alias("source_file"),
        F.col("_object_valid").alias("active_object_valid"),
        F.col("_header_valid").alias("schema_valid"),
        F.col("_content_nonempty").alias("content_nonempty"),
    )
    return bls.unionByName(datausa).select(*_AUDIT_COLUMNS)


def _datausa_rows() -> DataFrame:
    source = (
        spark.read.table("verified_datausa_source")
        .withColumn("_record", F.explode("_records"))
        .withColumn("_field_count_valid", F.col("_header_valid"))
    )
    return rows_with_provenance(
        source,
        [
            F.element_at("_record", "Nation ID").alias("Nation ID"),
            F.element_at("_record", "Nation").alias("Nation"),
            F.element_at("_record", "Year").cast("long").alias("Year"),
            F.element_at("_record", "Population").cast("double").alias("Population"),
        ],
        source_file=F.col("relative_path"),
    )


@dp.materialized_view(
    name="bronze_datausa_population",
    comment="Source-shaped national population records from Data USA.",
    table_properties={"delta.columnMapping.mode": "name"},
)
@dp.expect_all_or_fail(
    {
        "active_object_exists_and_matches_manifest": "_object_valid",
        "json_envelope_and_columns_match_contract": "_header_valid",
        "record_keys_and_pagination_match_contract": "_field_count_valid",
    }
)
@dp.expect_all_or_drop(
    {
        "nation_id_is_not_blank": "trim(`Nation ID`) <> ''",
        "nation_is_not_blank": "trim(`Nation`) <> ''",
        "year_is_not_null": "`Year` IS NOT NULL",
        "population_is_nonnegative": "`Population` IS NOT NULL AND `Population` >= 0",
    }
)
def bronze_datausa_population() -> DataFrame:
    return _datausa_rows()
