import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "stakeholder"

DATASETS = {
    "population_summary.sql": (
        "gold_population_summary_2013_2018",
        ["start_year", "end_year", "year_count", "mean_population",
         "population_stddev", "stddev_semantics"],
    ),
    "bls_best_year_by_series.sql": (
        "gold_bls_best_year_by_series",
        ["series_id", "series_label", "best_year", "annual_quarterly_sum",
         "quarterly_observation_count", "has_quarterly_observations"],
    ),
    "q01_population_context.sql": (
        "gold_bls_q01_population",
        ["series_id", "series_label", "year", "q01_value", "population",
         "population_match_found"],
    ),
}

MUTATING = re.compile(r"\b(insert|update|delete|merge|drop|alter|create)\b", re.I)


class StakeholderSqlTest(unittest.TestCase):
    def read(self, name):
        return (SQL_DIR / name).read_text(encoding="utf-8")

    @staticmethod
    def executable(sql):
        return "\n".join(
            line for line in sql.splitlines() if not line.lstrip().startswith("--")
        )

    def test_dashboard_datasets_are_explicit_read_only_gold_queries(self):
        for name, (table, fields) in DATASETS.items():
            with self.subTest(name=name):
                sql = self.read(name)
                executable = self.executable(sql)
                self.assertIn(f"workspace.rearc_data_quest.{table}", executable)
                self.assertEqual(executable.lower().count("gold_"), 1)
                self.assertNotRegex(executable, r"(?i)select\s+\*")
                self.assertNotRegex(executable, MUTATING)
                self.assertNotRegex(executable, r"(?i)\b(?:silver|bronze)_")
                self.assertNotIn("Volumes", executable)
                projection = executable.split("FROM", 1)[0]
                positions = [projection.index(field) for field in fields]
                self.assertEqual(positions, sorted(positions))

    def test_validation_is_read_only_and_uses_all_three_gold_contracts(self):
        sql = self.executable(self.read("validate_stakeholder_values.sql"))
        for _, (table, _) in DATASETS.items():
            self.assertIn(f"workspace.rearc_data_quest.{table}", sql)
        self.assertNotRegex(sql, MUTATING)
        self.assertNotRegex(sql, r"(?i)\b(?:silver|bronze)_")

    def test_validation_exposes_four_named_machine_readable_checks(self):
        sql = self.read("validate_stakeholder_values.sql")
        checks = [
            "population_summary_bounds",
            "population_summary_values",
            "bls_series_spot_check",
            "q01_population_context_spot_checks",
        ]
        for check in checks:
            self.assertEqual(sql.count(f"'{check}'"), 1)
        for field in ["check_name", "actual_value", "expected_value", "passed",
                      "interpretation"]:
            self.assertIn(field, sql)

    def test_q01_validation_covers_boundary_match_and_gap_years(self):
        sql = self.read("validate_stakeholder_values.sql")
        for year in [2012, 2013, 2020, 2024, 2026]:
            self.assertEqual(sql.count(f"({year},"), 1)


if __name__ == "__main__":
    unittest.main()
