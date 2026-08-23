# SmartShopping Price Web Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally runnable FastAPI web service that searches normalized KAMIS price snapshots through both JSON and an accessible server-rendered page.

**Architecture:** Keep the existing ETL and MySQL schema unchanged. Add a focused `web` package whose repository owns portable SQL, whose service owns filters and freshness rules, and whose FastAPI application exposes both JSON and Jinja2 HTML over the same service. Use a reproducible SQLite seed database for reviewer-friendly local execution.

**Tech Stack:** Python, FastAPI, Pydantic, SQLAlchemy 2, Jinja2, SQLite/MySQL, standard-library `unittest`, FastAPI `TestClient`

**Spec:** `docs/superpowers/specs/2026-08-23-price-web-service-design.md`

## Global Constraints

- Preserve the existing KAMIS ETL and MySQL loading behavior.
- Default to `sqlite:///database/smartshopping.db` when `DATABASE_URL` is absent.
- Do not commit generated SQLite database files or credentials.
- Do not call KAMIS while serving an HTTP request.
- Keep the MVP to search, market filter, pagination, freshness, and graceful errors.
- Use failing tests before every production behavior change.
- Use `python -m unittest` commands consistently with the existing test suite.
- Do not include the pre-existing CRLF-only working-tree changes in feature commits.

## File Map

- `.gitattributes`: normalize repository text files and force Python/Markdown/SQL/CSS/HTML to LF.
- `requirements.txt`: add FastAPI runtime and test-client dependencies.
- `.env.example`: document `DATABASE_URL` and web launch settings.
- `web/__init__.py`: mark the web package.
- `web/database.py`: resolve the database URL and build SQLAlchemy engines.
- `web/models.py`: define immutable price query/result/page value objects and freshness calculation.
- `web/repository.py`: execute portable joined price queries with filters, count, ordering, and pagination.
- `web/service.py`: validate normalized filters and enrich rows with freshness metadata.
- `web/app.py`: construct the FastAPI app, dependencies, API route, page route, and safe error responses.
- `web/templates/index.html`: render search controls, results, status messages, and pagination.
- `web/static/styles.css`: provide responsive, accessible visual presentation.
- `tools/seed_demo_db.py`: create a reproducible SQLite schema and sample KAMIS rows.
- `tests/test_web_database.py`: verify URL defaults and engine creation.
- `tests/test_web_service.py`: verify query behavior, pagination, filters, and freshness boundaries.
- `tests/test_web_api.py`: verify JSON contract, validation, empty results, and DB failure behavior.
- `tests/test_web_pages.py`: verify HTML form, result, empty, pagination, and failure states.
- `README.md`: present the web product, architecture, setup, API examples, testing, and screenshot.

---

### Task 1: Reproducible Web Runtime and Demo Database

**Files:**
- Create: `.gitattributes`
- Modify: `requirements.txt`
- Modify: `.env.example`
- Create: `web/__init__.py`
- Create: `web/database.py`
- Create: `tools/seed_demo_db.py`
- Create: `tests/test_web_database.py`

**Interfaces:**
- Produces: `resolve_database_url(environ: Mapping[str, str] | None = None) -> str`
- Produces: `create_web_engine(database_url: str | None = None) -> Engine`
- Produces: `seed_database(engine: Engine) -> int`
- The seed schema provides `Category`, `Product`, `ProductVariant`, `Grade`, and `RecentPriceSnapshot` with the same relevant column names as `sql/schema.sql`.

- [ ] **Step 1: Write failing database configuration tests**

Create `tests/test_web_database.py`:

```python
import unittest

from sqlalchemy import text

from web.database import create_web_engine, resolve_database_url


class WebDatabaseTests(unittest.TestCase):
    def test_resolve_database_url_defaults_to_demo_sqlite(self):
        result = resolve_database_url({})
        self.assertTrue(result.startswith("sqlite:///"))
        self.assertTrue(result.endswith("database/smartshopping.db"))

    def test_resolve_database_url_prefers_environment(self):
        result = resolve_database_url({"DATABASE_URL": "sqlite:///:memory:"})
        self.assertEqual(result, "sqlite:///:memory:")

    def test_create_web_engine_executes_sqlite_query(self):
        engine = create_web_engine("sqlite:///:memory:")
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT 1")).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_web_database -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'web'`.

- [ ] **Step 3: Add web dependencies and line-ending policy**

Append these packages to `requirements.txt`, using versions resolved by a clean installation before commit:

```text
fastapi
httpx
jinja2
uvicorn
```

Create `.gitattributes`:

```gitattributes
* text=auto
*.py text eol=lf
*.md text eol=lf
*.sql text eol=lf
*.html text eol=lf
*.css text eol=lf
```

Add to `.env.example`:

```dotenv
# Optional web database; omit to use database/smartshopping.db
DATABASE_URL=
```

- [ ] **Step 4: Implement the database boundary**

Create an empty `web/__init__.py` and create `web/database.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
import os

from sqlalchemy import Engine, create_engine

from config import SQLITE_PATH, ensure_directories


def resolve_database_url(environ: Mapping[str, str] | None = None) -> str:
    values = os.environ if environ is None else environ
    configured = values.get("DATABASE_URL", "").strip()
    return configured or f"sqlite:///{SQLITE_PATH.as_posix()}"


def create_web_engine(database_url: str | None = None) -> Engine:
    ensure_directories()
    url = database_url or resolve_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite:") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)
```

- [ ] **Step 5: Write a failing seed test**

Extend `tests/test_web_database.py`:

```python
from tools.seed_demo_db import seed_database

    def test_seed_database_creates_repeatable_sample_rows(self):
        engine = create_web_engine("sqlite:///:memory:")
        first_count = seed_database(engine)
        second_count = seed_database(engine)
        with engine.connect() as connection:
            stored = connection.execute(text("SELECT COUNT(*) FROM RecentPriceSnapshot")).scalar_one()
        self.assertEqual(first_count, 6)
        self.assertEqual(second_count, 6)
        self.assertEqual(stored, 6)
```

Use `Engine`, not a URL string, in the seed interface so the in-memory test keeps one database connection pool. Update the interface to `seed_database(engine: Engine) -> int`.

- [ ] **Step 6: Run the seed test and verify RED**

Run: `python -m unittest tests.test_web_database.WebDatabaseTests.test_seed_database_creates_repeatable_sample_rows -v`

Expected: FAIL because `tools.seed_demo_db` does not exist.

- [ ] **Step 7: Implement deterministic SQLite seeding**

Create `tools/seed_demo_db.py` with SQLAlchemy `text()` statements that:

1. Create the five normalized KAMIS tables using SQLite-compatible primary and foreign keys.
2. Delete child rows before parent rows inside `engine.begin()`.
3. Insert six fixed examples covering 배추, 사과, 양파; 도매 and 소매; and dates that render more than one freshness state relative to 2026-08-23.
4. Return the inserted snapshot count.
5. Run `seed_database(create_web_engine())` under `if __name__ == "__main__"` and print only `Seeded 6 price snapshots.`.

The inserted snapshot identity must remain `(variant_id, grade_code, examined_date, product_cls_code, unit, unit_size)`, matching `sql/schema.sql`.

- [ ] **Step 8: Verify Task 1 and commit**

Run:

```bash
python -m unittest tests.test_web_database -v
python -m unittest discover -s tests -v
git diff --check
```

Expected: all tests PASS and `git diff --check` prints nothing. If the clean environment lacks dependencies, create a workspace-local Linux virtual environment, install `requirements.txt`, and rerun the same commands using that environment's Python.

Commit only Task 1 files:

```bash
git add .gitattributes requirements.txt .env.example web/__init__.py web/database.py tools/seed_demo_db.py tests/test_web_database.py
git commit -m "chore: add reproducible web demo runtime"
```

---

### Task 2: Price Query Repository and Service

**Files:**
- Create: `web/models.py`
- Create: `web/repository.py`
- Create: `web/service.py`
- Create: `tests/test_web_service.py`

**Interfaces:**
- Consumes: `create_web_engine(database_url: str | None = None) -> Engine`
- Consumes: normalized tables seeded by `seed_database(engine: Engine) -> int`
- Produces: `PriceFilters(query: str | None, market_type: Literal["retail", "wholesale"] | None, page: int, page_size: int)`
- Produces: `PriceItem` with item, variety, market, grade, unit, price, examined date, and freshness fields.
- Produces: `PricePage(items: tuple[PriceItem, ...], page: int, page_size: int, total: int, total_pages: int)`
- Produces: `PriceRepository.search(filters: PriceFilters) -> tuple[list[dict[str, object]], int]`
- Produces: `PriceService.search(filters: PriceFilters, today: date | None = None) -> PricePage`

- [ ] **Step 1: Write failing service tests with an in-memory seeded DB**

Create `tests/test_web_service.py`. In `setUp`, build `sqlite:///:memory:`, call `seed_database`, and construct `PriceService(PriceRepository(engine))`. Add focused tests:

```python
def test_search_filters_partial_item_name(self):
    result = self.service.search(PriceFilters(query="배", page=1, page_size=20), today=date(2026, 8, 23))
    self.assertEqual({item.item_name for item in result.items}, {"배추"})

def test_search_maps_retail_market_filter(self):
    result = self.service.search(PriceFilters(market_type="retail", page=1, page_size=20), today=date(2026, 8, 23))
    self.assertTrue(result.items)
    self.assertEqual({item.product_cls_name for item in result.items}, {"소매"})

def test_search_returns_stable_pagination_metadata(self):
    result = self.service.search(PriceFilters(page=2, page_size=2), today=date(2026, 8, 23))
    self.assertEqual(result.page, 2)
    self.assertEqual(result.page_size, 2)
    self.assertEqual(result.total, 6)
    self.assertEqual(result.total_pages, 3)
    self.assertEqual(len(result.items), 2)

def test_freshness_uses_inclusive_boundaries(self):
    self.assertEqual(classify_freshness(date(2026, 7, 24), date(2026, 8, 23)), (30, "FRESH", "최신"))
    self.assertEqual(classify_freshness(date(2025, 8, 23), date(2026, 8, 23)), (365, "CAUTION", "주의"))
    self.assertEqual(classify_freshness(date(2025, 8, 22), date(2026, 8, 23)), (366, "STALE", "오래됨"))
```

- [ ] **Step 2: Run the service tests and verify RED**

Run: `python -m unittest tests.test_web_service -v`

Expected: FAIL because `web.models`, `web.repository`, and `web.service` do not exist.

- [ ] **Step 3: Implement immutable query and result models**

Create `web/models.py` using frozen dataclasses. Enforce `page >= 1`, `1 <= page_size <= 100`, and the two allowed market values in `PriceFilters.__post_init__`. Define:

```python
def classify_freshness(examined_date: date, today: date) -> tuple[int, str, str]:
    days = max((today - examined_date).days, 0)
    if days <= 30:
        return days, "FRESH", "최신"
    if days <= 365:
        return days, "CAUTION", "주의"
    return days, "STALE", "오래됨"
```

`PriceItem` must use `date` for `examined_date` and `int` for `price`. `PricePage.items` must be a tuple so callers do not mutate service results.

- [ ] **Step 4: Implement portable repository SQL**

Create `web/repository.py`. Query the five normalized tables directly rather than relying on the MySQL-only view. Use bound parameters for all user input, `LOWER(p.item_name) LIKE LOWER(:query)`, and map `retail` to `소매`, `wholesale` to `도매`. Run a separate `COUNT(*)` query with identical joins and filters. Order by `s.examined_date DESC, p.item_name ASC, s.snapshot_id ASC`, then apply `LIMIT :limit OFFSET :offset`.

- [ ] **Step 5: Implement service enrichment**

Create `web/service.py`. Convert repository row mappings into `PriceItem`, normalize an empty query to no filter, use `date.today()` only when the caller does not provide `today`, and calculate `total_pages` as `(total + page_size - 1) // page_size` with zero retained for empty results.

- [ ] **Step 6: Verify Task 2 and commit**

Run:

```bash
python -m unittest tests.test_web_service -v
python -m unittest discover -s tests -v
git diff --check
```

Expected: all tests PASS.

Commit:

```bash
git add web/models.py web/repository.py web/service.py tests/test_web_service.py
git commit -m "feat: add price search service"
```

---

### Task 3: Price Search REST API

**Files:**
- Create: `web/app.py`
- Create: `web/schemas.py`
- Create: `tests/test_web_api.py`

**Interfaces:**
- Consumes: `PriceService.search(filters: PriceFilters, today: date | None = None) -> PricePage`
- Produces: `create_app(service: PriceService | None = None) -> FastAPI`
- Produces: module-level `app` for `uvicorn web.app:app`.
- Produces: `GET /api/prices?q=&market_type=&page=1&page_size=20`.
- Error contract: `{"detail": {"code": "PRICE_SERVICE_UNAVAILABLE", "message": "가격 정보를 불러올 수 없습니다."}}` with HTTP 503.

- [ ] **Step 1: Write failing API contract tests**

Create `tests/test_web_api.py` using `TestClient(create_app(service))`. Use a real in-memory repository for success tests and a small service stub that raises `SQLAlchemyError` for the failure test. Cover:

```python
def test_api_returns_paginated_prices(self):
    response = self.client.get("/api/prices", params={"q": "배추", "page": 1, "page_size": 1})
    self.assertEqual(response.status_code, 200)
    body = response.json()
    self.assertEqual(body["page"], 1)
    self.assertEqual(body["page_size"], 1)
    self.assertGreaterEqual(body["total"], 1)
    self.assertEqual(body["items"][0]["item_name"], "배추")
    self.assertIn(body["items"][0]["freshness_status"], {"FRESH", "CAUTION", "STALE"})

def test_api_rejects_invalid_market_type(self):
    response = self.client.get("/api/prices", params={"market_type": "invalid"})
    self.assertEqual(response.status_code, 422)

def test_api_returns_empty_page_as_success(self):
    response = self.client.get("/api/prices", params={"q": "없는품목"})
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["items"], [])
    self.assertEqual(response.json()["total"], 0)

def test_api_hides_database_failure_details(self):
    response = failing_client.get("/api/prices")
    self.assertEqual(response.status_code, 503)
    self.assertEqual(response.json()["detail"]["code"], "PRICE_SERVICE_UNAVAILABLE")
    self.assertNotIn("password", response.text.lower())
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `python -m unittest tests.test_web_api -v`

Expected: FAIL because `web.app` does not exist.

- [ ] **Step 3: Implement API schemas**

Create `web/schemas.py` with Pydantic response models matching every `PriceItem` field and `PricePage` metadata. Configure dates to serialize as ISO `YYYY-MM-DD` strings through Pydantic's default JSON behavior.

- [ ] **Step 4: Implement the FastAPI application factory and API route**

Create `web/app.py` with:

```python
def create_app(service: PriceService | None = None) -> FastAPI:
    application = FastAPI(title="SmartShopping Price API", version="1.0.0")
    price_service = service or PriceService(PriceRepository(create_web_engine()))

    @application.get("/api/prices", response_model=PricePageResponse)
    def list_prices(
        q: str | None = Query(default=None, max_length=100),
        market_type: Literal["retail", "wholesale"] | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> PricePageResponse:
        ...

    return application


app = create_app()
```

Catch `SQLAlchemyError` at the route boundary, log with `logger.exception("Price query failed")`, and raise the specified HTTP 503 without including the exception text in the response.

- [ ] **Step 5: Verify Task 3 and commit**

Run:

```bash
python -m unittest tests.test_web_api -v
python -m unittest discover -s tests -v
python -c "from web.app import app; assert app.title == 'SmartShopping Price API'"
git diff --check
```

Expected: all commands exit zero.

Commit:

```bash
git add web/app.py web/schemas.py tests/test_web_api.py
git commit -m "feat: expose price search API"
```

---

### Task 4: Accessible Price Search Page and Portfolio Documentation

**Files:**
- Modify: `web/app.py`
- Create: `web/templates/index.html`
- Create: `web/static/styles.css`
- Create: `tests/test_web_pages.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the same `PriceService` instance and `PriceFilters` used by `/api/prices`.
- Produces: `GET /` with `q`, `market_type`, and `page`; fixed HTML page size 20.
- Produces: safe page error state with HTTP 503 and Korean guidance.

- [ ] **Step 1: Write failing page tests**

Create `tests/test_web_pages.py` with real in-memory seeded service setup. Cover:

```python
def test_page_renders_search_form_and_price(self):
    response = self.client.get("/", params={"q": "배추"})
    self.assertEqual(response.status_code, 200)
    self.assertIn('name="q"', response.text)
    self.assertIn('value="배추"', response.text)
    self.assertIn("배추", response.text)
    self.assertIn("신선도", response.text)

def test_page_renders_empty_result_message(self):
    response = self.client.get("/", params={"q": "없는품목"})
    self.assertEqual(response.status_code, 200)
    self.assertIn("검색 결과가 없습니다", response.text)

def test_page_keeps_filter_in_pagination_link(self):
    response = self.client.get("/", params={"q": "배추", "market_type": "retail"})
    self.assertIn("q=%EB%B0%B0%EC%B6%94", response.text)
    self.assertIn("market_type=retail", response.text)

def test_page_hides_database_failure_details(self):
    response = failing_client.get("/")
    self.assertEqual(response.status_code, 503)
    self.assertIn("잠시 후 다시 시도", response.text)
    self.assertNotIn("password", response.text.lower())
```

- [ ] **Step 2: Run page tests and verify RED**

Run: `python -m unittest tests.test_web_pages -v`

Expected: FAIL because `/` and the template do not exist.

- [ ] **Step 3: Implement the page route**

Mount `web/static` at `/static`, initialize `Jinja2Templates(directory="web/templates")`, and add `GET /` to `create_app`. Construct `PriceFilters` with a fixed `page_size=20`, call the shared service, and render `index.html` with `request`, `result`, `q`, `market_type`, and `error`. On `SQLAlchemyError`, render the same template with HTTP 503, an empty result, and `error="가격 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."`.

- [ ] **Step 4: Implement the accessible responsive template**

Create `index.html` with semantic `<header>`, `<main>`, `<form role="search">`, explicit `<label>` elements, an `aria-live="polite"` status region, and a results table. Render price using thousands separators, date as ISO text, and freshness as both code and Korean label. Preserve `q` and `market_type` in previous/next links using Jinja URL generation. Escape all user values through Jinja auto-escaping and never use `|safe`.

Create `styles.css` with a neutral finance-service palette, visible `:focus-visible`, status badges whose text remains visible without color, a max-width content container, and a mobile breakpoint that allows the table wrapper to scroll horizontally.

- [ ] **Step 5: Verify the page tests GREEN**

Run: `python -m unittest tests.test_web_pages -v`

Expected: all page tests PASS.

- [ ] **Step 6: Update portfolio documentation**

Revise `README.md` so its opening describes the price-search web product before the ETL implementation. Add:

- a 30-second reviewer path: create venv, install, seed, start;
- `python tools/seed_demo_db.py` and `uvicorn web.app:app --reload` commands;
- `http://127.0.0.1:8000` and `/docs` URLs;
- one `/api/prices?q=배추&market_type=retail` request and shortened response;
- updated architecture showing browser, FastAPI, service, repository, DB, and offline ETL;
- a test command and observed test count after final verification;
- design decisions: offline ETL separation, SQLite demo/MySQL operation, safe DB errors;
- a screenshot path `docs/images/price-search.png` only after an actual screenshot is captured.

Remove or revise statements that say the project has no automation only if the implemented behavior makes them false. Do not claim cloud deployment.

- [ ] **Step 7: Run final verification**

From a workspace-local Linux virtual environment:

```bash
python tools/seed_demo_db.py
python -m unittest discover -s tests -v
python -c "from fastapi.testclient import TestClient; from web.app import app; response = TestClient(app).get('/'); assert response.status_code == 200"
git diff --check
git status --short
```

Expected:

- Seed command reports exactly six snapshots.
- Every test passes with zero errors and zero failures.
- Smoke request exits zero.
- `git diff --check` prints nothing.
- `git status --short` contains only Task 4 changes plus the already-known CRLF-only user changes.

- [ ] **Step 8: Commit page and documentation separately**

First commit the working page:

```bash
git add web/app.py web/templates/index.html web/static/styles.css tests/test_web_pages.py
git commit -m "feat: add price search web page"
```

Then rerun the full test suite and commit documentation and a real screenshot, if captured:

```bash
python -m unittest discover -s tests -v
git add README.md docs/images/price-search.png
git commit -m "docs: present SmartShopping web service"
```

If no screenshot can be captured in the execution environment, omit the image reference and commit only `README.md`; do not add a placeholder image.

## Final Review Checklist

- [ ] Compare every completed behavior against all 12 sections of the approved design spec.
- [ ] Confirm API and page use one `PriceService` instance per application.
- [ ] Confirm SQL uses bound parameters and no user input is interpolated.
- [ ] Confirm responses and HTML never expose connection URLs, passwords, or raw exceptions.
- [ ] Confirm generated DB and local environments remain ignored.
- [ ] Confirm each feature commit contains only its declared files.
- [ ] Confirm the existing CRLF-only changes remain uncommitted and unmodified.
