import unittest
from pathlib import Path


class SilverPipelineDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1] / "pipelines" / "silver.py"
        ).read_text(encoding="utf-8")

    def test_reads_only_bronze_observation_inputs(self) -> None:
        self.assertIn('"bronze_bls_observation_all"', self.source)
        self.assertIn('"bronze_bls_observation_current"', self.source)
        self.assertNotIn("binaryFile", self.source)

    def test_declares_intentional_types_and_business_key(self) -> None:
        self.assertIn('.cast("int").alias("year")', self.source)
        self.assertIn('.cast("decimal(20,6)").alias("value")', self.source)
        self.assertIn(
            '_BUSINESS_KEY = ("series_id", "year", "period_code")', self.source
        )
        self.assertIn('"Q01", "Q02", "Q03", "Q04", "Q05"', self.source)

    def test_fails_duplicates_and_current_mismatches(self) -> None:
        self.assertIn(
            '@dp.expect_or_fail("business_key_is_unique",', self.source
        )
        self.assertIn(
            '@dp.expect_or_fail("current_rows_match_all_data",', self.source
        )
        self.assertIn('spark.read.table("bls_current_consistency")', self.source)

    def test_publishes_one_explainable_silver_table(self) -> None:
        self.assertEqual(self.source.count("@dp.materialized_view("), 1)
        self.assertIn('name="silver_bls_observation"', self.source)


if __name__ == "__main__":
    unittest.main()
