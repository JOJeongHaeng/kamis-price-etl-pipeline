from datetime import date
import unittest

from etl.report import (
    derive_week_metadata,
    extract_issue,
    extract_report_date,
    extract_season_food,
    extract_summary,
    extract_summary_items,
)


class ReportTests(unittest.TestCase):
    def test_extract_report_date_uses_text_date(self):
        text = '749호 발행일 2026-06-18\n이번주 체리, 참외, 아보카도 하락'
        result = extract_report_date(text, fallback=date(2026, 7, 29))
        self.assertEqual(result.isoformat(), '2026-06-18')

    def test_derive_week_metadata_builds_iso_week_range(self):
        result = derive_week_metadata(date(2026, 6, 18))
        self.assertEqual(result['start_date'], '2026-06-15')
        self.assertEqual(result['end_date'], '2026-06-21')
        self.assertEqual(result['week_no'], 25)
        self.assertEqual(result['year'], 2026)
        self.assertEqual(result['month'], 6)

    def test_extract_summary_combines_headline_and_items(self):
        text = '\n'.join([
            '농축수산 주간알뜰장보기',
            '749호 발행일 2026-06-18',
            '이번 주는 이 품목 가격이 낮아졌어요!',
            '체리 수입',
            '100g',
            '지난주 3,184원',
            '양배추',
            '1포기',
            '지난주 3,171원',
            '아보카도 수입',
            '1개',
            '지난주 1,930원',
            '주요 농축산물 소매가격',
        ])
        self.assertEqual(
            extract_summary(text),
            '이번 주는 이 품목 가격이 낮아졌어요! 체리 수입, 양배추, 아보카도 수입',
        )

    def test_extract_summary_items_collects_top_three_items(self):
        text = '\n'.join([
            '이번 주는 이 품목 가격이 낮아졌어요!',
            '체리 수입',
            '100g',
            '지난주 3,184원',
            '양배추',
            '1포기',
            '지난주 3,171원',
            '아보카도 수입',
            '1개',
            '지난주 1,930원',
            '주요 농축산물 소매가격',
        ])
        self.assertEqual(extract_summary_items(text), ['체리 수입', '양배추', '아보카도 수입'])

    def test_extract_season_food_reads_quoted_item(self):
        text = "6월에 꼭 먹어야 하는 '산딸기'\n미네랄이 풍부해 피부에 좋은 '산딸기'"
        self.assertEqual(extract_season_food(text), '산딸기')

    def test_extract_issue_returns_clean_supply_section(self):
        text = '\n'.join([
            '제철먹거리',
            "6월에 꼭 먹어야 하는 '산딸기'",
            '농축산물 수급정보',
            '여름철 농축산물 수급관리 강화로 장바구니 물가 부담 완화',
            '- 첫 번째 문장',
            '- 두 번째 문장',
            '유통소비정책관',
            '2026.06.23',
        ])
        self.assertEqual(
            extract_issue(text),
            '여름철 농축산물 수급관리 강화로 장바구니 물가 부담 완화\n- 첫 번째 문장\n- 두 번째 문장',
        )


if __name__ == '__main__':
    unittest.main()
