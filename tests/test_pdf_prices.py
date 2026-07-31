from pathlib import Path
import unittest

from etl.pdf_prices import (
    extract_weekly_price_date_range,
    parse_market_price_from_text,
    parse_weekly_price_from_text,
)


class PdfPriceTests(unittest.TestCase):
    def test_extract_weekly_price_date_range_prefers_current_week_header(self):
        text = """
주요 농축산물 소매가격
품목
단위
지난주
이번주
(08.28~09.03)
(09.04~09.10)
등락률
(%)
"""
        result = extract_weekly_price_date_range(text, Path("알뜰 장보기 물가정보-710_2025-09-04~2025-09-10_전체보기.pdf"))
        self.assertEqual(result, ("2025-09-04", "2025-09-10"))

    def test_parse_weekly_price_from_text_attaches_week_metadata(self):
        text = """
주요 농축산물 소매가격
품목
단위
지난주
이번주
(08.28~09.03)
(09.04~09.10)
등락률
(%)
파프리카
200g
2,382
1,884
-20.9%
양파
1kg
2,214
2,178
-1.6%
가격비교 알뜰정보
"""
        df = parse_weekly_price_from_text(text, Path("알뜰 장보기 물가정보-710_2025-09-04~2025-09-10_전체보기.pdf"))
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, "item_name"], "파프리카")
        self.assertEqual(df.loc[1, "current_price"], "2,178")
        self.assertEqual(df.loc[0, "start_date"], "2025-09-04")
        self.assertEqual(df.loc[0, "end_date"], "2025-09-10")
        self.assertEqual(df.loc[0, "year"], 2025)
        self.assertEqual(df.loc[0, "month"], 9)

    def test_parse_market_price_from_text(self):
        text = """
가격비교 알뜰정보
전통시장이 더 저렴해요!
참깨(백색(국산)) / 500g
전통시장
대형마트
-8,250원 저렴
15,750
24,000
천일염 / 5kg
-7,675원 저렴
전통시장
대형마트
6,316
13,991
제철먹거리
"""
        df = parse_market_price_from_text(text, Path("sample.pdf"))
        self.assertEqual(len(df), 2)
        self.assertEqual(df.loc[0, "item_name"], "참깨(백색(국산))")
        self.assertEqual(df.loc[0, "unit"], "500g")
        self.assertEqual(df.loc[1, "traditional_price"], "6,316")


if __name__ == "__main__":
    unittest.main()
