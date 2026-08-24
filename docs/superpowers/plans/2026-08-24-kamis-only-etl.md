# KAMIS-Only ETL Dependency Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mixed XLSX/PDF/KAMIS pipeline with a dependency-minimal KAMIS-only JSON pipeline while preserving its CSV, database, API, web, SQLite demo, CI, and deployment contracts.

**Architecture:** KAMIS JSON is fetched with `urllib`, normalized into ordered `list[dict[str, object]]` records, written with `csv.DictWriter`, and upserted with SQLAlchemy. The FastAPI service continues to read KAMIS relational tables and never performs remote collection during a web request.

**Tech Stack:** Python standard library, FastAPI, Pydantic, SQLAlchemy, PyMySQL, Jinja2, Uvicorn, unittest, httpx2, PyYAML

**Spec:** `docs/superpowers/specs/2026-08-24-kamis-only-etl-design.md`

## Global Constraints

- `python main.py` is the only ETL command; remove `--raw-dir`, `--skip-pdfs`, `--include-api`, and `--api-only`.
- Preserve KAMIS pagination, normalization, CSV filenames, UTF-8 BOM, column order, DB upsert identity, FastAPI response schema, filters, pagination, web UI, `/health`, SQLite demo, GitHub Actions, and Render behavior.
- Use only `dict`, `list`, and Python standard types in KAMIS transformation and CSV generation; remove pandas, XLSX, and PDF processing dependencies.
- Keep MySQL through `mysql+pymysql` and keep the KAMIS-only SQLite demo.
- Do not rewrite or delete dated historical design documents.

---

### Task 1: Replace pandas KAMIS transformation with canonical row lists

**Files:**
- Modify: `tests/test_api_transform.py`
- Modify: `etl/api_transform.py`

**Interfaces:**
- Consumes: KAMIS response `dict[str, Any]` and optional UTC `datetime`.
- Produces: `normalize_kamis_prices(...) -> list[dict[str, object]]` and `create_kamis_dimensions(rows) -> dict[str, list[dict[str, object]]]`.

- [ ] **Step 1: Write failing row-list contract tests**

Update assertions to require real lists and literal row dictionaries, including numeric/date cleanup, duplicate-last behavior, deterministic ordering, canonical empty list, and dimension row order:

```python
rows = normalize_kamis_prices(response, collected_at=datetime(2026, 8, 24, tzinfo=timezone.utc))
self.assertIsInstance(rows, list)
self.assertEqual(rows[0]["price"], 12340)
self.assertEqual(rows[0]["price_date"], "2026-08-23")
self.assertEqual(normalize_kamis_prices({"body": {"items": {"item": []}}}), [])
self.assertEqual(dimensions["category"], [{"category_code": "100", "category_name": "식량작물"}])
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m unittest tests.test_api_transform -v`

Expected: FAIL because current functions return `pandas.DataFrame` objects.

- [ ] **Step 3: Implement standard-library normalization**

Replace `pd.to_numeric`, `pd.to_datetime`, DataFrame deduplication, and DataFrame sorting with:

```python
def normalize_kamis_prices(response: dict[str, Any], *, collected_at: datetime | None = None) -> list[dict[str, object]]:
    records_by_key: dict[tuple[object, ...], dict[str, object]] = {}
    for source_row in _price_rows(response):
        record = _normalize_row(source_row, collected_at=collected_at)
        if record is not None:
            records_by_key[_snapshot_key(record)] = record
    return sorted(records_by_key.values(), key=_snapshot_sort_key)

def create_kamis_dimensions(snapshot_rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    return {
        "category": _unique_rows(snapshot_rows, ("category_code",), ("category_code", "category_name")),
        "product": _unique_rows(snapshot_rows, ("item_code",), ("item_code", "item_name", "category_code")),
        "product_variant": _unique_rows(snapshot_rows, ("item_code", "variety_code"), ("item_code", "variety_code", "variety_name")),
        "grade": _unique_rows(snapshot_rows, ("grade_code",), ("grade_code", "grade_name")),
    }
```

Parse accepted provider date forms explicitly with `datetime.strptime`; parse cleaned prices through `Decimal` so rounding remains deterministic.

- [ ] **Step 4: Run focused and API extraction tests**

Run: `python -m unittest tests.test_api_transform tests.test_api_extract -v`

Expected: all tests PASS with no pandas import.

- [ ] **Step 5: Commit**

```bash
git add etl/api_transform.py tests/test_api_transform.py
git commit -m "refactor: normalize KAMIS rows without pandas"
```

### Task 2: Convert KAMIS database loading to row lists

**Files:**
- Create: `tests/test_load.py`
- Modify: `etl/load.py`

**Interfaces:**
- Consumes: the category, product, variant, grade, and snapshot row lists from Task 1.
- Produces: `load_kamis_outputs(category_rows, product_rows, variant_rows, grade_rows, snapshot_rows, engine) -> dict[str, int]`.

- [ ] **Step 1: Write a failing SQLite loader integration test**

Build a temporary SQLite KAMIS schema, call `load_kamis_outputs` twice with changed price/name values, and assert literal row counts plus updated database values:

```python
first = load_kamis_outputs(categories, products, variants, grades, snapshots, engine=engine)
second = load_kamis_outputs(categories, products, updated_variants, grades, updated_snapshots, engine=engine)
self.assertEqual(first, {"categories_upserted": 1, "products_upserted": 1, "variants_upserted": 1, "grades_upserted": 1, "snapshots_written": 1})
self.assertEqual(connection.execute(text("SELECT price FROM RecentPriceSnapshot")).scalar_one(), 13000)
```

- [ ] **Step 2: Run the loader test and verify RED**

Run: `python -m unittest tests.test_load -v`

Expected: ERROR because the current loader calls `.to_dict("records")` on lists.

- [ ] **Step 3: Implement list-based KAMIS loading and delete legacy loading**

Remove `_get_or_create_item_id`, `_get_or_create_week_id`, `_upsert_weekly_report`, and `load_pipeline_outputs`. Iterate row mappings directly and replace pandas missing-value handling with a standard helper:

```python
def _normalize_scalar(value: object) -> object | None:
    return None if value in (None, "") else value

def load_kamis_outputs(category_rows, product_rows, variant_rows, grade_rows, snapshot_rows, engine=default_engine):
    with engine.begin() as conn:
        for row in category_rows:
            _upsert_by_code(conn, "Category", "category_code", "category_name", row)
        # preserve existing Product, ProductVariant, Grade and snapshot upsert SQL
```

- [ ] **Step 4: Run loader, transform, database, and web database tests**

Run: `python -m unittest tests.test_load tests.test_api_transform tests.test_web_database -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add etl/load.py tests/test_load.py
git commit -m "refactor: load KAMIS records without dataframes"
```

### Task 3: Make the pipeline and CLI KAMIS-only

**Files:**
- Modify: `tests/test_pipeline.py`
- Modify: `etl/pipeline.py`
- Modify: `main.py`
- Modify: `config.py`

**Interfaces:**
- Consumes: `fetch_recent_kamis_prices()`, Task 1 row transformers, Task 2 loader, `API_OUTPUT_DIR`, and `SCHEMA_PATH`.
- Produces: `write_csv(rows, columns, output_dir, file_name) -> Path` and `run_pipeline(engine=default_engine) -> dict[str, object]`.

- [ ] **Step 1: Write failing CSV and single-flow pipeline tests**

Replace legacy metadata tests with observable KAMIS behaviors. Assert UTF-8 BOM and literal headers from a temporary CSV, then patch only the external fetch boundary and assert five output files and summary counts:

```python
output = write_csv([], RECENT_PRICE_SNAPSHOT_COLUMNS, output_dir, "recent_price_snapshot.csv")
self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))
self.assertEqual(output.read_text(encoding="utf-8-sig").splitlines()[0], ",".join(RECENT_PRICE_SNAPSHOT_COLUMNS))

summary = run_pipeline(engine=engine)
self.assertEqual(summary["recent_price_snapshot_rows"], 1)
self.assertEqual(set(summary["outputs"]), {"recent_price_snapshot_csv", "category_csv", "product_csv", "product_variant_csv", "grade_csv"})
```

- [ ] **Step 2: Run pipeline tests and verify RED**

Run: `python -m unittest tests.test_pipeline -v`

Expected: FAIL because `write_csv` is not public and current `run_pipeline` retains legacy arguments and outputs.

- [ ] **Step 3: Implement KAMIS-only orchestration**

Use `csv.DictWriter` with `encoding="utf-8-sig"` and `newline=""`; always write the header. Simplify `run_pipeline`:

```python
def run_pipeline(engine=default_engine) -> dict[str, object]:
    ensure_directories()
    snapshot_rows = normalize_kamis_prices(fetch_recent_kamis_prices())
    dimensions = create_kamis_dimensions(snapshot_rows)
    ensure_schema(SCHEMA_PATH, engine=engine)
    # write the five fixed CSV artifacts and load all KAMIS rows
    return {"category_rows": len(dimensions["category"]), "recent_price_snapshot_rows": len(snapshot_rows), "load_summary": load_summary, "outputs": outputs}
```

Remove legacy imports, date parsing, XLSX/PDF loops and summaries. Make `main.py` call `run_pipeline()` without argparse. Retain only `PROCESSED_DATA_DIR`, `API_OUTPUT_DIR`, `SCHEMA_PATH`, API settings, and DB settings in `config.py`.

- [ ] **Step 4: Run pipeline, API, web, and deployment tests**

Run: `python -m unittest tests.test_pipeline tests.test_api_extract tests.test_api_transform tests.test_web_api tests.test_web_pages tests.test_deployment_config -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add etl/pipeline.py main.py config.py tests/test_pipeline.py
git commit -m "refactor: make ETL pipeline KAMIS-only"
```

### Task 4: Remove legacy modules, schemas, tests, and dependencies

**Files:**
- Delete: `etl/extract.py`
- Delete: `etl/pdf_prices.py`
- Delete: `etl/report.py`
- Delete: `etl/transform.py`
- Delete: `tools/classify_pdf_sources.py`
- Delete: `tools/ingest_text_based_pdfs.py`
- Delete: `tests/test_extract.py`
- Delete: `tests/test_pdf_prices.py`
- Delete: `tests/test_report.py`
- Delete: `tests/test_transform.py`
- Modify: `tests/test_schema.py`
- Modify: `sql/schema.sql`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: KAMIS-only loader and query schema.
- Produces: a MySQL schema containing only `Category`, `Product`, `ProductVariant`, `Grade`, `RecentPriceSnapshot`, and `KAMISPriceAnalysis`; a direct-dependency requirements file.

- [ ] **Step 1: Write a failing schema behavior test**

Update `tests/test_schema.py` to split SQL statements and assert the exact KAMIS table creation set and analysis view, demonstrating that legacy tables would violate the contract:

```python
self.assertEqual(
    created_tables,
    {"Category", "Product", "ProductVariant", "Grade", "RecentPriceSnapshot"},
)
self.assertIn("CREATE OR REPLACE VIEW KAMISPriceAnalysis", schema)
```

- [ ] **Step 2: Run schema tests and verify RED**

Run: `python -m unittest tests.test_schema -v`

Expected: FAIL because five legacy table definitions remain.

- [ ] **Step 3: Remove legacy artifacts and minimize dependencies**

Delete the listed modules/tools/tests, remove legacy table DDL, and set requirements to direct imports/contracts only:

```text
PyMySQL==1.2.0
SQLAlchemy==2.0.52
fastapi==0.141.1
pydantic==2.13.4
httpx2==2.12.0
jinja2==3.1.6
uvicorn==0.52.4
PyYAML==6.0.3
```

Run `rg` across Python files to confirm no production or current test import references pandas, openpyxl, pdfplumber, pdfminer, XLSX/PDF modules, or `mysql.connector`.

- [ ] **Step 4: Run schema and all remaining tests**

Run: `python -m unittest discover -s tests -v`

Expected: all remaining tests PASS and no legacy test modules are discovered.

- [ ] **Step 5: Commit**

```bash
git add -A etl tools tests sql/schema.sql requirements.txt
git commit -m "refactor: remove legacy file ETL dependencies"
```

### Task 5: Rewrite README for the actual KAMIS architecture

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the final CLI, CSV artifacts, schema, web routes, deployment configuration, and direct dependencies.
- Produces: current setup, architecture, usage, API, Power BI, test, CI, and Render documentation without active XLSX/PDF claims.

- [ ] **Step 1: Inventory README claims against current files**

Check every command, file path, route, table, and dependency in README against the repository. Human documentation earns no source-text unit test; correctness is verified against executable commands and artifacts.

- [ ] **Step 2: Rewrite README**

Lead with the approved Korean project description, show the exact KAMIS-only flow, document `python main.py`, five API CSVs for Power BI, KAMIS tables/view, SQLite demo, web/API routes, environment variables, unittest command, GitHub Actions and Render deployment. Remove active XLSX/PDF/pandas descriptions, legacy flags, tables, outputs, and dashboard sections.

- [ ] **Step 3: Verify documented commands and links**

Run: `python -m unittest tests.test_web_database tests.test_deployment_config tests.test_deployment_smoke -v`

Expected: SQLite demo, deployment configuration, and public route smoke tests PASS.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: describe KAMIS-only project architecture"
```

### Task 6: Final dependency and behavior verification

**Files:**
- Modify only if verification exposes a defect in an already planned file.

**Interfaces:**
- Consumes: all previous task outputs.
- Produces: evidence that the repository contains only the current KAMIS execution path and all retained behavior passes.

- [ ] **Step 1: Audit imports and requirements**

Run:

```bash
rg -n "^(from|import) " --glob "*.py"
rg -n "pdfplumber|pdfminer|openpyxl|pandas|numpy|mysql.connector|XLSX|PDF" --glob "!docs/superpowers/**" --glob "!docs/plans/**"
```

Expected: no active code, test, requirements, or README references to removed technologies; historical dated documents may retain them.

- [ ] **Step 2: Compile all Python sources**

Run: `python -m compileall -q .`

Expected: exit code 0.

- [ ] **Step 3: Run the complete test suite freshly**

Run: `python -m unittest discover -s tests -v`

Expected: all discovered tests PASS with 0 failures and 0 errors.

- [ ] **Step 4: Inspect repository state and commit history**

Run:

```bash
git status --short
git log --oneline main..HEAD
git diff --check main...HEAD
```

Expected: clean worktree, task-scoped commits present, and no whitespace errors.
