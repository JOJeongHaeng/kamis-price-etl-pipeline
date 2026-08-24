import unittest

import httpx2
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError

from tools.seed_demo_db import seed_database
from web.app import create_app
from web.database import create_web_engine
from web.repository import PriceRepository
from web.service import PriceService


class WebHealthTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_web_engine("sqlite:///:memory:")
        seed_database(self.engine)
        service = PriceService(PriceRepository(self.engine))
        self.client = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(
                app=create_app(service, health_engine=self.engine)
            ),
            base_url="http://test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        self.engine.dispose()

    async def test_health_returns_ready_for_seeded_database(self):
        response = await self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "database": "ready"},
        )

    async def test_health_returns_unavailable_for_empty_database(self):
        with self.engine.begin() as connection:
            connection.execute(text("DELETE FROM RecentPriceSnapshot"))

        with self.assertLogs("web.app", level="ERROR") as captured_logs:
            response = await self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable", "database": "unavailable"},
        )
        self.assertIn("no price snapshots", captured_logs.output[0])

    async def test_health_returns_unavailable_when_snapshot_table_is_missing(self):
        engine = create_web_engine("sqlite:///:memory:")
        self.addAsyncCleanup(self._dispose_engine, engine)
        async with self._health_client(engine) as client:
            with self.assertLogs("web.app", level="ERROR") as captured_logs:
                response = await client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable", "database": "unavailable"},
        )
        self.assertIn("Database health check failed", captured_logs.output[0])

    async def test_health_hides_and_logs_sqlalchemy_failure(self):
        engine = create_web_engine("sqlite:///:memory:")
        self.addAsyncCleanup(self._dispose_engine, engine)

        @event.listens_for(engine, "engine_connect")
        def fail_connection(connection):
            raise SQLAlchemyError("password=do-not-expose")

        async with self._health_client(engine) as client:
            with self.assertLogs("web.app", level="ERROR") as captured_logs:
                response = await client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable", "database": "unavailable"},
        )
        self.assertIn("Database health check failed", captured_logs.output[0])
        self.assertNotIn("password", response.text.lower())

    def _health_client(self, engine):
        service = PriceService(PriceRepository(engine))
        return httpx2.AsyncClient(
            transport=httpx2.ASGITransport(
                app=create_app(service, health_engine=engine)
            ),
            base_url="http://test",
        )

    async def _dispose_engine(self, engine):
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
