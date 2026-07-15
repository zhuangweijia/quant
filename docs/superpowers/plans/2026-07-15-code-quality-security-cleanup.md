# Code Quality and Dependency Security Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the complete backend Ruff baseline from 358 findings to zero and the frontend production dependency audit from four vulnerable packages to zero without framework major upgrades or business behavior changes.

**Architecture:** Treat Ruff and npm audit as executable regression tests. Apply only Ruff safe fixes and formatting first, then isolate the remaining semantic changes into core contracts, runtime services, and migration/script batches. Resolve frontend advisories with compatible direct upgrades and a narrowly scoped DOMPurify override, then run full artifact and HTTP verification.

**Tech Stack:** Python 3.11+, Ruff, Pytest, FastAPI, SQLAlchemy, Alembic, Vue 3, TypeScript, npm, Vitest, Vite.

## Global Constraints

- `ruff check app tests scripts alembic` must return zero findings without adding global rule ignores.
- `npm audit --omit=dev` must return zero vulnerabilities.
- Do not run `ruff --unsafe-fixes` or `npm audit fix --force`.
- Do not upgrade Vue, Vite, Pinia, Vue Router, or Zod to a new major version.
- Do not downgrade Monaco Editor.
- Do not change API response contracts, recommendation logic, or start a real market-data setup run.
- Preserve the user's existing services and unrelated worktree content.

---

### Task 1: Apply Safe Mechanical Python Normalization

**Files:**
- Modify: `backend/app/**/*.py`
- Modify: `backend/tests/**/*.py`
- Modify: `backend/scripts/*.py`
- Modify: `backend/alembic/**/*.py`
- Exclude from autofix: `backend/app/core/__init__.py`
- Exclude from autofix: `backend/app/schemas/__init__.py`
- Exclude from autofix: `backend/app/models/__init__.py`

**Interfaces:**
- Consumes: the current Ruff configuration in `backend/pyproject.toml` and the recorded 358-finding baseline.
- Produces: mechanically normalized Python files with safe autofixes and Ruff formatting applied, leaving only findings that require semantic judgment.

- [ ] **Step 1: Reproduce and record the failing lint baseline**

Run:

```bash
cd backend
.venv/bin/ruff check --statistics app tests scripts alembic
```

Expected: exit 1 with 358 findings, including 127 `E501`, 77 `F401`, 63 `I001`, 26 `UP017`, and 25 `UP032` findings.

- [ ] **Step 2: Apply only Ruff safe fixes**

Run:

```bash
cd backend
.venv/bin/ruff check --fix app tests scripts alembic \
  --exclude app/core/__init__.py \
  --exclude app/schemas/__init__.py \
  --exclude app/models/__init__.py
.venv/bin/ruff format app tests scripts alembic
```

Do not pass `--unsafe-fixes`. The three package `__init__.py` files are intentionally excluded from autofix because their imports are public exports or SQLAlchemy registration side effects; Task 2 handles them with contract tests and explicit `__all__` declarations. Formatting may still normalize their whitespace without deleting imports. Review `git diff --stat` and `git diff --check` immediately afterward.

- [ ] **Step 3: Verify mechanical changes preserve current behavior**

Run:

```bash
cd backend
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app tests scripts alembic
```

Expected: 13 tests pass and compileall exits 0.

- [ ] **Step 4: Capture the reduced semantic baseline**

Run:

```bash
cd backend
.venv/bin/ruff check --statistics app tests scripts alembic
```

Expected: exit 1, but the safe-fix categories are reduced; use the remaining output to drive Tasks 2–4.

- [ ] **Step 5: Commit mechanical normalization**

```bash
git add backend/app backend/tests backend/scripts backend/alembic
git commit -m "style: apply safe Ruff normalization"
```

---

### Task 2: Make Core Public Contracts Explicit and Lint-Clean

**Files:**
- Create: `backend/tests/test_core_contracts.py`
- Modify: `backend/app/core/__init__.py`
- Modify: `backend/app/core/exceptions.py`
- Modify: `backend/app/core/types.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Consumes: existing exception subclasses, `Market`, `Timeframe`, schema re-exports, and model import side effects.
- Produces: `AppError`, explicit `__all__` exports, Python 3.11 `StrEnum` types, and preserved Alembic model discovery.

- [ ] **Step 1: Write failing core-contract tests**

Create `backend/tests/test_core_contracts.py`:

```python
from enum import StrEnum

from app.core import AppError, Encryption, Market, StrategyLoadError, Timeframe, event_bus
from app.models import SetupRun, Stock, User
from app.schemas import LoginRequest, ResponseBase, SetupStatusResponse


def test_core_exports_are_explicit_and_stable():
    assert issubclass(StrategyLoadError, AppError)
    assert Encryption is not None
    assert event_bus is not None


def test_market_types_use_python_str_enum():
    assert issubclass(Market, StrEnum)
    assert issubclass(Timeframe, StrEnum)


def test_model_and_schema_packages_keep_public_exports():
    assert all(item is not None for item in (SetupRun, Stock, User))
    assert all(item is not None for item in (LoginRequest, ResponseBase, SetupStatusResponse))
```

- [ ] **Step 2: Run the test and confirm RED**

Run:

```bash
cd backend
.venv/bin/pytest tests/test_core_contracts.py -q
```

Expected: collection fails because `AppError` and `SetupStatusResponse` are not currently exported by those packages.

- [ ] **Step 3: Implement explicit public contracts**

In `app/core/exceptions.py`, rename the base class to `AppError` and update every subclass:

```python
class AppError(Exception):
    def __init__(self, code: int, message: str, detail: str = ""):
        self.code = code
        self.message = message
        self.detail = detail
```

Change each existing exception subclass base from `AppException` to `AppError`. Update `app/main.py` to register `AppError`. Replace star imports in `app/core/__init__.py` with explicit imports and a complete `__all__`. Convert `Market` and `Timeframe` to inherit from `StrEnum`. Add explicit imports and `__all__` entries to `app/schemas/__init__.py`; retain all existing public schema names and add the setup schema names. Keep all model classes explicitly imported and listed in `app/models/__init__.py`.

- [ ] **Step 4: Verify the core contract and full backend suite**

Run:

```bash
cd backend
.venv/bin/pytest tests/test_core_contracts.py -q
.venv/bin/pytest -q
.venv/bin/ruff check app/core app/main.py app/models/__init__.py app/schemas/__init__.py tests/test_core_contracts.py
```

Expected: core-contract tests pass, the full suite passes, and the scoped Ruff check returns 0.

- [ ] **Step 5: Commit explicit contracts**

```bash
git add backend/app/core backend/app/main.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/tests/test_core_contracts.py
git commit -m "refactor: make backend core exports explicit"
```

---

### Task 3: Resolve Runtime API and Service Findings

**Files:**
- Modify: `backend/app/api/**/*.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/middleware/**/*.py`
- Modify: `backend/app/models/*.py`
- Modify: `backend/app/schemas/*.py`
- Modify: `backend/app/services/*.py`
- Modify: `backend/app/utils/*.py`
- Modify: `backend/app/ws/*.py`
- Test: `backend/tests/test_setup_api.py`
- Test: `backend/tests/test_setup_pipeline.py`
- Test: `backend/tests/test_core_contracts.py`

**Interfaces:**
- Consumes: the reduced lint baseline after Tasks 1–2 and all existing backend behavior tests.
- Produces: lint-clean runtime modules without unused names, ambiguous locals, uppercase function-local matrices, or overlong expressions.

- [ ] **Step 1: Use the remaining Ruff findings as the failing regression**

Run:

```bash
cd backend
.venv/bin/ruff check app
```

Expected: exit 1 with exact file and line findings remaining after Tasks 1–2.

- [ ] **Step 2: Remove genuinely unused runtime names**

Before deletion, search each reported symbol with `rg`. Remove unused imports and assignments in API modules, models, schemas, WebSocket modules, and services. Replace the AKShare availability probe in `market_service.py` with:

```python
from importlib.util import find_spec

if find_spec("akshare") is None:
    logger.warning("akshare.not_installed")
else:
    try:
        provider = AKShareProvider()
        if provider._ak is None:
            raise ImportError("akshare failed to import")
        _providers[market] = provider
        return provider
    except ImportError:
        logger.warning("akshare.not_installed")
```

The function must then continue through its existing cached `MockDataProvider` fallback. Rename the audit log comprehension variable from `l` to `log`. Do not remove model imports required for SQLAlchemy mapper registration.

- [ ] **Step 3: Normalize ML locals without changing calculations**

In `app/services/ml_model.py`, rename function-local `X`, `X_train`, `X_val`, and the `X_val` parameter to `features`, `train_features`, and `validation_features`. Update every reference in the same scope. Remove only the Ruff-reported unused `settings`, `stock_names`, and other dead locals. Preserve feature column ordering, LightGBM calls, prediction scores, and formatter output.

- [ ] **Step 4: Wrap remaining long runtime expressions**

Use parentheses and one-argument-per-line formatting for API responses, SQLAlchemy statements, logger calls, notification calls, model declarations, and the factor-description mapping. Do not shorten or rewrite user-facing Chinese text merely to satisfy line length; split the Python expression instead.

- [ ] **Step 5: Verify runtime code**

Run:

```bash
cd backend
.venv/bin/ruff check app
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app
```

Expected: Ruff returns 0 for `app`, all tests pass, and compileall exits 0.

- [ ] **Step 6: Commit runtime cleanup**

```bash
git add backend/app backend/tests
git commit -m "refactor: clear backend runtime lint debt"
```

---

### Task 4: Normalize Alembic History and Maintenance Scripts

**Files:**
- Modify: `backend/alembic/env.py`
- Modify: `backend/alembic/versions/*.py`
- Modify: `backend/scripts/init_admin.py`
- Modify: `backend/scripts/reset_admin_password.py`
- Modify: `backend/scripts/bootstrap_data.py`

**Interfaces:**
- Consumes: the existing ordered Alembic revision chain ending at `b8f31a2c4d90`.
- Produces: lint-clean migration and maintenance files with unchanged revision identifiers and DDL behavior.

- [ ] **Step 1: Reproduce the migration/script lint remainder**

Run:

```bash
cd backend
.venv/bin/ruff check alembic scripts
```

Expected: exit 1 until the remaining long migration declarations and script findings are fixed.

- [ ] **Step 2: Normalize migrations without changing DDL**

Remove unused generated typing imports, use PEP 604 annotations where annotations are present, and wrap `sa.Column`, `op.create_table`, index, constraint, and alter-column arguments across lines. Preserve every `revision`, `down_revision`, table name, column type, nullable flag, default, index, constraint, and upgrade/downgrade operation.

Keep the explicit model imports in `alembic/env.py` with the existing focused `# noqa: F401` comment because autogeneration depends on import side effects.

- [ ] **Step 3: Normalize scripts**

Sort imports below each script's `sys.path` bootstrap using a targeted `# noqa: E402` only where import timing is required. Remove the three empty f-string prefixes in `reset_admin_password.py` and wrap the long messages without changing their content.

- [ ] **Step 4: Verify lint and the complete migration chain**

Run:

```bash
cd backend
.venv/bin/ruff check alembic scripts
DATABASE_URL=postgresql+asyncpg://quant@127.0.0.1:5436/quant .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+asyncpg://quant@127.0.0.1:5436/quant .venv/bin/alembic current
```

Expected: Ruff returns 0, upgrade exits 0, and current reports `b8f31a2c4d90 (head)`.

- [ ] **Step 5: Verify the complete backend lint target and tests**

Run:

```bash
cd backend
.venv/bin/ruff check app tests scripts alembic
.venv/bin/pytest -q
```

Expected: Ruff returns 0 and all backend tests pass.

- [ ] **Step 6: Commit migration and script cleanup**

```bash
git add backend/alembic backend/scripts
git commit -m "style: clear migration and script lint debt"
```

---

### Task 5: Upgrade Vulnerable Frontend Dependencies Compatibly

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Consumes: ECharts 6.0.0, Axios 1.16.0, Monaco Editor 0.55.1, and DOMPurify 3.2.7.
- Produces: ECharts 6.1.x, Axios 1.18.x, `form-data` 4.0.6 or newer, Monaco Editor 0.55.1, and DOMPurify 3.4.12 through an npm override.

- [ ] **Step 1: Reproduce the failing production audit**

Run:

```bash
cd frontend
npm audit --omit=dev
```

Expected: exit 1 with four affected packages and totals of one low, two moderate, and one high vulnerability.

- [ ] **Step 2: Add the narrow transitive override**

Add this top-level key to `frontend/package.json` using `apply_patch`:

```json
"overrides": {
  "dompurify": "3.4.12"
}
```

Do not change the `monaco-editor` version.

- [ ] **Step 3: Install compatible direct security upgrades**

Run:

```bash
cd frontend
npm install axios@^1.18.1 echarts@^6.1.0
```

Expected: `package.json` and `package-lock.json` update without a forced major framework upgrade.

- [ ] **Step 4: Verify the resolved dependency tree and audit**

Run:

```bash
cd frontend
npm ls axios form-data echarts monaco-editor dompurify
npm audit --omit=dev
```

Expected: Monaco remains 0.55.1, DOMPurify is 3.4.12, ECharts is 6.1.x, `form-data` is at least 4.0.6, the tree is valid, and audit reports zero vulnerabilities.

- [ ] **Step 5: Run all frontend regression checks**

Run:

```bash
cd frontend
npm test -- --run
npm run test:login-copy
npm run test:layout
npm run build
```

Expected: nine Vitest tests pass, both contract scripts pass, and the production build exits 0. The existing ECharts chunk-size warning is informational only.

- [ ] **Step 6: Commit dependency remediation**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "fix: remediate frontend dependency advisories"
```

---

### Task 6: Final Verification and Service Handoff

**Files:**
- Verify: `backend/app/**/*.py`
- Verify: `backend/tests/**/*.py`
- Verify: `backend/scripts/*.py`
- Verify: `backend/alembic/**/*.py`
- Verify: `frontend/package.json`
- Verify: `frontend/package-lock.json`

**Interfaces:**
- Consumes: all cleanup commits.
- Produces: fresh evidence for lint, tests, audit, build, migration, HTTP behavior, service availability, and clean Git state.

- [ ] **Step 1: Run all static, test, security, and build gates from scratch**

Run:

```bash
cd backend
.venv/bin/ruff check app tests scripts alembic
.venv/bin/pytest -q
.venv/bin/python -m compileall -q app tests scripts alembic

cd ../frontend
npm audit --omit=dev
npm test -- --run
npm run test:login-copy
npm run test:layout
npm run build
```

Expected: every command exits 0, with zero Ruff findings and zero production audit vulnerabilities.

- [ ] **Step 2: Restart development services on the existing local database**

Stop only the Quant Desk processes currently bound to ports 8000 and 3000. Start the backend against PostgreSQL on 5436 and the existing Redis on 6379, then start Vite on 3000. Do not stop PostgreSQL or delete its data.

- [ ] **Step 3: Perform authenticated HTTP smoke checks**

Verify:

```text
GET  http://127.0.0.1:8000/health                         -> 200
POST http://127.0.0.1:8000/api/v1/auth/login              -> 200
GET  http://127.0.0.1:8000/api/v1/setup/status             -> 200 with readiness
POST http://127.0.0.1:8000/api/v1/setup/start as non-admin -> 403
GET  http://127.0.0.1:3000                                 -> 200
```

Use the injected smoke application for the admin start route so it returns 202 without launching real market downloads.

- [ ] **Step 4: Confirm repository and service state**

Run:

```bash
git diff --check
git status --short
ss -ltnp
```

Expected: no whitespace errors, a clean worktree, and listeners on 127.0.0.1:3000 and 127.0.0.1:8000.
