import unittest

import httpx2
from sqlalchemy.exc import SQLAlchemyError

from tools.seed_demo_db import seed_database
from web.app import create_app
from web.database import create_web_engine
from web.repository import PriceRepository
from web.service import PriceService


class FailingPriceService:
    def search(self, filters, today=None):
        raise SQLAlchemyError("password=do-not-expose")


class WebApiTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_api_returns_paginated_prices(self):
        response = await self.client.get(
            "/api/prices",
            params={"q": "배추", "page": 1, "page_size": 1},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], 1)
        self.assertEqual(body["total"], 2)
        self.assertEqual(body["total_pages"], 2)
        self.assertEqual(body["items"][0]["item_name"], "배추")
        self.assertIn(
            body["items"][0]["freshness_status"],
            {"FRESH", "CAUTION", "STALE"},
        )

    async def test_api_filters_retail_prices(self):
        response = await self.client.get(
            "/api/prices",
            params={"market_type": "retail"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 3)
        self.assertEqual(
            {item["product_cls_name"] for item in response.json()["items"]},
            {"소매"},
        )

    async def test_api_rejects_invalid_market_type(self):
        response = await self.client.get(
            "/api/prices",
            params={"market_type": "invalid"},
        )

        self.assertEqual(response.status_code, 422)

    async def test_api_rejects_page_size_above_limit(self):
        response = await self.client.get("/api/prices", params={"page_size": 101})

        self.assertEqual(response.status_code, 422)

    async def test_api_returns_empty_page_as_success(self):
        response = await self.client.get("/api/prices", params={"q": "없는품목"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["total"], 0)
        self.assertEqual(response.json()["total_pages"], 0)

    async def test_api_hides_database_failure_details(self):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=create_app(FailingPriceService())),
            base_url="http://test",
        ) as failing_client:
            with self.assertLogs("web.app", level="ERROR") as captured_logs:
                response = await failing_client.get("/api/prices")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"],
            "PRICE_SERVICE_UNAVAILABLE",
        )
        self.assertEqual(
            response.json()["detail"]["message"],
            "가격 정보를 불러올 수 없습니다.",
        )
        self.assertIn("Price query failed", captured_logs.output[0])
        self.assertNotIn("password", response.text.lower())


if __name__ == "__main__":
    unittest.main()
