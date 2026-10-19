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


class GoldBlsBestYearDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1] / "pipelines" / "gold.py"
        ).read_text(encoding="utf-8")

    def test_uses_expected_series_inventory_and_validated_observations(self) -> None:
        self.assertIn('spark.read.table("silver_bls_series")', self.source)
        self.assertIn('spark.read.table("silver_bls_observation")', self.source)
        self.assertNotIn('spark.read.table("bronze_', self.source)

    def test_includes_quarters_and_excludes_annual_average(self) -> None:
        self.assertIn(
            '.isin("Q01", "Q02", "Q03", "Q04")', self.source
        )
        best_year_source = self.source.split(
            'name="gold_bls_best_year_by_series_candidate"', 1
        )[1]
        self.assertNotIn('"Q05"', best_year_source)

    def test_selects_earliest_year_when_annual_sums_tie(self) -> None:
        self.assertIn('F.col("annual_quarterly_sum").desc()', self.source)
        self.assertIn('F.col("year").asc()', self.source)
        self.assertIn("F.row_number().over(ranking)", self.source)

    def test_preserves_and_flags_series_without_quarterly_history(self) -> None:
        self.assertIn(
            'expected_series.join(best_years, "series_id", "left")', self.source
        )
        self.assertIn('"has_quarterly_observations"', self.source)
        self.assertIn(
            '"quarterly_result_is_complete_or_visibly_missing"', self.source
        )

    def test_fails_when_an_observation_lacks_unique_series_metadata(self) -> None:
        self.assertIn(
            'name="gold_bls_series_metadata_validation"', self.source
        )
        self.assertIn(
            '"every_quarterly_observation_has_exactly_one_series_metadata_row"',
            self.source,
        )
        self.assertIn(
            'F.coalesce(F.col("_metadata_row_count"), F.lit(0)) != F.lit(1)',
            self.source,
        )
        self.assertIn('"_unresolved_series_count"', self.source)
        self.assertIn(
            'spark.read.table(\n        "gold_bls_series_metadata_validation"',
            self.source,
        )
        self.assertIn(".crossJoin(metadata_validation)", self.source)

    def test_publishes_required_best_year_contract(self) -> None:
        self.assertIn('name="gold_bls_best_year_by_series"', self.source)
        for field in (
            "series_id",
            "series_label",
            "best_year",
            "annual_quarterly_sum",
            "quarterly_observation_count",
            "has_quarterly_observations",
        ):
            self.assertIn(f'"{field}"', self.source)


class GoldBlsQ01PopulationDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1] / "pipelines" / "gold.py"
        ).read_text(encoding="utf-8")

    def test_filters_the_exact_series_and_q01_period(self) -> None:
        self.assertIn('_Q01_SERIES_ID = "PRS30006032"', self.source)
        self.assertIn('_Q01_PERIOD_CODE = "Q01"', self.source)
        self.assertIn(
            '(F.col("series_id") == _Q01_SERIES_ID)', self.source
        )
        self.assertIn(
            '(F.col("period_code") == _Q01_PERIOD_CODE)', self.source
        )

    def test_fails_on_empty_duplicate_or_ambiguous_inputs(self) -> None:
        self.assertIn(
            'name="gold_bls_q01_population_input_validation"', self.source
        )
        self.assertIn(
            '"selected_q01_history_is_nonempty_and_uniquely_keyed"',
            self.source,
        )
        self.assertIn('"_observation_row_count > 0 "', self.source)
        self.assertIn('"_metadata_row_count = 1"', self.source)

    def test_preserves_bls_years_with_a_population_left_join(self) -> None:
        self.assertIn(
            '.join(us_population, "year", "left")', self.source
        )
        self.assertIn(
            '"population_match_found", F.col("population").isNotNull()',
            self.source,
        )
        self.assertIn(
            '"population_match_indicator_is_consistent"', self.source
        )

    def test_publishes_the_ordered_q01_population_contract(self) -> None:
        self.assertIn('name="gold_bls_q01_population"', self.source)
        for field in (
            "series_id",
            "series_label",
            "year",
            "q01_value",
            "population",
            "population_match_found",
        ):
            self.assertIn(f'"{field}"', self.source)
        self.assertIn('.orderBy("year")', self.source)


if __name__ == "__main__":
    unittest.main()
