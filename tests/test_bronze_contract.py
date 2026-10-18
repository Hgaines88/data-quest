from pathlib import Path
import unittest

from data_quest.validation.bronze_contract import (
    BLS_BRONZE_SPECS,
    PipelineSettings,
)


class BronzeContractTests(unittest.TestCase):
    def test_declares_every_analytical_bls_source_once(self) -> None:
        self.assertEqual(
            [spec.relative_path for spec in BLS_BRONZE_SPECS],
            [
                "pr.class",
                "pr.data.0.Current",
                "pr.data.1.AllData",
                "pr.duration",
                "pr.footnote",
                "pr.measure",
                "pr.period",
                "pr.seasonal",
                "pr.sector",
                "pr.series",
            ],
        )
        self.assertEqual(
            len({spec.table_name for spec in BLS_BRONZE_SPECS}),
            len(BLS_BRONZE_SPECS),
        )

    def test_excludes_governed_nonanalytical_bls_artifacts(self) -> None:
        paths = {spec.relative_path for spec in BLS_BRONZE_SPECS}
        self.assertNotIn("pr.contacts", paths)
        self.assertNotIn("pr.txt", paths)

    def test_observation_and_series_headers_match_binding_contract(self) -> None:
        by_path = {spec.relative_path: spec for spec in BLS_BRONZE_SPECS}
        observation_columns = (
            "series_id",
            "year",
            "period",
            "value",
            "footnote_codes",
        )
        self.assertEqual(
            by_path["pr.data.0.Current"].columns,
            observation_columns,
        )

        self.assertEqual(
            by_path["pr.data.1.AllData"].columns,
            observation_columns,
        )
        self.assertEqual(
            by_path["pr.series"].columns,
            (
                "series_id",
                "sector_code",
                "class_code",
                "measure_code",
                "duration_code",
                "seasonal",
                "base_year",
                "footnote_codes",
                "begin_year",
                "begin_period",
                "end_year",
                "end_period",
            ),
        )

    def test_seasonal_preserves_exact_provider_header(self) -> None:
        by_path = {spec.relative_path: spec for spec in BLS_BRONZE_SPECS}

        self.assertEqual(
            by_path["pr.seasonal"].expected_source_columns,
            ("Seasonal_code", "Seasonal_text"),
        )
        self.assertEqual(
            by_path["pr.seasonal"].columns,
            ("seasonal_code", "seasonal_text"),
        )

    def test_required_fields_are_declared_columns(self) -> None:
        for spec in BLS_BRONZE_SPECS:
            with self.subTest(spec=spec.relative_path):
                self.assertTrue(spec.required_nonblank)
                self.assertLessEqual(
                    set(spec.required_nonblank),
                    set(spec.columns),
                )


class PipelineSettingsTests(unittest.TestCase):
    def test_builds_configured_names_and_volume_roots(self) -> None:
        settings = PipelineSettings(
            catalog="workspace",
            schema="rearc_data_quest",
            volume="raw_landing",
        )
        self.assertEqual(
            settings.bls_manifest_table,
            "workspace.rearc_data_quest.bls_ingestion_manifest",
        )
        self.assertEqual(
            settings.datausa_manifest_table,
            "workspace.rearc_data_quest.datausa_ingestion_manifest",
        )
        self.assertEqual(
            settings.bls_object_glob,
            "/Volumes/workspace/rearc_data_quest/raw_landing/"
            "bls/productivity/objects/*/*",
        )
        self.assertEqual(
            settings.datausa_object_glob,
            "/Volumes/workspace/rearc_data_quest/raw_landing/"
            "datausa/population/objects/*/*",
        )

    def test_rejects_unsafe_sql_or_volume_identifiers(self) -> None:
        for field_name, value in (
            ("catalog", "workspace; DROP TABLE x"),
            ("schema", "rearc-data-quest"),
            ("volume", "raw/landing"),
        ):
            values = {
                "catalog": "workspace",
                "schema": "rearc_data_quest",
                "volume": "raw_landing",
            }
            values[field_name] = value
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, field_name):
                    PipelineSettings(**values)


class PipelineDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            Path(__file__).resolve().parents[1] / "pipelines" / "bronze.py"
        ).read_text(encoding="utf-8")

    def test_publications_depend_on_verified_source_views(self) -> None:
        self.assertIn('spark.read.table("verified_bls_sources")', self.source)
        self.assertIn('spark.read.table("verified_datausa_source")', self.source)
        self.assertIn('@dp.temporary_view(name="verified_bls_sources")', self.source)
        self.assertIn('@dp.temporary_view(name="verified_datausa_source")', self.source)

    def test_population_view_supports_source_names_and_unlimited_pages(self) -> None:
        self.assertIn('"delta.columnMapping.mode": "name"', self.source)
        self.assertIn('(F.element_at("_page", "limit") == 0)', self.source)


if __name__ == "__main__":
    unittest.main()
