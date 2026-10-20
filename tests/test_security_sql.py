import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "security"
GROUP = "`data_quest_readonly_analysts`"
GOLD_TABLES = {
    "gold_population_summary_2013_2018",
    "gold_bls_best_year_by_series",
    "gold_bls_q01_population",
}


class SecuritySqlTest(unittest.TestCase):
    def read(self, name):
        return (SQL_DIR / name).read_text(encoding="utf-8")

    def test_apply_grants_only_parent_usage_and_exact_gold_select(self):
        sql = self.read("apply_gold_readonly_access.sql")
        uncommented = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        statements = {
            re.sub(r"\s+", " ", statement).strip()
            for statement in uncommented.split(";")
            if statement.strip()
        }
        expected = {
            f"GRANT USE CATALOG ON CATALOG workspace TO {GROUP}",
            (
                "GRANT USE SCHEMA ON SCHEMA workspace.rearc_data_quest "
                f"TO {GROUP}"
            ),
            *{
                "GRANT SELECT ON TABLE "
                f"workspace.rearc_data_quest.{table} TO {GROUP}"
                for table in GOLD_TABLES
            },
        }
        self.assertEqual(statements, expected)

    def test_inspection_inventories_all_project_securable_types(self):
        sql = self.read("inspect_gold_readonly_access.sql")
        for relation in [
            "catalog_privileges",
            "schema_privileges",
            "table_privileges",
            "volume_privileges",
            "routine_privileges",
        ]:
            self.assertIn(f"system.information_schema.{relation}", sql)
        self.assertIn("Repeat with grantee = 'users'", sql)
        self.assertIn("no direct grants", sql)

    def test_positive_checks_read_only_the_three_gold_contracts(self):
        sql = self.read("analyst_positive_checks.sql")
        self.assertEqual(len(re.findall(r"(?i)\bSELECT\b", sql)), 3)
        self.assertEqual(len(re.findall(r"(?i)\bFROM\b", sql)), 3)
        for table in GOLD_TABLES:
            self.assertEqual(sql.count(table), 1)
        self.assertNotRegex(
            sql,
            r"(?i)\b(?:UPDATE|INSERT|DELETE|MERGE|CREATE|ALTER|DROP)\b",
        )

    def test_negative_checks_cover_write_lower_layers_volume_and_create(self):
        sql = self.read("analyst_negative_checks.sql")
        for marker in [
            "UPDATE workspace.rearc_data_quest.gold_",
            "workspace.rearc_data_quest.bronze_",
            "workspace.rearc_data_quest.silver_",
            "LIST '/Volumes/workspace/rearc_data_quest/raw_landing'",
            "CREATE TABLE workspace.rearc_data_quest.dq26_unauthorized_probe",
        ]:
            self.assertIn(marker, sql)
        self.assertIn("Run ONE statement at a time", sql)
        self.assertIn("EXPECT_TABLE_NOT_VIEW", sql)
        self.assertRegex(sql, r"not an\s+(?:--\s*)?authorization-denial test")

    def test_revoke_is_symmetric_with_apply(self):
        apply_sql = self.read("apply_gold_readonly_access.sql")
        revoke_sql = self.read("revoke_gold_readonly_access.sql")
        for table in GOLD_TABLES:
            self.assertIn(table, apply_sql)
            self.assertIn(table, revoke_sql)
        self.assertEqual(revoke_sql.count("REVOKE SELECT ON TABLE"), 3)
        self.assertEqual(revoke_sql.count("REVOKE USE SCHEMA"), 1)
        self.assertEqual(revoke_sql.count("REVOKE USE CATALOG"), 1)
        self.assertEqual(revoke_sql.count(GROUP), 5)

    def test_runbook_keeps_workspace_acls_and_identity_explicit(self):
        guide = (ROOT / "docs" / "GOLD_ACCESS_CONTROL.md").read_text(
            encoding="utf-8"
        )
        for phrase in [
            "CAN USE",
            "CAN VIEW",
            "Individual data permission",
            "dedicated non-admin validation user or service principal",
            "dq26_gold_access_control_validation.md",
            "Databricks SQL access",
            "Consumer access",
            "Workspace access",
            "Admin access",
        ]:
            self.assertIn(phrase, guide)

    def test_live_evidence_records_structural_and_authorization_failures(self):
        evidence = (
            ROOT / "docs" / "evidence" / "dq26_gold_access_control_validation.md"
        ).read_text(encoding="utf-8")
        self.assertIn("EXPECT_TABLE_NOT_VIEW", evidence)
        self.assertIn("four authorization denials", evidence)
        self.assertIn("exactly five direct grants", evidence)


if __name__ == "__main__":
    unittest.main()
