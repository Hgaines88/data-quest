import unittest
from pathlib import Path


class GoldPopulationSummaryDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1] / "pipelines" / "gold.py"
        ).read_text(encoding="utf-8")

    def test_reads_only_the_validated_silver_population_table(self) -> None:
        self.assertIn('spark.read.table("silver_population")', self.source)
        self.assertNotIn("bronze_", self.source)

    def test_filters_the_exact_us_year_window(self) -> None:
        self.assertIn('(F.col("nation_id") == "01000US")', self.source)
        self.assertIn('(F.col("nation") == "United States")', self.source)
        self.assertIn(
            'F.col("year").between(_START_YEAR, _END_YEAR)', self.source
        )
        self.assertIn("_START_YEAR = 2013", self.source)
        self.assertIn("_END_YEAR = 2018", self.source)

    def test_fails_unless_each_requested_year_occurs_once(self) -> None:
        self.assertIn(
            '@dp.expect_or_fail(\n    "one_population_row_per_requested_year",',
            self.source,
        )
        self.assertIn('F.countDistinct("year")', self.source)
        self.assertIn('F.min("year")', self.source)
        self.assertIn('F.max("year")', self.source)
        self.assertIn('f"_row_count = {_EXPECTED_YEAR_COUNT} "', self.source)
        self.assertIn(
            'f"AND _distinct_year_count = {_EXPECTED_YEAR_COUNT} "', self.source
        )

    def test_uses_population_standard_deviation(self) -> None:
        self.assertIn("F.stddev_pop(", self.source)
        self.assertNotIn("stddev_samp", self.source)
        self.assertIn('F.lit("population").alias("stddev_semantics")', self.source)

    def test_publishes_only_the_required_contract_fields(self) -> None:
        self.assertIn('name="gold_population_summary_2013_2018"', self.source)
        for field in (
            "start_year",
            "end_year",
            "year_count",
            "mean_population",
            "population_stddev",
            "stddev_semantics",
        ):
            self.assertIn(f'"{field}"', self.source)


if __name__ == "__main__":
    unittest.main()
