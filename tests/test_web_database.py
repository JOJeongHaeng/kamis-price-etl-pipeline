from pathlib import Path
import subprocess
import sys
import unittest

from sqlalchemy import text

from tools.seed_demo_db import seed_database
from web.database import create_web_engine, resolve_database_url


class WebDatabaseTests(unittest.TestCase):
    def test_resolve_database_url_defaults_to_demo_sqlite(self):
        result = resolve_database_url({})

        self.assertTrue(result.startswith("sqlite:///"))
        self.assertTrue(result.endswith("database/smartshopping.db"))

    def test_resolve_database_url_prefers_environment(self):
        result = resolve_database_url({"DATABASE_URL": "sqlite:///:memory:"})

        self.assertEqual(result, "sqlite:///:memory:")

    def test_create_web_engine_executes_sqlite_query(self):
        engine = create_web_engine("sqlite:///:memory:")

        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()

        self.assertEqual(result, 1)

    def test_seed_database_creates_repeatable_sample_rows(self):
        engine = create_web_engine("sqlite:///:memory:")

        first_count = seed_database(engine)
        second_count = seed_database(engine)
        with engine.connect() as connection:
            stored = connection.execute(
                text("SELECT COUNT(*) FROM RecentPriceSnapshot")
            ).scalar_one()

        self.assertEqual(first_count, 6)
        self.assertEqual(second_count, 6)
        self.assertEqual(stored, 6)

    def test_seed_script_runs_from_project_root(self):
        project_root = Path(__file__).resolve().parents[1]

        result = subprocess.run(
            [sys.executable, "tools/seed_demo_db.py"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "Seeded 6 price snapshots.")


if __name__ == "__main__":
    unittest.main()
