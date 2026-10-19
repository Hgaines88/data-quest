"""Structural tests for the repeatable Bronze-to-Silver reconciliation."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / "sql" / "quality" / "validate_bronze_to_silver.sql"


class BronzeToSilverQualityQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = QUERY.read_text(encoding="utf-8")

    def test_reports_every_required_quality_boundary(self) -> None:
        required_checks = (
            "observation_row_count_reconciles",
            "series_row_count_reconciles",
            "population_us_row_count_reconciles",
            "observation_duplicate_keys",
            "series_duplicate_keys",
            "population_duplicate_keys",
            "observation_required_nulls",
            "series_required_nulls_or_blank_labels",
            "population_required_nulls_or_invalid_values",
            "observation_series_orphans",
            "population_missing_required_years",
        )
        for check_name in required_checks:
            with self.subTest(check_name=check_name):
                self.assertEqual(self.sql.count(f"'{check_name}'"), 1)

    def test_is_read_only_and_uses_governed_layers(self) -> None:
        lowered = self.sql.lower()
        for forbidden in ("insert ", "update ", "delete ", "merge ", "drop "):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lowered)
        for table in (
            "bronze_bls_observation_all",
            "bronze_bls_series",
            "bronze_datausa_population",
            "silver_bls_observation",
            "silver_bls_series",
            "silver_population",
        ):
            with self.subTest(table=table):
                self.assertIn(f"workspace.rearc_data_quest.{table}", self.sql)

    def test_has_one_machine_readable_pass_condition(self) -> None:
        self.assertIn("every output row has passed = true", self.sql)
        self.assertIn(
            "select check_name, actual_value, expected_value, passed, interpretation",
            self.sql.lower(),
        )

    def test_required_series_label_check_counts_null_and_blank_labels(self) -> None:
        predicate = "series_label is null or trim(series_label) = ''"
        self.assertEqual(self.sql.lower().count(predicate), 2)

    def test_population_check_enforces_the_documented_us_grain(self) -> None:
        self.assertEqual(self.sql.count("nation_id <> '01000US'"), 2)
        self.assertEqual(self.sql.count("nation <> 'United States'"), 2)


if __name__ == "__main__":
    unittest.main()
