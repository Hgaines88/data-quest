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


if __name__ == "__main__":
    unittest.main()
