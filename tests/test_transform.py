from pathlib import Path
import unittest

import pandas as pd

from etl.transform import build_analysis_mart, create_item_df, normalize_market_price, normalize_weekly_price


class TransformTests(unittest.TestCase):
    def test_normalize_weekly_price_converts_numeric_fields(self):
        raw = pd.DataFrame([["배추", "1포기", "1,000", "1,250", "25.0%"]], columns=["A", "B", "C", "D", "E"])
        result = normalize_weekly_price(raw, Path("weekly.xlsx"))
        self.assertEqual(result.loc[0, "item_name"], "배추")
        self.assertEqual(result.loc[0, "last_price"], 1000)
        self.assertEqual(result.loc[0, "current_price"], 1250)
        self.assertEqual(result.loc[0, "change_rate"], 25.0)

    def test_normalize_weekly_price_filters_misaligned_rows(self):
        raw = pd.DataFrame(
            [
                ["배추", "1포기", "1,000", "1,250", "25.0%"],
                ["423", "-1.8%", "10개", "351", "-20.3%"],
                ["(국산))", "1kg", "343", "344", "1.0%"],
            ],
            columns=["A", "B", "C", "D", "E"],
        )
        result = normalize_weekly_price(raw, Path("weekly.xlsx"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "item_name"], "배추")

    def test_normalize_market_price_keeps_real_items_and_filters_noise(self):
        raw = pd.DataFrame(
            [
                ["사과", "1개", "2,000", "2,300", "300"],
                ["대추방울토마토", "1개", "419", "420", "1"],
                ["굵은소금", "5kg", "6000", "6500", "500"],
                ["냉장", "100g", "418", "500", "82"],
            ],
            columns=["A", "B", "C", "D", "E"],
        )
        result = normalize_market_price(raw, Path("market.xlsx"))
        self.assertEqual(set(result["item_name"]), {"사과", "대추방울토마토", "굵은소금"})

    def test_normalize_weekly_price_filters_header_rows(self):
        raw = pd.DataFrame(
            [
                ["품목", "단위", "전주", "금주", "등락률"],
                ["배추", "1포기", "1,000", "1,250", "25.0%"],
            ],
            columns=["A", "B", "C", "D", "E"],
        )
        result = normalize_weekly_price(raw, Path("weekly.xlsx"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "item_name"], "배추")

    def test_normalize_market_price_filters_header_rows(self):
        raw = pd.DataFrame(
            [
                ["품목", "단위", "전통시장", "대형마트", "차이"],
                ["사과", "1개", "2,000", "2,300", "300"],
            ],
            columns=["A", "B", "C", "D", "E"],
        )
        result = normalize_market_price(raw, Path("market.xlsx"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "item_name"], "사과")

    def test_normalize_weekly_price_deduplicates_same_item_in_same_source(self):
        raw = pd.DataFrame(
            [
                ["배추", "1포기", "1,000", "1,250", "25.0%"],
                ["배추", "1포기", "1,000", "1,250", "25.0%"],
            ],
            columns=["A", "B", "C", "D", "E"],
        )
        result = normalize_weekly_price(raw, Path("weekly.xlsx"))
        self.assertEqual(len(result), 1)

    def test_normalize_market_price_deduplicates_same_item_in_same_source(self):
        raw = pd.DataFrame(
            [
                ["사과", "1개", "2,000", "2,300", "300"],
                ["사과", "1개", "2,000", "2,300", "300"],
            ],
            columns=["A", "B", "C", "D", "E"],
        )
        result = normalize_market_price(raw, Path("market.xlsx"))
        self.assertEqual(len(result), 1)

    def test_create_item_df_deduplicates_items(self):
        weekly_df = pd.DataFrame(
            [["배추", "1포기", 1000, 1200, 20, "weekly.xlsx"]],
            columns=["item_name", "unit", "last_price", "current_price", "change_rate", "source_file"],
        )
        market_df = pd.DataFrame(
            [["배추", "1포기", 900, 1100, 200, "market.xlsx"]],
            columns=["item_name", "unit", "traditional_price", "large_market_price", "price_difference", "source_file"],
        )
        result = create_item_df(weekly_df, market_df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "name"], "배추")

    def test_build_analysis_mart_creates_both_dataset_views(self):
        weekly_df = pd.DataFrame(
            [["배추", "1포기", 1000, 1200, 20, 31, 2026, 7, "weekly.xlsx"]],
            columns=["item_name", "unit", "last_price", "current_price", "change_rate", "week_no", "year", "month", "source_file"],
        )
        market_df = pd.DataFrame(
            [["배추", "1포기", 900, 1100, 200, 31, 2026, 7, "market.xlsx"]],
            columns=["item_name", "unit", "traditional_price", "large_market_price", "price_difference", "week_no", "year", "month", "source_file"],
        )
        result = build_analysis_mart(weekly_df, market_df)
        self.assertEqual(set(result["dataset_type"]), {"weekly", "market"})
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
