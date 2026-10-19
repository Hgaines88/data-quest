"""Structural tests for the repeatable Gold SQL/PySpark reconciliation."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / "sql" / "quality" / "validate_gold_cross_implementation.sql"


class GoldCrossImplementationQualityQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = QUERY.read_text(encoding="utf-8")
        cls.lowered = cls.sql.lower()

    def test_reports_every_required_boundary_once(self) -> None:
        required_checks = (
            "q1_schema_parity",
            "q1_row_count_and_key_parity",
            "q1_values_within_tolerance",
            "q1_year_bounds_and_semantics",
            "q1_source_spot_check",
            "q2_schema_parity",
            "q2_row_count_parity",
            "q2_unique_key_parity",
            "q2_exact_value_parity",
            "q2_earliest_year_tie_break",
            "q2_source_spot_check",
            "q3_schema_parity",
            "q3_row_count_parity",
            "q3_unique_key_parity",
            "q3_exact_value_parity",
            "q3_source_preservation_and_bounds",
            "q3_source_spot_check",
        )
        for check_name in required_checks:
            with self.subTest(check_name=check_name):
                self.assertEqual(self.sql.count(f"'{check_name}'"), 1)

    def test_is_read_only_and_uses_governed_layers(self) -> None:
        for forbidden in ("insert ", "update ", "delete ", "merge ", "drop "):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.lowered)
        for table in (
            "silver_population",
            "silver_bls_observation",
            "silver_bls_series",
            "gold_population_summary_2013_2018",
            "gold_bls_best_year_by_series",
            "gold_bls_q01_population",
        ):
            with self.subTest(table=table):
                self.assertIn(f"workspace.rearc_data_quest.{table}", self.sql)

    def test_has_one_machine_readable_pass_contract(self) -> None:
        self.assertIn("every output row has passed = true", self.sql)
        self.assertIn(
            "question,\n  check_name,\n  actual_value,\n  expected_value,\n  passed,",
            self.sql,
        )
        self.assertIn("ORDER BY question, check_name", self.sql)

    def test_applies_tolerance_only_to_double_aggregates(self) -> None:
        self.assertIn("CAST(0.000001 AS DOUBLE) AS double_tolerance", self.sql)
        self.assertEqual(self.sql.count("settings.double_tolerance"), 4)
        self.assertIn(
            "NOT (sql_result.mean_population <=> pyspark_result.mean_population)",
            self.sql,
        )
        self.assertIn("sql_result.mean_population IS NULL", self.sql)
        self.assertIn("pyspark_result.mean_population IS NULL", self.sql)
        self.assertIn("sql_result.q01_value <=> pyspark_result.q01_value", self.sql)
        self.assertIn(
            "sql_result.annual_quarterly_sum\n        <=> pyspark_result.annual_quarterly_sum",
            self.sql,
        )

    def test_validates_question_specific_invariants(self) -> None:
        self.assertIn("HAVING COUNT(*) = 6", self.sql)
        self.assertIn("ORDER BY annual_quarterly_sum DESC, year ASC", self.sql)
        self.assertIn("MIN(annual.year) AS expected_best_year", self.sql)
        self.assertIn("LEFT JOIN workspace.rearc_data_quest.silver_population", self.sql)
        self.assertIn("COUNT_IF(population_match_found <> (population IS NOT NULL))", self.sql)
        self.assertIn("q2_metadata_violations AS", self.sql)
        self.assertIn("HAVING COUNT(metadata.series_id) <> 1", self.sql)

    def test_compares_published_names_types_and_order(self) -> None:
        self.assertEqual(self.sql.count("workspace.information_schema.columns"), 3)
        self.assertEqual(self.sql.count("ORDER BY ordinal_position"), 3)
        for column_signature in (
            "start_year:int",
            "series_id:string",
            "q01_value:decimal(20,6)",
        ):
            with self.subTest(column_signature=column_signature):
                self.assertIn(column_signature, self.sql)

    def test_stable_checks_do_not_depend_on_result_rows(self) -> None:
        self.assertIn("COUNT(*) = 1\n      AND MIN(start_year) = 2013", self.sql)
        self.assertNotIn("FROM q1_sql\n),\nq1_pyspark_schema", self.sql)

    def test_contains_independent_source_spot_checks(self) -> None:
        self.assertIn("q1_source_calculation AS", self.sql)
        self.assertIn("q1_source_mean AS", self.sql)
        self.assertIn(
            "SUM(POW(values.population - mean.source_mean_population, 2))",
            self.sql,
        )
        self.assertIn("q1_source_mismatches AS", self.sql)
        self.assertIn("result.series_id = 'PRS30006032'", self.sql)
        self.assertIn("best_year = 1994", self.sql)
        self.assertIn("source.year IN (2012, 2013, 2020, 2024, 2026)", self.sql)
        self.assertIn("source_sample_count = 5", self.sql)
        self.assertIn("result_sample_count = 5", self.sql)

    def test_compares_values_in_both_directions(self) -> None:
        self.assertEqual(self.lowered.count("full outer join"), 5)
        expected_references = {
            "q1_value_mismatches": 2,
            "q1_source_mismatches": 2,
            "q2_value_mismatches": 2,
            "q3_value_mismatches": 2,
        }
        for mismatch_cte, reference_count in expected_references.items():
            with self.subTest(mismatch_cte=mismatch_cte):
                self.assertEqual(self.sql.count(mismatch_cte), reference_count)


if __name__ == "__main__":
    unittest.main()
