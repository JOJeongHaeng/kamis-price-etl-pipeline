# Render KAMIS SQLite Startup Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate Render's SQLite database from the full KAMIS API before starting FastAPI instead of seeding six demo rows.

**Architecture:** Add a portable SQLite KAMIS schema selected by SQLAlchemy dialect, reuse it for demo seeding, and make an empty normalized API result fail the ETL. Render starts `main.py` with SQLite and a dashboard-managed KAMIS key before Uvicorn.

**Tech Stack:** Python 3.13, urllib, SQLAlchemy, SQLite, FastAPI, Render Blueprint, unittest

**Spec:** `docs/superpowers/specs/2026-08-24-render-kamis-sqlite-design.md`

## Global Constraints

- Keep MySQL ETL, API/CSV contracts, SQLite demo, web routes, filters, pagination, health, CI, and free Render plan.
- Never commit the KAMIS service key; declare it with `sync: false`.
- A zero-row KAMIS result must fail startup instead of serving demo or empty data.
- Render ETL and web must use the same `database/smartshopping.db` file.

---

### Task 1: Add a shared SQLite KAMIS schema

**Files:**
- Create: `sql/sqlite_schema.sql`
- Modify: `config.py`
- Modify: `etl/load.py`
- Modify: `tools/seed_demo_db.py`
- Modify: `tests/test_load.py`
- Modify: `tests/test_web_database.py`

**Interfaces:**
- Produces: `ensure_schema(schema_path, engine)` selecting `SQLITE_SCHEMA_PATH` for SQLite.
- Consumes: the same five KAMIS table columns used by loader and demo seed.

- [ ] Write a failing SQLite integration test that calls `ensure_schema(SCHEMA_PATH, sqlite_engine)`, loads a normalized snapshot containing all comparison-price fields, and asserts the stored row.
- [ ] Run `python -m unittest tests.test_load -v`; verify RED because MySQL DDL cannot execute on SQLite.
- [ ] Add SQLite DDL for `Category`, `Product`, `ProductVariant`, `Grade`, and every `RecentPriceSnapshot` column; select it by `engine.dialect.name`.
- [ ] Replace the duplicated demo `SCHEMA_STATEMENTS` with statements read from `sql/sqlite_schema.sql` while preserving repeatable six-row seeding.
- [ ] Run `python -m unittest tests.test_load tests.test_web_database -v`; expect PASS.
- [ ] Commit with `feat: support KAMIS loading into SQLite`.

### Task 2: Reject empty KAMIS startup data

**Files:**
- Modify: `tests/test_pipeline.py`
- Modify: `etl/pipeline.py`

**Interfaces:**
- Produces: `run_pipeline()` raising `KamisApiError("KAMIS API returned no valid price rows")` for zero normalized rows.

- [ ] Add a failing test patching the fetch response to an empty item list and asserting the exact `KamisApiError` message.
- [ ] Run `python -m unittest tests.test_pipeline.PipelineTests.test_run_pipeline_rejects_empty_kamis_data -v`; verify RED because the current pipeline writes empty outputs.
- [ ] Add the minimal guard immediately after normalization and before schema/CSV/DB mutations.
- [ ] Run `python -m unittest tests.test_pipeline tests.test_api_extract -v`; expect PASS.
- [ ] Commit with `fix: fail startup on empty KAMIS data`.

### Task 3: Switch Render startup from demo seed to KAMIS sync

**Files:**
- Modify: `tests/test_deployment_config.py`
- Modify: `tools/validate_deployment_config.py`
- Modify: `render.yaml`
- Modify: `README.md`

**Interfaces:**
- Produces: Blueprint start command `python main.py && uvicorn web.app:app --host 0.0.0.0 --port $PORT` and environment variables `DB_DRIVER=sqlite`, `KAMIS_SERVICE_KEY` with `sync: false`.

- [ ] Update the deployment semantic test expectations first and run `python -m unittest tests.test_deployment_config -v`; verify RED on old seed command and missing env vars.
- [ ] Update the validator and Blueprint with the exact command and environment contracts.
- [ ] Update README deployment text to state real KAMIS startup sync, secret registration, restart behavior, and that six-row seed remains local/CI only.
- [ ] Run `python -m unittest tests.test_deployment_config tests.test_deployment_smoke -v`; expect PASS.
- [ ] Commit with `deploy: sync KAMIS data before Render startup`.

### Task 4: Verify, merge, push, and deploy

**Files:**
- Modify only if verification exposes a planned-contract defect.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: green branch and deployment handoff for the Render secret.

- [ ] Run `python -m compileall -q config.py db.py main.py etl tools web tests`.
- [ ] Run `python -m unittest discover -s tests -v`; require zero failures/errors.
- [ ] Run `git diff --check main...HEAD` and inspect `git status --short`.
- [ ] Merge locally after user choice, verify again, and push only with authorization.
- [ ] Ask the user to enter `KAMIS_SERVICE_KEY` in Render and sync the Blueprint; never request the key value in chat.
- [ ] Verify GitHub Actions and then public `/health`, `/api/prices`, filtering, pagination, and a total greater than six.
