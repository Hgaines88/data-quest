import unittest
from pathlib import Path


class SilverPipelineDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1] / "pipelines" / "silver.py"
        ).read_text(encoding="utf-8")

    def test_reads_validated_bronze_inputs(self) -> None:
        self.assertIn('"bronze_bls_observation_all"', self.source)
        self.assertIn('"bronze_bls_observation_current"', self.source)
        for table in (
            "bronze_bls_series",
            "bronze_bls_sector",
            "bronze_bls_class",
            "bronze_bls_measure",
            "bronze_bls_duration",
            "bronze_bls_seasonal",
        ):
            self.assertIn(f'"{table}"', self.source)
        self.assertNotIn("binaryFile", self.source)

    def test_declares_intentional_types_and_business_key(self) -> None:
        self.assertIn(
            'F.expr("try_cast(trim(year) as int)").alias("year")',
            self.source,
        )
        self.assertIn(
            'F.expr("try_cast(trim(value) as decimal(20,6))").alias("value")',
            self.source,
        )
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

    def test_publishes_explainable_silver_tables(self) -> None:
        self.assertEqual(self.source.count("@dp.materialized_view("), 2)
        self.assertIn('name="silver_bls_observation"', self.source)
        self.assertIn('name="silver_bls_series"', self.source)

    def test_series_labels_require_complete_unique_provider_lookups(self) -> None:
        self.assertIn(
            '"series_metadata_is_complete_and_unique",', self.source
        )
        self.assertIn('"_series_match_count = 1 AND _all_lookups_matched"', self.source)
        self.assertIn('F.concat_ws(', self.source)
        self.assertNotIn("Unknown series", self.source)

    def test_series_metadata_uses_contract_types_and_periods(self) -> None:
        self.assertIn(
            'F.expr("try_cast(nullif(trim(base_year), \'-\') as int)")',
            self.source,
        )
        self.assertEqual(
            self.source.count(
                '.isin("Q01", "Q02", "Q03", "Q04", "Q05")'
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
