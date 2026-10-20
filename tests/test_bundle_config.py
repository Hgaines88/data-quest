"""Static regression checks for the DQ-24 bundle contract."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BundleConfigTests(unittest.TestCase):
    """Protect deployment order, parameterization, and ownership boundaries."""

    def test_bundle_root_is_parameterized_and_has_isolated_targets(self):
        config = (ROOT / "databricks.yml").read_text(encoding="utf-8")
        self.assertIn('databricks_cli_version: ">= 1.21.0"', config)
        for variable in ("catalog", "schema", "output_schema", "volume"):
            self.assertRegex(config, rf"(?m)^  {variable}:$")
        self.assertIn("mode: development", config)
        self.assertIn("mode: production", config)
        self.assertIn(
            "output_schema: rearc_data_quest_dq24_${workspace.current_user.short_name}",
            config,
        )
        self.assertNotRegex(config, r"(?i)(token|password|secret)\s*:")

    def test_three_serverless_triggered_pipelines_are_declared(self):
        config = (ROOT / "resources" / "pipelines.yml").read_text(
            encoding="utf-8"
        )
        for layer in ("bronze", "silver", "gold"):
            self.assertRegex(config, rf"(?m)^    {layer}:$")
            self.assertIn(f"path: ../pipelines/{layer}.py", config)
        self.assertEqual(config.count("serverless: true"), 3)
        self.assertEqual(config.count("continuous: false"), 3)
        self.assertEqual(
            len(re.findall(r"(?m)^      schema: \$\{var\.output_schema\}$", config)),
            3,
        )
        self.assertIn("data_quest.schema: ${var.schema}", config)
        self.assertIn("data_quest.schema: ${var.output_schema}", config)
        self.assertNotIn("@gmail.com", config)
        self.assertNotIn("@zipcode.rocks", config)

    def test_refresh_job_orders_only_non_landing_pipeline_tasks(self):
        config = (ROOT / "resources" / "refresh.job.yml").read_text(
            encoding="utf-8"
        )
        task_positions = [
            config.index(f"task_key: {task}")
            for task in (
                "refresh_bronze",
                "refresh_silver",
                "refresh_gold",
            )
        ]
        self.assertEqual(task_positions, sorted(task_positions))
        self.assertEqual(config.count("max_concurrent_runs: 1"), 1)
        self.assertNotIn("land_bls", config)
        self.assertNotIn("land_population", config)
        self.assertNotIn("notebook_task:", config)
        self.assertNotIn("${var.schema}", config)
        self.assertNotIn("${var.volume}", config)
        self.assertEqual(config.count("depends_on:"), 2)
        self.assertIn("- task_key: refresh_bronze", config)
        self.assertIn("- task_key: refresh_silver", config)
        self.assertNotIn("operator@example", config)
        self.assertNotIn("client:", config)
        self.assertNotIn("environment_key:", config)

    def test_shared_governance_resources_are_not_bundle_owned(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "databricks.yml",
                ROOT / "resources" / "pipelines.yml",
                ROOT / "resources" / "refresh.job.yml",
            )
        )
        for resource_type in (
            "catalogs:",
            "schemas:",
            "volumes:",
            "dashboards:",
            "sql_warehouses:",
        ):
            self.assertNotIn(resource_type, combined)


if __name__ == "__main__":
    unittest.main()
