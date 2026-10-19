import unittest
from pathlib import Path


class GoldPopulationSummarySqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1]
            / "sql"
            / "alternatives"
            / "question_1_population_summary.sql"
        ).read_text(encoding="utf-8").upper()

    def test_reads_silver_and_filters_the_exact_us_year_window(self) -> None:
        self.assertIn("FROM WORKSPACE.REARC_DATA_QUEST.SILVER_POPULATION", self.source)
        self.assertIn("NATION_ID = '01000US'", self.source)
        self.assertIn("NATION = 'UNITED STATES'", self.source)
        self.assertIn("YEAR BETWEEN 2013 AND 2018", self.source)
        self.assertNotIn("BRONZE_", self.source)

    def test_enforces_complete_unique_year_coverage(self) -> None:
        self.assertIn("COUNT(DISTINCT YEAR)", self.source)
        self.assertIn("WHERE YEAR_COUNT = 6", self.source)
        self.assertIn("AND DISTINCT_YEAR_COUNT = 6", self.source)
        self.assertIn("AND OBSERVED_START_YEAR = 2013", self.source)
        self.assertIn("AND OBSERVED_END_YEAR = 2018", self.source)

    def test_uses_population_standard_deviation(self) -> None:
        self.assertIn("STDDEV_POP(", self.source)
        self.assertNotIn("STDDEV_SAMP", self.source)
        self.assertIn("'POPULATION' AS STDDEV_SEMANTICS", self.source)


class GoldBlsBestYearSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1]
            / "sql"
            / "alternatives"
            / "question_2_bls_best_year.sql"
        ).read_text(encoding="utf-8").upper()

    def test_uses_only_quarterly_silver_observations(self) -> None:
        self.assertIn(
            "FROM WORKSPACE.REARC_DATA_QUEST.SILVER_BLS_OBSERVATION", self.source
        )
        self.assertIn("PERIOD_CODE IN ('Q01', 'Q02', 'Q03', 'Q04')", self.source)
        where_clause = self.source.split("WHERE PERIOD_CODE", 1)[1]
        self.assertNotIn("Q05", where_clause)
        self.assertNotIn("BRONZE_", self.source)

    def test_uses_deterministic_best_year_ranking(self) -> None:
        self.assertIn("SUM(VALUE) AS ANNUAL_QUARTERLY_SUM", self.source)
        self.assertIn("PARTITION BY SERIES_ID", self.source)
        self.assertIn("ORDER BY ANNUAL_QUARTERLY_SUM DESC, YEAR ASC", self.source)
        self.assertIn("RANKED.RESULT_RANK = 1", self.source)

    def test_preserves_and_flags_the_expected_series_inventory(self) -> None:
        self.assertIn(
            "FROM WORKSPACE.REARC_DATA_QUEST.SILVER_BLS_SERIES AS SERIES",
            self.source,
        )
        self.assertIn("LEFT JOIN RANKED_YEARS AS RANKED", self.source)
        self.assertIn("AS HAS_QUARTERLY_OBSERVATIONS", self.source)
        self.assertIn("COALESCE(RANKED.QUARTERLY_OBSERVATION_COUNT, 0)", self.source)

    def test_rejects_quarterly_series_without_unique_metadata(self) -> None:
        self.assertIn("METADATA_CARDINALITY AS", self.source)
        self.assertIn("UNRESOLVED_QUARTERLY_SERIES AS", self.source)
        self.assertIn(
            "COALESCE(METADATA.METADATA_ROW_COUNT, 0) <> 1", self.source
        )
        self.assertIn("RAISE_ERROR(", self.source)
        self.assertIn("INNER JOIN METADATA_VALIDATION AS VALIDATION", self.source)
        self.assertIn("ON VALIDATION.METADATA_IS_VALID", self.source)


class GoldBlsQ01PopulationSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1]
            / "sql"
            / "alternatives"
            / "question_3_bls_q01_population.sql"
        ).read_text(encoding="utf-8").upper()

    def test_filters_exact_silver_series_and_period(self) -> None:
        self.assertIn(
            "FROM WORKSPACE.REARC_DATA_QUEST.SILVER_BLS_OBSERVATION",
            self.source,
        )
        self.assertIn("SERIES_ID = 'PRS30006032'", self.source)
        self.assertIn("PERIOD_CODE = 'Q01'", self.source)
        self.assertNotIn("BRONZE_", self.source)

    def test_validates_observation_and_metadata_cardinality(self) -> None:
        self.assertIn("COUNT(DISTINCT YEAR)", self.source)
        self.assertIn("INPUT.OBSERVATION_ROW_COUNT > 0", self.source)
        self.assertIn(
            "INPUT.DISTINCT_YEAR_COUNT = INPUT.OBSERVATION_ROW_COUNT",
            self.source,
        )
        self.assertIn("METADATA.METADATA_ROW_COUNT = 1", self.source)
        self.assertIn("RAISE_ERROR(", self.source)

    def test_left_joins_population_and_exposes_match_status(self) -> None:
        self.assertIn(
            "FROM WORKSPACE.REARC_DATA_QUEST.SILVER_POPULATION", self.source
        )
        self.assertIn("NATION_ID = '01000US'", self.source)
        self.assertIn("NATION = 'UNITED STATES'", self.source)
        self.assertIn("LEFT JOIN US_POPULATION AS POPULATION", self.source)
        self.assertIn(
            "POPULATION.POPULATION IS NOT NULL AS POPULATION_MATCH_FOUND",
            self.source,
        )

    def test_orders_reviewer_output_by_year(self) -> None:
        self.assertIn("ORDER BY OBSERVATIONS.YEAR", self.source)


if __name__ == "__main__":
    unittest.main()
