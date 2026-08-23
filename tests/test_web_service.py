from datetime import date
import unittest

from tools.seed_demo_db import seed_database
from web.database import create_web_engine
from web.models import PriceFilters, classify_freshness
from web.repository import PriceRepository
from web.service import PriceService


class WebServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_web_engine("sqlite:///:memory:")
        seed_database(self.engine)
        self.service = PriceService(PriceRepository(self.engine))

    def tearDown(self):
        self.engine.dispose()

    def test_search_filters_partial_item_name(self):
        result = self.service.search(
            PriceFilters(query="배", page=1, page_size=20),
            today=date(2026, 8, 23),
        )

        self.assertEqual({item.item_name for item in result.items}, {"배추"})
        self.assertEqual(result.total, 2)

    def test_search_maps_retail_market_filter(self):
        result = self.service.search(
            PriceFilters(market_type="retail", page=1, page_size=20),
            today=date(2026, 8, 23),
        )

        self.assertEqual(len(result.items), 3)
        self.assertEqual({item.product_cls_name for item in result.items}, {"소매"})

    def test_search_orders_by_date_then_item_name(self):
        result = self.service.search(
            PriceFilters(page=1, page_size=6),
            today=date(2026, 8, 23),
        )

        self.assertEqual(
            [(item.examined_date.isoformat(), item.item_name) for item in result.items],
            [
                ("2026-08-21", "배추"),
                ("2026-08-21", "배추"),
                ("2026-07-24", "양파"),
                ("2026-07-24", "양파"),
                ("2025-08-23", "사과"),
                ("2025-08-22", "사과"),
            ],
        )

    def test_search_returns_stable_pagination_metadata(self):
        result = self.service.search(
            PriceFilters(page=2, page_size=2),
            today=date(2026, 8, 23),
        )

        self.assertEqual(result.page, 2)
        self.assertEqual(result.page_size, 2)
        self.assertEqual(result.total, 6)
        self.assertEqual(result.total_pages, 3)
        self.assertEqual(len(result.items), 2)

    def test_search_returns_empty_page_without_fabricating_pages(self):
        result = self.service.search(
            PriceFilters(query="없는품목", page=1, page_size=20),
            today=date(2026, 8, 23),
        )

        self.assertEqual(result.items, ())
        self.assertEqual(result.total, 0)
        self.assertEqual(result.total_pages, 0)

    def test_freshness_uses_inclusive_boundaries(self):
        self.assertEqual(
            classify_freshness(date(2026, 7, 24), date(2026, 8, 23)),
            (30, "FRESH", "최신"),
        )
        self.assertEqual(
            classify_freshness(date(2025, 8, 23), date(2026, 8, 23)),
            (365, "CAUTION", "주의"),
        )
        self.assertEqual(
            classify_freshness(date(2025, 8, 22), date(2026, 8, 23)),
            (366, "STALE", "오래됨"),
        )


if __name__ == "__main__":
    unittest.main()
