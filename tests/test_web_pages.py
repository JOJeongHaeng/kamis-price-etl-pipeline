import unittest

import httpx2
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from tools.seed_demo_db import seed_database
from web.app import create_app
from web.database import create_web_engine
from web.repository import PriceRepository
from web.service import PriceService


class FailingPriceService:
    def search(self, filters, today=None):
        raise SQLAlchemyError("password=do-not-expose")


class WebPageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_web_engine("sqlite:///:memory:")
        seed_database(self.engine)
        service = PriceService(PriceRepository(self.engine))
        self.client = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=create_app(service)),
            base_url="http://test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        self.engine.dispose()

    async def test_page_renders_search_form_and_price(self):
        response = await self.client.get("/", params={"q": "배추"})

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="q"', response.text)
        self.assertIn('value="배추"', response.text)
        self.assertIn("배추", response.text)
        self.assertIn("신선도", response.text)

    async def test_page_treats_empty_market_type_as_all_markets(self):
        response = await self.client.get(
            "/",
            params={"q": "배추", "market_type": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("배추", response.text)
        self.assertIn("소매", response.text)
        self.assertIn("도매", response.text)

    async def test_page_renders_empty_result_message(self):
        response = await self.client.get("/", params={"q": "없는품목"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("검색 결과가 없습니다", response.text)

    async def test_page_keeps_filters_in_next_page_link(self):
        self._add_retail_cabbage_history(20)

        response = await self.client.get(
            "/",
            params={"q": "배추", "market_type": "retail"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("page=2", response.text)
        self.assertIn("q=%EB%B0%B0%EC%B6%94", response.text)
        self.assertIn("market_type=retail", response.text)

    async def test_page_hides_database_failure_details(self):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=create_app(FailingPriceService())),
            base_url="http://test",
        ) as failing_client:
            with self.assertLogs("web.app", level="ERROR"):
                response = await failing_client.get("/")

        self.assertEqual(response.status_code, 503)
        self.assertIn("잠시 후 다시 시도", response.text)
        self.assertNotIn("password", response.text.lower())

    def _add_retail_cabbage_history(self, count):
        rows = [
            {
                "examined_date": f"2026-07-{day:02d}",
                "unit_size": str(day),
                "price": 3000 + day,
            }
            for day in range(1, count + 1)
        ]
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO RecentPriceSnapshot (
                        variant_id, grade_code, examined_date, product_cls_code,
                        product_cls_name, unit, unit_size, price, kg_price,
                        source_name, collected_at
                    ) VALUES (
                        1, '04', :examined_date, '01', '소매', '포기', :unit_size,
                        :price, NULL, 'PUBLIC_DATA_KAMIS', '2026-08-23 00:00:00'
                    )
                    """
                ),
                rows,
            )


if __name__ == "__main__":
    unittest.main()
