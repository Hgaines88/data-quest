"""Baseline checks for the repository's Python package structure."""

import importlib
import unittest


class PackageSmokeTests(unittest.TestCase):
    """Keep the initial package boundary importable as the project grows."""

    def test_core_packages_import(self):
        for module_name in (
            "data_quest",
            "data_quest.ingestion",
            "data_quest.validation",
        ):
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)


if __name__ == "__main__":
    unittest.main()
