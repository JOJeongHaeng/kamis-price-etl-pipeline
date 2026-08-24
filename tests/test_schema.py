from pathlib import Path
import re
import unittest


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"


class SchemaTests(unittest.TestCase):
    def test_schema_contains_only_kamis_tables(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        created_tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", schema))

        self.assertEqual(
            created_tables,
            {"Category", "Product", "ProductVariant", "Grade", "RecentPriceSnapshot"},
        )

    def test_kamis_analysis_view_contains_freshness_rules(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATE OR REPLACE VIEW KAMISPriceAnalysis", schema)
        self.assertIn("INTERVAL 30 DAY", schema)
        self.assertIn("INTERVAL 1 YEAR", schema)
        self.assertIn("is_analysis_ready", schema)


if __name__ == "__main__":
    unittest.main()
