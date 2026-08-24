import unittest

from sqlalchemy import create_engine, text

from config import SCHEMA_PATH
from etl.load import ensure_schema, load_kamis_outputs


class KamisLoadTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        ensure_schema(SCHEMA_PATH, engine=self.engine)

    def test_load_kamis_outputs_upserts_row_lists(self):
        categories = [{"category_code": "200", "category_name": "채소류"}]
        products = [{"item_code": "211", "item_name": "배추", "category_code": "200"}]
        variants = [{"item_code": "211", "variety_code": "01", "variety_name": "여름"}]
        grades = [{"grade_code": "04", "grade_name": "상품"}]
        snapshot = {
            "item_code": "211", "variety_code": "01", "grade_code": "04",
            "price_date": "2026-08-23", "product_cls_code": "01",
            "product_cls_name": "소매", "unit": "포기", "unit_size": "1",
            "price": 12000, "kg_price": None, "day_before_price": 11000,
            "day_before_kg_price": None, "week_before_price": None,
            "week_before_kg_price": None, "month_before_price": None,
            "month_before_kg_price": None, "year_before_price": None,
            "year_before_kg_price": None, "source_name": "PUBLIC_DATA_KAMIS",
            "collected_at": "2026-08-24T00:00:00",
        }

        first = load_kamis_outputs(categories, products, variants, grades, [snapshot], engine=self.engine)
        updated_snapshot = {**snapshot, "price": 13000}
        updated_variants = [{**variants[0], "variety_name": "고랭지"}]
        second = load_kamis_outputs(categories, products, updated_variants, grades, [updated_snapshot], engine=self.engine)

        expected_summary = {
            "categories_upserted": 1,
            "products_upserted": 1,
            "variants_upserted": 1,
            "grades_upserted": 1,
            "snapshots_written": 1,
        }
        self.assertEqual(first, expected_summary)
        self.assertEqual(second, expected_summary)
        with self.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT COUNT(*) FROM RecentPriceSnapshot")).scalar_one(), 1)
            self.assertEqual(connection.execute(text("SELECT price FROM RecentPriceSnapshot")).scalar_one(), 13000)
            self.assertEqual(connection.execute(text("SELECT variety_name FROM ProductVariant")).scalar_one(), "고랭지")


if __name__ == "__main__":
    unittest.main()
