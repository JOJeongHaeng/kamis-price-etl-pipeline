from datetime import datetime, timezone
import unittest

from etl.api_transform import RECENT_PRICE_SNAPSHOT_COLUMNS, create_kamis_dimensions, normalize_kamis_prices


class ApiTransformTests(unittest.TestCase):
    def test_normalize_kamis_prices_maps_official_fields(self):
        response = {
            "body": {
                "items": {
                    "item": [{
                        "exmn_ymd": "2026-08-21", "se_cd": "01", "se_nm": "소매",
                        "ctgry_cd": "200", "ctgry_nm": "채소류", "item_cd": "211",
                        "item_nm": "배추", "vrty_cd": "01", "vrty_nm": "여름",
                        "grd_cd": "04", "grd_nm": "상품", "unit": "포기", "unit_sz": "1",
                        "exmn_dd_prc": "3,450", "exmn_dd_cnvs_prc": "3,450",
                        "dd1_bfr_prc": "3,300", "dd1_bfr_cnvs_prc": "3,300",
                        "ww1_bfr_prc": "3,100", "ww1_bfr_cnvs_prc": "3,100",
                        "mm1_bfr_prc": "2,900", "mm1_bfr_cnvs_prc": "2,900",
                        "yy1_bfr_prc": "2,700", "yy1_bfr_cnvs_prc": "2,700",
                    }]
                }
            }
        }

        result = normalize_kamis_prices(
            response,
            collected_at=datetime(2026, 8, 23, 1, 2, 3, tzinfo=timezone.utc),
        )

        self.assertIsInstance(result, list)
        self.assertEqual(list(result[0]), RECENT_PRICE_SNAPSHOT_COLUMNS)
        self.assertEqual(result[0]["item_code"], "211")
        self.assertEqual(result[0]["item_name"], "배추")
        self.assertEqual(result[0]["variety_name"], "여름")
        self.assertEqual(result[0]["price"], 3450)
        self.assertEqual(result[0]["week_before_price"], 3100)
        self.assertEqual(result[0]["year_before_kg_price"], 2700)
        self.assertEqual(result[0]["source_name"], "PUBLIC_DATA_KAMIS")
        self.assertEqual(result[0]["collected_at"], "2026-08-23T01:02:03")

    def test_normalize_deduplicates_by_full_product_identity(self):
        valid = {
            "exmn_ymd": "20260821", "se_cd": "02", "se_nm": "도매",
            "item_cd": "211", "item_nm": "배추", "vrty_cd": "01",
            "grd_cd": "04", "unit": "kg", "unit_sz": "10", "exmn_dd_prc": "12,500",
        }
        response = {"body": {"items": {"item": [valid, valid.copy(), {"item_cd": ""}]}}}

        result = normalize_kamis_prices(response)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["price_date"], "2026-08-21")

    def test_normalize_returns_canonical_empty_list(self):
        result = normalize_kamis_prices({"body": {"items": {"item": []}}})
        self.assertEqual(result, [])

    def test_create_kamis_dimensions_removes_repeated_attributes(self):
        snapshot = normalize_kamis_prices({"body": {"items": {"item": [{
            "exmn_ymd": "20260821", "se_cd": "01", "se_nm": "소매",
            "ctgry_cd": "200", "ctgry_nm": "채소류", "item_cd": "211",
            "item_nm": "배추", "vrty_cd": "01", "vrty_nm": "여름",
            "grd_cd": "04", "grd_nm": "상품", "unit": "포기", "unit_sz": "1",
            "exmn_dd_prc": "3450",
        }]}}})

        dimensions = create_kamis_dimensions(snapshot)

        self.assertEqual(dimensions["category"], [{"category_code": "200", "category_name": "채소류"}])
        self.assertEqual(dimensions["product"], [{"item_code": "211", "item_name": "배추", "category_code": "200"}])
        self.assertEqual(dimensions["product_variant"], [{"item_code": "211", "variety_code": "01", "variety_name": "여름"}])
        self.assertEqual(dimensions["grade"], [{"grade_code": "04", "grade_name": "상품"}])


if __name__ == "__main__":
    unittest.main()
