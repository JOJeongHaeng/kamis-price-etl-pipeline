import json
import unittest

from etl.api_extract import KamisApiError, fetch_recent_kamis_prices, validate_kamis_response


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return self.payload


def api_response(rows, *, page_no=1, total_count=None):
    return {
        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
        "body": {
            "items": {"item": rows},
            "pageNo": page_no,
            "numOfRows": len(rows),
            "totalCount": len(rows) if total_count is None else total_count,
        },
    }


class ApiExtractTests(unittest.TestCase):
    def test_fetch_uses_service_key_and_json_parameters(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeResponse(api_response([{"item_cd": "111"}]))

        result = fetch_recent_kamis_prices(
            service_key="decoded+key",
            base_url="https://example.test/recent/price",
            page_size=1000,
            timeout=3,
            opener=opener,
        )

        self.assertEqual(result["body"]["totalCount"], 1)
        self.assertIn("serviceKey=decoded%2Bkey", captured["url"])
        self.assertIn("returnType=JSON", captured["url"])
        self.assertIn("numOfRows=1000", captured["url"])
        self.assertEqual(captured["timeout"], 3)

    def test_fetch_collects_all_pages(self):
        calls = []

        def opener(request, timeout):
            calls.append(request.full_url)
            page_no = len(calls)
            return FakeResponse(api_response([{"item_cd": str(page_no)}], page_no=page_no, total_count=2))

        result = fetch_recent_kamis_prices(service_key="key", page_size=1, opener=opener)

        self.assertEqual(len(calls), 2)
        self.assertEqual([row["item_cd"] for row in result["body"]["items"]["item"]], ["1", "2"])

    def test_fetch_requires_service_key(self):
        with self.assertRaisesRegex(KamisApiError, "KAMIS_SERVICE_KEY"):
            fetch_recent_kamis_prices(service_key="")

    def test_validate_response_rejects_api_error(self):
        with self.assertRaisesRegex(KamisApiError, "SERVICE KEY IS NOT REGISTERED"):
            validate_kamis_response(
                {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}, "body": {}}
            )

    def test_validate_response_accepts_provider_success_code_zero(self):
        response = {"header": {"resultCode": "0", "resultMsg": "정상"}, "body": {}}
        self.assertEqual(validate_kamis_response(response), response)


if __name__ == "__main__":
    unittest.main()
