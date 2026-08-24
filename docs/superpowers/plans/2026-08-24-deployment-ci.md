# SmartShopping Deployment and CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a database-aware health endpoint, automated GitHub test workflow, and reproducible Render deployment configuration for the SmartShopping demo service.

**Architecture:** Keep health checking at the web application's database boundary: the app receives an SQLAlchemy `Engine`, and a focused readiness function checks connectivity, the snapshot table, and at least one row without contacting KAMIS. Treat CI and Render YAML as executable configuration, with standard-library tests loading YAML through a small project-owned validator instead of asserting source text.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, SQLite, standard-library `unittest`, GitHub Actions, Render Blueprint, PyYAML

**Spec:** `docs/superpowers/specs/2026-08-23-deployment-ci-design.md`

## Global Constraints

- `GET /health` returns exactly `{"status": "ok", "database": "ready"}` with HTTP 200 only when `SELECT 1` succeeds and `RecentPriceSnapshot` contains at least one row.
- SQLAlchemy errors, a missing table, and an empty table return exactly `{"status": "unavailable", "database": "unavailable"}` with HTTP 503.
- Health responses never expose connection strings, passwords, or original database errors; failures are logged server-side.
- Health checks never call the KAMIS API.
- CI runs on pushes to `main`, pull requests targeting `main`, and manual dispatch, using `.python-version` and pip caching.
- CI runs `PYTHONWARNINGS=error python -m unittest discover -s tests`, compilation, and demo seeding in that order.
- Render uses a free Python web service, seeds six SQLite rows before Uvicorn starts, checks `/health`, and auto-deploys `main`.
- Generated databases and credentials remain untracked, and no remote push or external Render mutation is performed in this plan.
- Every production behavior change follows RED, GREEN, refactor, full verification, then a focused Git commit.

## File Map

- `web/health.py`: run the readiness SQL and return a boolean while allowing SQLAlchemy failures to reach the HTTP boundary.
- `web/app.py`: inject the health engine and expose the safe `/health` HTTP contract.
- `tests/test_web_health.py`: exercise seeded, empty, missing-table, and SQLAlchemy-error states through the real ASGI app.
- `.github/workflows/test.yml`: run the required test, compile, and seed gates on the three approved triggers.
- `tests/test_deployment_config.py`: execute the deployment-config loader and assert semantic CI/Render contracts.
- `tools/validate_deployment_config.py`: safely load YAML files and validate their consumer-visible deployment settings.
- `.python-version`: pin the deployment family to Python 3.13.
- `render.yaml`: define the free Render service, build/start commands, health path, and main auto-deploy behavior.
- `requirements.txt`: include the YAML parser used by configuration validation.

---

### Task 1: Database Health Endpoint

**Files:**
- Create: `tests/test_web_health.py`
- Create: `web/health.py`
- Modify: `web/app.py`

**Interfaces:**
- Produces: `database_is_ready(engine: sqlalchemy.Engine) -> bool`
- Modifies: `create_app(service: PriceService | None = None, health_engine: Engine | None = None) -> FastAPI`
- Produces: `GET /health -> {"status": str, "database": str}` with HTTP 200 or 503.

- [ ] **Step 1: Write the failing seeded-database test**

Create an in-memory engine, call `seed_database(engine)`, construct `create_app(service, health_engine=engine)`, request `/health` with the existing `httpx2.ASGITransport`, and assert literal status 200 and the exact JSON object `{"status": "ok", "database": "ready"}`. This catches removal of either readiness query or the success mapping.

- [ ] **Step 2: Verify RED**

Run: `../../.venv/Scripts/python.exe -m unittest tests.test_web_health.WebHealthTests.test_health_returns_ready_for_seeded_database -v`

Expected: FAIL because `/health` is not registered (HTTP 404).

- [ ] **Step 3: Implement the minimum successful readiness path**

In `web/health.py`, execute `SELECT 1` and `SELECT COUNT(*) FROM RecentPriceSnapshot` inside `engine.connect()`, returning `count >= 1`. In `create_app`, retain an injected `health_engine` or create one once, and add `/health` returning the exact success JSON when the helper returns true.

- [ ] **Step 4: Verify GREEN**

Run the single test from Step 2 and expect PASS.

- [ ] **Step 5: Write failing unavailable-state tests**

Add separate tests for an empty seeded schema after deleting all snapshots, a fresh engine with no table, and an engine whose connection raises `SQLAlchemyError("password=do-not-expose")`. Assert HTTP 503, the exact fixed unavailable JSON, an `ERROR` log containing `Database health check failed`, and absence of `password` from the response body. Each test catches a distinct false-positive readiness branch or secret leak.

- [ ] **Step 6: Verify RED**

Run: `../../.venv/Scripts/python.exe -m unittest tests.test_web_health -v`

Expected: FAIL because false readiness and SQLAlchemy failures are not yet mapped to the fixed 503 response.

- [ ] **Step 7: Implement safe failure mapping**

Return a `JSONResponse(status_code=503, content={"status": "unavailable", "database": "unavailable"})` when readiness is false. Catch `SQLAlchemyError` only at the route boundary, log with `logger.exception("Database health check failed")`, and return the same fixed response.

- [ ] **Step 8: Verify and commit Task 1**

Run:

```bash
../../.venv/Scripts/python.exe -m unittest tests.test_web_health -v
../../.venv/Scripts/python.exe -m unittest discover -s tests
git diff --check
```

Expected: 64 tests pass and `git diff --check` is silent.

Commit:

```bash
git add docs/superpowers/plans/2026-08-24-deployment-ci.md tests/test_web_health.py web/health.py web/app.py
git commit -m "feat: add database health endpoint"
```

---

### Task 2: GitHub Actions Test Workflow

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `tests/test_deployment_config.py`
- Create: `tools/validate_deployment_config.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `load_yaml(path: pathlib.Path) -> dict[str, object]`
- Produces: `validate_ci(config: dict[str, object]) -> list[str]`, returning an empty list for a valid workflow and human-readable violations otherwise.

- [ ] **Step 1: Add PyYAML and write a failing semantic workflow test**

Add a pinned `PyYAML` version to `requirements.txt`. In `tests/test_deployment_config.py`, load `.github/workflows/test.yml` through `load_yaml`, call `validate_ci`, and assert `[]`. The validator must require `push.branches == ["main"]`, `pull_request.branches == ["main"]`, `workflow_dispatch`, Ubuntu, checkout, setup-python with `python-version-file: .python-version` and pip cache, dependency installation, the exact warning-as-error unittest command, the exact compile command, and the exact seed command.

- [ ] **Step 2: Verify RED**

Run: `../../.venv/Scripts/python.exe -m unittest tests.test_deployment_config.DeploymentConfigTests.test_ci_workflow_matches_required_execution_contract -v`

Expected: FAIL because the validator/workflow does not exist.

- [ ] **Step 3: Implement the loader, validator, and workflow**

Use `yaml.safe_load` in `load_yaml`. Implement `validate_ci` with explicit structural checks and no environment dumps or secrets. Create one `test` job in `.github/workflows/test.yml` with the required triggers and ordered steps: checkout, Python setup from `.python-version` with pip cache keyed by `requirements.txt`, install, tests, compile, seed.

- [ ] **Step 4: Verify and commit Task 2**

Run:

```bash
../../.venv/Scripts/python.exe -m unittest tests.test_deployment_config -v
set PYTHONWARNINGS=error&& ../../.venv/Scripts/python.exe -m unittest discover -s tests
../../.venv/Scripts/python.exe -m compileall -q config.py etl tools web tests
../../.venv/Scripts/python.exe tools/seed_demo_db.py
git diff --check
```

Expected: all tests pass, compilation exits 0, and seeding prints `Seeded 6 price snapshots.` On non-Windows runners, use `PYTHONWARNINGS=error` before the same unittest command.

Commit:

```bash
git add .github/workflows/test.yml tests/test_deployment_config.py tools/validate_deployment_config.py requirements.txt
git commit -m "ci: run tests for pushes and pull requests"
```

---

### Task 3: Render Blueprint and Python Version

**Files:**
- Create: `.python-version`
- Create: `render.yaml`
- Modify: `tests/test_deployment_config.py`
- Modify: `tools/validate_deployment_config.py`

**Interfaces:**
- Produces: `validate_render(config: dict[str, object], python_version: str) -> list[str]`.
- Consumes: `tools/seed_demo_db.py`, `web.app:app`, and `/health` from Tasks 1–2.

- [ ] **Step 1: Write a failing Render contract test**

Load `render.yaml`, read `.python-version`, call `validate_render`, and assert `[]`. Require exactly one service with `type: web`, `runtime: python`, `plan: free`, `branch: main`, `autoDeploy: true`, `buildCommand: pip install -r requirements.txt`, `startCommand: python tools/seed_demo_db.py && uvicorn web.app:app --host 0.0.0.0 --port $PORT`, `healthCheckPath: /health`, and Python version text `3.13`.

- [ ] **Step 2: Verify RED**

Run: `../../.venv/Scripts/python.exe -m unittest tests.test_deployment_config.DeploymentConfigTests.test_render_blueprint_matches_runtime_contract -v`

Expected: FAIL because `render.yaml` and `.python-version` do not exist.

- [ ] **Step 3: Implement Render validation and configuration**

Add `validate_render` with semantic dictionary checks. Create `.python-version` containing only `3.13` and `render.yaml` defining the single service contract above; do not add `DATABASE_URL`, credentials, or persistent disk settings.

- [ ] **Step 4: Verify Render configuration and live process**

Run the configuration test, then seed the database and start Uvicorn with a temporary `PORT`. Poll the actual process and assert HTTP 200 for `/health`, `/`, `/api/prices`, and `/docs`; assert `/health` returns the exact ready JSON and `/api/prices` reports six rows. Stop the temporary process after verification.

- [ ] **Step 5: Run the full local CI contract and commit Task 3**

Run:

```bash
../../.venv/Scripts/python.exe -m unittest discover -s tests
../../.venv/Scripts/python.exe -m compileall -q config.py etl tools web tests
../../.venv/Scripts/python.exe tools/seed_demo_db.py
git diff --check
git status --short
```

Expected: all tests and compilation pass; seeding prints `Seeded 6 price snapshots.`; generated SQLite and bytecode remain absent from `git status`.

Commit:

```bash
git add .python-version render.yaml tests/test_deployment_config.py tools/validate_deployment_config.py
git commit -m "chore: configure Render deployment"
```

---

### Task 4: Final Requirement Audit

**Files:**
- Verify only; no planned file changes.

**Interfaces:**
- Consumes all outputs from Tasks 1–3.
- Produces local evidence ready for the separately authorized push and Render provisioning phase.

- [ ] **Step 1: Re-read the approved spec and map every in-scope local requirement to a test, command, or committed setting**

Confirm that README publication and screenshot work remain deferred until a real URL exists, as required by the spec's external-work ordering.

- [ ] **Step 2: Run fresh verification**

Run the full unittest suite with warnings as errors, compileall, seed script, real Uvicorn four-path smoke test, `git diff --check`, `git status --short --branch`, and `git log --oneline -4`.

- [ ] **Step 3: Request code review and address findings**

Review the three feature commits against this plan and the approved spec. Fix Critical and Important findings with TDD and commit them into the owning functional boundary; report Minor findings explicitly.

- [ ] **Step 4: Hand off without external mutation**

Report the worktree path, branch, test count, exact commits, and the remaining external sequence: confirm GitHub target, push, observe Actions, connect Render Blueprint, verify public paths, then add the README URL/badge/screenshot commit.
