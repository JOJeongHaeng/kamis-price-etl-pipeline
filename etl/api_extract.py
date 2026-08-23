from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from config import KAMIS_API_PAGE_SIZE, KAMIS_API_TIMEOUT, KAMIS_API_URL, KAMIS_SERVICE_KEY


class KamisApiError(RuntimeError):
    """Raised when the public-data KAMIS API cannot return a valid response."""


def _build_url(base_url: str, service_key: str, page_no: int, page_size: int) -> str:
    query = urlencode({"pageNo": page_no, "numOfRows": page_size, "returnType": "JSON"})
    encoded_key = quote(service_key, safe="%")
    return f"{base_url}?serviceKey={encoded_key}&{query}"


def _decode_json(payload: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KamisApiError("The public-data API returned an invalid JSON response") from exc
    if not isinstance(decoded, dict):
        raise KamisApiError("The public-data API JSON response must be an object")
    return decoded


def validate_kamis_response(response: dict[str, Any]) -> dict[str, Any]:
    header = response.get("header")
    if not isinstance(header, dict):
        nested = response.get("response")
        if isinstance(nested, dict):
            response = nested
            header = response.get("header")
    if not isinstance(header, dict):
        raise KamisApiError("The public-data API response does not contain a header")

    code = str(header.get("resultCode", ""))
    if code not in {"0", "00", "000", "0000"}:
        message = str(header.get("resultMsg", "Unknown API error"))
        raise KamisApiError(f"Public-data API error {code}: {message}")
    if not isinstance(response.get("body"), dict):
        raise KamisApiError("The public-data API response does not contain a body")
    return response


def _fetch_page(
    *,
    service_key: str,
    base_url: str,
    page_no: int,
    page_size: int,
    timeout: float,
    opener: Callable[..., Any],
) -> dict[str, Any]:
    request = Request(
        _build_url(base_url, service_key, page_no, page_size),
        headers={"Accept": "application/json", "User-Agent": "SmartShopping-ETL/1.0"},
    )
    try:
        with opener(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        raise KamisApiError(f"Public-data API HTTP error: {exc.code}") from exc
    except (URLError, TimeoutError) as exc:
        raise KamisApiError("Public-data API request failed") from exc
    return validate_kamis_response(_decode_json(payload))


def _items(response: dict[str, Any]) -> list[dict[str, Any]]:
    items = response.get("body", {}).get("items", {})
    rows = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(rows, dict):
        rows = [rows]
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def fetch_recent_kamis_prices(
    *,
    service_key: str = KAMIS_SERVICE_KEY,
    base_url: str = KAMIS_API_URL,
    page_size: int = KAMIS_API_PAGE_SIZE,
    timeout: float = KAMIS_API_TIMEOUT,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    """Fetch every page of the public-data recent wholesale/retail API."""
    if not service_key:
        raise KamisApiError("Missing KAMIS_SERVICE_KEY")
    if not 1 <= page_size <= 1000:
        raise KamisApiError("KAMIS_API_PAGE_SIZE must be between 1 and 1000")

    page_no = 1
    all_rows: list[dict[str, Any]] = []
    first_response: dict[str, Any] | None = None
    while True:
        response = _fetch_page(
            service_key=service_key,
            base_url=base_url,
            page_no=page_no,
            page_size=page_size,
            timeout=timeout,
            opener=opener,
        )
        if first_response is None:
            first_response = response
        page_rows = _items(response)
        all_rows.extend(page_rows)
        total_count = int(response["body"].get("totalCount", len(all_rows)) or 0)
        if not page_rows or len(all_rows) >= total_count:
            break
        page_no += 1

    result = first_response or {"header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"}}
    result["body"] = {
        **result.get("body", {}),
        "items": {"item": all_rows},
        "pageNo": 1,
        "numOfRows": page_size,
        "totalCount": len(all_rows),
    }
    return result
