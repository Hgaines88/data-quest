import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "extensions" / "05_spark_groupby_baseline.py"
GUIDE = ROOT / "docs" / "extensions" / "SPARK_EXECUTION_BASELINE.md"
BROADCAST_NOTEBOOK = (
    ROOT / "notebooks" / "extensions" / "06_broadcast_join_comparison.py"
)
BROADCAST_GUIDE = ROOT / "docs" / "extensions" / "BROADCAST_JOIN_COMPARISON.md"
SKEW_NOTEBOOK = ROOT / "notebooks" / "extensions" / "07_partition_skew_diagnosis.py"
SKEW_GUIDE = ROOT / "docs" / "extensions" / "PARTITION_SKEW_DIAGNOSIS.md"
CACHE_NOTEBOOK = ROOT / "notebooks" / "extensions" / "08_cache_reuse_comparison.py"
CACHE_GUIDE = ROOT / "docs" / "extensions" / "CACHE_REUSE_COMPARISON.md"
PARTITION_NOTEBOOK = (
    ROOT / "notebooks" / "extensions" / "09_repartition_coalesce_comparison.py"
)
PARTITION_GUIDE = (
    ROOT / "docs" / "extensions" / "REPARTITION_COALESCE_COMPARISON.md"
)
SYNTHESIS_GUIDE = (
    ROOT / "docs" / "extensions" / "SPARK_INTERNALS_DATA_QUEST_CORRECTION.md"
)
SPARK_PLAN_SCREENSHOT = (
    ROOT / "docs" / "screenshots" / "spark_repartition_plan_live.png"
)
BRONZE_RUN_SCREENSHOT = (
    ROOT / "docs" / "screenshots" / "dq11_bronze_run_completed.png"
)
BRONZE_EXPECTATIONS_SCREENSHOT = (
    ROOT / "docs" / "screenshots" / "dq11_bronze_tables_expectations.png"
)
README = ROOT / "README.md"


class SparkExtensionContractTests(unittest.TestCase):
    def test_baseline_is_an_exported_databricks_notebook(self):
        notebook = NOTEBOOK.read_text(encoding="utf-8")

        self.assertTrue(notebook.startswith("# Databricks notebook source"))
        for required in [
            "spark.range",
            "numPartitions=4",
            "F.spark_partition_id()",
            ".groupBy(",
            ".agg(",
            '.explain(mode="extended")',
            "result_rows = grouped.collect()",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, notebook)

        for forbidden in [
            "spark.sparkContext",
            "spark.conf.get",
            ".rdd",
            "_jdf",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, notebook)

        self.assertLess(
            notebook.index("grouped = filtered.groupBy("),
            notebook.index("result_rows = grouped.collect()"),
        )

    def test_baseline_uses_controlled_data_and_independent_expected_results(self):
        notebook = NOTEBOOK.read_text(encoding="utf-8")

        self.assertIn("BASELINE_ROWS", notebook)
        self.assertIn("EXPECTED_RESULTS", notebook)
        self.assertIn("actual_results", notebook)
        self.assertIn("assert actual_results == EXPECTED_RESULTS", notebook)
        self.assertNotIn("spark.read.table", notebook)
        self.assertNotIn("spark.sql(", notebook)

    def test_guide_preserves_the_post_submission_evidence_boundary(self):
        guide = GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "post-submission",
            "does not modify the submitted assessment",
            "python 3.10",
            "lazy",
            "driver",
            "executor",
            "job",
            "stage",
            "task",
            "shuffle",
            "physical plan",
            "spark ui",
            "what this proves",
            "what this does not prove",
            "live validation",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_baseline_guide_maps_the_narrow_wide_acceptance_evidence(self):
        guide = GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "issue #93 acceptance map",
            "controlled input and verified result",
            "source and filtered partition occupancy",
            "shuffle boundary",
            "transformation versus action",
            "jobs, stages, and tasks",
            "evidence limit",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_broadcast_experiment_compares_and_reconciles_both_join_paths(self):
        notebook = BROADCAST_NOTEBOOK.read_text(encoding="utf-8")

        for required in [
            "spark.range",
            "STANDARD_EXPECTED_RESULTS",
            "standard_join =",
            "broadcast_join =",
            "F.broadcast(dimension)",
            'standard_join.explain(mode="extended")',
            'broadcast_join.explain(mode="extended")',
            "standard_results == STANDARD_EXPECTED_RESULTS",
            "broadcast_results == STANDARD_EXPECTED_RESULTS",
            "standard_results == broadcast_results",
            "partition_profile(facts)",
            "partition_profile(dimension)",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, notebook)

        for forbidden in [
            "spark.sparkContext",
            "spark.conf.get",
            "spark.conf.set",
            ".rdd",
            "_jdf",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, notebook)

    def test_broadcast_guide_states_benefit_risk_and_evidence_boundary(self):
        guide = BROADCAST_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "post-submission",
            "ordinary optimizer selection",
            "explicit broadcast",
            "avoid shuffling the larger input",
            "executor memory",
            "observed",
            "environment-specific",
            "what this proves",
            "what this does not prove",
            "live validated",
            "photonbroadcasthashjoin",
            "resolvedhint",
            "isfinalplan=false",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_skew_experiment_defines_balanced_and_skewed_distributions(self):
        notebook = SKEW_NOTEBOOK.read_text(encoding="utf-8")

        for required in [
            "BALANCED_EXPECTED_COUNTS",
            "SKEWED_EXPECTED_COUNTS",
            "balanced_counts",
            "skewed_counts",
            "assert balanced_counts == BALANCED_EXPECTED_COUNTS",
            "assert skewed_counts == SKEWED_EXPECTED_COUNTS",
            "F.spark_partition_id()",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, notebook)

        self.assertNotIn("spark.read.table", notebook)

    def test_skew_mitigation_recombines_to_the_unsalted_result(self):
        notebook = SKEW_NOTEBOOK.read_text(encoding="utf-8")

        for required in [
            "salt_bucket",
            "HOT_KEY_SALT_EXPECTED_COUNTS",
            "partition_profile",
            "skewed_by_key",
            "salted_by_key_and_bucket",
            "unsalted_summary",
            "mitigated_summary",
            "assert hot_key_salt_counts == HOT_KEY_SALT_EXPECTED_COUNTS",
            "assert mitigated_summary == unsalted_summary",
            '.explain(mode="extended")',
        ]:
            with self.subTest(required=required):
                self.assertIn(required, notebook)

        for forbidden in [
            "spark.sparkContext",
            "spark.conf.get",
            "spark.conf.set",
            ".rdd",
            "_jdf",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, notebook)

    def test_skew_guide_explains_evidence_limits_and_operational_tradeoffs(self):
        guide = SKEW_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "post-submission",
            "balanced",
            "skewed",
            "partition occupancy",
            "spark performance profile",
            "concentrated executor pressure",
            "total cluster capacity",
            "salting",
            "extra shuffle",
            "cardinality",
            "complexity",
            "whole-file parsing",
            "distributed line-oriented reading",
            "observed",
            "environment-specific",
            "what this proves",
            "what this does not prove",
            "live validation",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_skew_guide_records_live_databricks_evidence_without_overclaiming(self):
        guide = SKEW_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "november 12, 2026",
            "108 to 58",
            "54, 58, and 8",
            "four equal 27-record salt buckets",
            "hash placement",
            "did not guarantee equal physical partition occupancy",
            "hashpartitioning(group_key, salt_bucket, 4)",
            "hashpartitioning(group_key, 16)",
            "result_parity",
            "photon",
            "isfinalplan=false",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_cache_experiment_reconciles_uncached_and_persisted_paths(self):
        notebook = CACHE_NOTEBOOK.read_text(encoding="utf-8")

        for required in [
            "spark.range",
            "EXPECTED_RESULTS",
            "uncached_run_1",
            "uncached_run_2",
            "StorageLevel.MEMORY_AND_DISK",
            "cached_source.count()",
            "cached_run_1",
            "cached_run_2",
            "uncached_run_1 == EXPECTED_RESULTS",
            "cached_run_1 == EXPECTED_RESULTS",
            "cached_source.unpersist(blocking=True)",
            '.explain(mode="extended")',
        ]:
            with self.subTest(required=required):
                self.assertIn(required, notebook)

        for forbidden in [
            "spark.sparkContext",
            "spark.conf.get",
            "spark.conf.set",
            ".rdd",
            "_jdf",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, notebook)

    def test_cache_guide_defines_lifecycle_tradeoffs_and_evidence_limits(self):
        guide = CACHE_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "post-submission",
            "same deterministic computation",
            "uncached",
            "memory_and_disk",
            "materialization action",
            "unpersist",
            "memory pressure",
            "eviction",
            "stale",
            "not an automatic optimization",
            "what this proves",
            "what this does not prove",
            "live validation",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_cache_guide_records_live_serverless_evidence_without_overclaiming(self):
        guide = CACHE_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "november 12, 2026",
            "disk serialized 1x replicated",
            "prepareddeltafileindex",
            "photonscan parquet",
            "60",
            "result parity",
            "2.531449",
            "0.742856",
            "0.989433",
            "1.034268",
            "not a benchmark",
            "serverless-specific",
            "isfinalplan=false",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_partition_comparison_reconciles_both_paths_and_records_occupancy(self):
        notebook = PARTITION_NOTEBOOK.read_text(encoding="utf-8")

        for required in [
            "spark.range",
            "numPartitions=4",
            'repartition(2, "group_key")',
            "coalesce(2)",
            "partition_profile(source)",
            "partition_profile(repartitioned)",
            "partition_profile(coalesced)",
            'repartitioned.explain(mode="extended")',
            'coalesced.explain(mode="extended")',
            "EXPECTED_RESULTS",
            "repartitioned_results == EXPECTED_RESULTS",
            "coalesced_results == EXPECTED_RESULTS",
            "source_results == repartitioned_results == coalesced_results",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, notebook)

        for forbidden in [
            "spark.sparkContext",
            "spark.conf.get",
            "spark.conf.set",
            ".rdd",
            "_jdf",
            "spark.read.table",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, notebook)

    def test_partition_guide_defines_shuffle_shape_and_safety_boundaries(self):
        guide = PARTITION_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "post-submission",
            "same controlled baseline",
            "repartition",
            "coalesce",
            "full shuffle",
            "narrow",
            "partition occupancy",
            "reducing partitions",
            "rebalancing data",
            "small files",
            "parallelism",
            "skew",
            "result parity",
            "what this proves",
            "what this does not prove",
            "live validation",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)

    def test_partition_guide_records_live_serverless_evidence_without_overclaiming(self):
        guide = PARTITION_GUIDE.read_text(encoding="utf-8").lower()

        for required in [
            "november 12, 2026",
            "30, 30, 30, and 30",
            "40 and 80",
            "60 and 60",
            "repartition_by_num",
            "hashpartitioning(group_key",
            "coalesce 2",
            "no shuffle exchange",
            "not fully supported by photon",
            "result parity",
            "not a performance benchmark",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, guide)


    def test_synthesis_guide_connects_live_evidence_to_original_correction(self):
        text = SYNTHESIS_GUIDE.read_text(encoding="utf-8").lower()
        for required in (
            "whole-file",
            "unsaferow.copy",
            "jvm_out_of_memory",
            "distributed line-oriented",
            "narrow",
            "wide",
            "broadcast",
            "skew",
            "salting",
            "cache",
            "repartition",
            "coalesce",
            "adaptive query execution",
            "aqe",
            "observed environment evidence",
            "general spark guidance",
            "what this does not prove",
            "90-second",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_synthesis_guide_links_live_evidence_artifacts(self):
        text = SYNTHESIS_GUIDE.read_text(encoding="utf-8")
        for relative_path in (
            "../screenshots/spark_repartition_plan_live.png",
            "../screenshots/dq11_bronze_run_completed.png",
            "../screenshots/dq11_bronze_tables_expectations.png",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertIn(relative_path, text)

        for screenshot in (
            SPARK_PLAN_SCREENSHOT,
            BRONZE_RUN_SCREENSHOT,
            BRONZE_EXPECTATIONS_SCREENSHOT,
        ):
            with self.subTest(screenshot=screenshot.name):
                self.assertTrue(screenshot.exists(), screenshot)
                self.assertEqual(screenshot.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_readme_maps_all_spark_extension_notebooks(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn(
            "docs/extensions/SPARK_INTERNALS_DATA_QUEST_CORRECTION.md",
            text,
        )
        for notebook_name in (
            "05_spark_groupby_baseline.py",
            "06_broadcast_join_comparison.py",
            "07_partition_skew_diagnosis.py",
            "08_cache_reuse_comparison.py",
            "09_repartition_coalesce_comparison.py",
        ):
            with self.subTest(notebook_name=notebook_name):
                self.assertIn(f"notebooks/extensions/{notebook_name}", text)


if __name__ == "__main__":
    unittest.main()
