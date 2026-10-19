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


if __name__ == "__main__":
    unittest.main()
