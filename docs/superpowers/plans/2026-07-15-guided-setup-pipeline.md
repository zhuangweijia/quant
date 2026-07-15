# Quant Desk Guided Setup Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an administrator initialize an empty Quant Desk installation, train and activate a qualified model, and generate the first daily recommendations from the dashboard with persistent progress and safe retries.

**Architecture:** Add a PostgreSQL-backed `SetupRun` aggregate and an injected `SetupPipeline` orchestrator that reuses the existing data, model, and analysis services. Expose readiness and start APIs, then render a state-driven dashboard card that polls only while setup is active and reuses the existing analysis progress display.

**Tech Stack:** FastAPI, async SQLAlchemy, Alembic, PostgreSQL, pytest, Vue 3, TypeScript, Pinia, Vite, Vitest

## Global Constraints

- Only administrators may start setup or daily analysis; ordinary users receive read-only status.
- Preserve the existing `MODEL_IC_THRESHOLD` gate and never activate a model that fails it.
- Persist long-running setup stages and per-stock progress in PostgreSQL.
- Do not introduce Celery, a separate worker, or another task queue.
- Reuse existing `DataSyncService`, `MLModelService`, and `AnalysisPipeline` business logic.
- Repeated setup and analysis triggers must be idempotent.
- Tests must not call real market-data providers or train a real model.

---

### Task 1: Persist Setup Runs

**Files:**
- Create: `backend/app/models/setup_run.py`
- Create: `backend/alembic/versions/b8f31a2c4d90_add_setup_runs.py`
- Create: `backend/app/schemas/setup.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/alembic/env.py`
- Test: `backend/tests/test_setup_model.py`

**Interfaces:**
- Produces: `SetupRun`, `SetupStage`, `SetupStatusResponse`, and `SetupStartResponse`.
- Consumes: `TimestampMixin` and PostgreSQL `JSONB` conventions already used by `AnalysisRun`.

- [ ] **Step 1: Install the declared backend development dependencies**

Run from `backend/`: `uv pip install --python .venv/bin/python -e '.[dev]'`

Expected: pytest, pytest-asyncio, pytest-cov, and ruff are installed into `backend/.venv` without changing application dependency declarations.

- [ ] **Step 2: Write the failing model contract test**

Create `backend/tests/test_setup_model.py` with assertions that `SetupRun.__tablename__ == "setup_runs"`, that the primary key is `run_id`, that `status` defaults to `running`, and that `SetupStatusResponse(readiness="uninitialized", counts=...)` serializes all required keys.

```python
from app.models.setup_run import SetupRun
from app.schemas.setup import SetupCounts, SetupStatusResponse


def test_setup_run_mapping_and_status_schema():
    assert SetupRun.__tablename__ == "setup_runs"
    assert [column.name for column in SetupRun.__table__.primary_key] == ["run_id"]
    assert SetupRun.__table__.c.status.default.arg == "running"

    response = SetupStatusResponse(
        readiness="uninitialized",
        counts=SetupCounts(stocks=0, daily_bars=0, models=0, today_predictions=0),
        active_model=None,
        run=None,
        can_start=True,
        can_run_analysis=False,
    )
    assert response.model_dump()["counts"]["daily_bars"] == 0
```

- [ ] **Step 3: Run the test and confirm the missing-module failure**

Run from `backend/`: `.venv/bin/pytest tests/test_setup_model.py -q`

Expected: FAIL because `app.models.setup_run` does not exist.

- [ ] **Step 4: Add the model, schemas, exports, and migration**

Implement `SetupRun` with `run_id`, `status`, `current_stage`, `stages`, `started_at`, `finished_at`, and `error`. Define setup response schemas with exact literals for `uninitialized`, `initializing`, `failed`, and `ready`. Add the model import to both model registries and add an Alembic migration with `down_revision = "7e781c825fac"` that creates and drops `setup_runs`.

```python
class SetupRun(TimestampMixin, Base):
    __tablename__ = "setup_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    stages: Mapped[dict] = mapped_column(postgresql.JSONB, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
```

- [ ] **Step 5: Verify the model contract and migration**

Run from `backend/`:

```bash
.venv/bin/pytest tests/test_setup_model.py -q
DATABASE_URL=postgresql+asyncpg://quant@127.0.0.1:5436/quant .venv/bin/alembic upgrade head
DATABASE_URL=postgresql+asyncpg://quant@127.0.0.1:5436/quant .venv/bin/alembic current
```

Expected: test PASS and Alembic reports `b8f31a2c4d90 (head)`.

- [ ] **Step 6: Commit the persistence layer**

```bash
git add backend/app/models/setup_run.py backend/app/models/__init__.py backend/app/schemas/setup.py backend/alembic/env.py backend/alembic/versions/b8f31a2c4d90_add_setup_runs.py backend/tests/test_setup_model.py
git commit -m "feat: persist setup pipeline runs"
```

### Task 2: Build the Resumable Setup Orchestrator

**Files:**
- Create: `backend/app/services/setup_pipeline.py`
- Create: `backend/tests/test_setup_pipeline.py`
- Modify: `backend/scripts/bootstrap_data.py`
- Modify: `backend/app/services/analysis_pipeline.py`

**Interfaces:**
- Consumes: `DataSyncService.sync_csi300_constituents()`, `sync_daily_bars_full(symbol)`, `sync_fundamentals()`, `validate_data_integrity()`, `MLModelService.train()`, `activate_model(db, version)`, and a new `AnalysisPipeline.run_and_wait(trigger_type)`.
- Produces: `SetupPipeline.start() -> str`, `SetupPipeline.interrupt_stale_runs() -> int`, and persisted stage progress.

- [ ] **Step 1: Write orchestration tests using fakes**

Create tests that inject fake data, model, analysis, and store dependencies. Assert the exact seven-stage call order, per-stock progress, idempotent start behavior, quality-gate failure propagation, and stale-run interruption.

```python
@pytest.mark.asyncio
async def test_setup_pipeline_runs_all_stages_in_order():
    store = FakeSetupStore()
    data = FakeDataSync(symbols=["000001", "000002"])
    model = FakeModel(ic=0.05)
    analysis = FakeAnalysis(predictions=2)
    pipeline = SetupPipeline(store=store, data_sync=data, model_service=model, analysis=analysis)

    run_id = await pipeline.start(wait=True)

    assert store.runs[run_id]["status"] == "completed"
    assert store.completed_stages(run_id) == [
        "constituents", "daily_bars", "fundamentals", "validation",
        "training", "activation", "analysis",
    ]
    assert store.runs[run_id]["stages"]["daily_bars"]["current"] == 2
```

- [ ] **Step 2: Run the orchestration tests and confirm RED**

Run: `.venv/bin/pytest tests/test_setup_pipeline.py -q`

Expected: FAIL because `SetupPipeline` and `run_and_wait` do not exist.

- [ ] **Step 3: Implement the injected pipeline and SQLAlchemy store**

Define a `SetupStore` protocol plus `SqlAlchemySetupStore`. Implement `start(wait=False)` with an `asyncio.Lock`; a running setup returns its existing run ID. `_run()` must persist stage transitions, continue past individual stock failures, update `last_synced_date` after a successful full sync, stop on stage exceptions, and retain the original error summary at 1024 characters or fewer.

Recovery rules are exact:

- Always refresh constituents.
- Skip full history for a stock whose `last_synced_date` is non-null.
- Always refresh fundamentals and run integrity validation.
- Reuse an active model; otherwise reuse the newest inactive model whose file exists; otherwise train.
- Call `activate_model()` before analysis.
- Require `run_and_wait()` to return a positive prediction count before marking setup complete.

Add `AnalysisPipeline.run_and_wait(trigger_type="manual")`, which returns the completed `AnalysisRun`; keep `trigger()` asynchronous. Make the CLI script call `setup_pipeline.start(wait=True)` so CLI and UI share one workflow.

- [ ] **Step 4: Run service tests and the existing analysis tests**

Run: `.venv/bin/pytest tests/test_setup_pipeline.py -q`

Expected: PASS with no network or model training calls.

- [ ] **Step 5: Commit the orchestrator**

```bash
git add backend/app/services/setup_pipeline.py backend/app/services/analysis_pipeline.py backend/scripts/bootstrap_data.py backend/tests/test_setup_pipeline.py
git commit -m "feat: orchestrate resumable first-time setup"
```

### Task 3: Expose Readiness and Safe Trigger APIs

**Files:**
- Create: `backend/app/api/v1/setup.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_setup_api.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/api/v1/analysis.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `SetupPipeline.start()`, `SetupPipeline.interrupt_stale_runs()`, setup schemas, `Stock`, `DailyBar`, `ModelVersion`, `Prediction`, and `AnalysisRun`.
- Produces: `GET /api/v1/setup/status`, `POST /api/v1/setup/start`, and idempotent `POST /api/v1/analysis/trigger`.

- [ ] **Step 1: Write API behavior tests**

Create shared `admin_client` and `user_client` fixtures in `backend/tests/conftest.py`. Set the test database URL before importing `app`, override `get_db` with a transaction-scoped async session, override `get_current_user` with admin and ordinary `User` objects, and inject a fake setup pipeline so no background market task starts. Then cover:

```python
def test_setup_status_empty_database_is_uninitialized(admin_client):
    response = admin_client.get("/api/v1/setup/status")
    assert response.status_code == 200
    assert response.json()["data"]["readiness"] == "uninitialized"
    assert response.json()["data"]["can_start"] is True


def test_non_admin_cannot_start_setup(user_client):
    response = user_client.post("/api/v1/setup/start")
    assert response.status_code == 403


def test_analysis_without_active_model_returns_409(admin_client):
    response = admin_client.post("/api/v1/analysis/trigger")
    assert response.status_code == 409
```

- [ ] **Step 2: Run API tests and confirm missing routes/guards**

Run: `.venv/bin/pytest tests/test_setup_api.py -q`

Expected: FAIL with setup route 404 or missing response fields.

- [ ] **Step 3: Implement setup status, start, lifecycle recovery, and analysis guards**

The status endpoint must count CSI 300 stocks, daily bars, model versions, and today's predictions in four scalar queries; load the latest setup run and active model; and derive:

```python
if latest_run and latest_run.status == "running":
    readiness = "initializing"
elif latest_run and latest_run.status in {"failed", "interrupted"}:
    readiness = "failed"
elif latest_run and latest_run.status == "completed" and active_model and stock_count and bar_count:
    readiness = "ready"
else:
    readiness = "uninitialized"
```

Use `AdminUser` on the start endpoint. At application startup, call `interrupt_stale_runs()` after `init_db()` and before the scheduler starts. Harden analysis triggering so a running `AnalysisRun` returns its ID, while missing data or an active model raises `HTTPException(409, detail=...)`.

- [ ] **Step 4: Run API tests and the full backend test suite**

Run: `.venv/bin/pytest -q`

Expected: all tests PASS.

- [ ] **Step 5: Commit the API layer**

```bash
git add backend/app/api/v1/setup.py backend/app/api/v1/__init__.py backend/app/api/v1/analysis.py backend/app/main.py backend/tests/conftest.py backend/tests/test_setup_api.py
git commit -m "feat: expose setup readiness and safe triggers"
```

### Task 4: Add the Dashboard Setup Experience

**Files:**
- Create: `frontend/src/api/setup.ts`
- Create: `frontend/src/views/dashboard/setup-state.ts`
- Create: `frontend/src/views/dashboard/SetupStatusCard.vue`
- Create: `frontend/src/views/dashboard/setup-state.test.ts`
- Create: `frontend/src/views/dashboard/SetupStatusCard.test.ts`
- Create: `frontend/src/views/dashboard/useSetupPolling.ts`
- Create: `frontend/src/views/dashboard/useSetupPolling.test.ts`
- Modify: `frontend/src/views/dashboard/DashboardView.vue`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/scripts/verify-spacious-layout.mjs`

**Interfaces:**
- Consumes: setup status/start endpoints, analysis status/trigger endpoints, `authStore.role`, existing Button/Card/Badge/Progress components.
- Produces: `setupApi`, `getSetupPresentation(status, analysisStatus)`, a reusable `SetupStatusCard`, and administrator dashboard actions.

- [ ] **Step 1: Add Vitest, Vue Test Utils, and failing UI-state tests**

Add `vitest`, `@vue/test-utils`, and `happy-dom` as development dependencies, add a `test` script, and configure Vitest's `happy-dom` environment in `vite.config.ts`. Test the pure state mapping before adding UI code:

```typescript
import { describe, expect, it } from 'vitest'
import { getSetupPresentation } from './setup-state'

describe('getSetupPresentation', () => {
  it('offers first-time setup for an empty installation', () => {
    const view = getSetupPresentation({ readiness: 'uninitialized' }, null)
    expect(view.title).toBe('完成首次配置')
    expect(view.action).toBe('start_setup')
    expect(view.emptyMessage).toContain('首次配置')
  })

  it('offers daily analysis only after setup is ready', () => {
    const view = getSetupPresentation({ readiness: 'ready' }, { status: 'idle' })
    expect(view.action).toBe('run_analysis')
    expect(view.actionLabel).toBe('运行今日分析')
  })

  it('does not claim a completed analysis failed when no strong picks exist', () => {
    const view = getSetupPresentation({ readiness: 'ready' }, { status: 'done' })
    expect(view.emptyMessage).toContain('未产生符合条件的强推股票')
  })
})
```

Add component and polling tests that assert ordinary users see no action button, administrators emit `start`, polling starts only for `initializing`, and timers are cleared for `ready` and on unmount. Use `vi.useFakeTimers()` and an injected fetch callback; no HTTP request is made by these tests.

- [ ] **Step 2: Run Vitest and confirm RED**

Run from `frontend/`: `npm test -- --run src/views/dashboard/setup-state.test.ts src/views/dashboard/SetupStatusCard.test.ts src/views/dashboard/useSetupPolling.test.ts`

Expected: FAIL because the dashboard setup modules do not exist.

- [ ] **Step 3: Implement API types, pure state mapping, status card, and dashboard integration**

`setup.ts` must define `SetupReadiness`, `SetupStage`, `SetupRun`, `SetupStatus`, `getStatus()`, and `start()`. `SetupStatusCard` receives `status`, `isAdmin`, `starting`, and `analysisRunning`; it emits `start`, `run-analysis`, and `open-model`.

Dashboard behavior must:

- Fetch ranking, analysis status, and setup status together.
- Poll setup status every three seconds only while readiness is `initializing`.
- Clear the timer on completion, failure, or component unmount.
- Prevent repeat clicks with local `starting` and `triggeringAnalysis` flags.
- Show setup controls only for administrators.
- Refresh all dashboard data when setup or analysis completes.
- Replace the unconditional Pipeline empty message with `getSetupPresentation(...).emptyMessage`.
- Back off failed polling requests at 3, 6, 12, 24, then 30 seconds and reset to three seconds after a successful response.

- [ ] **Step 4: Run focused tests, layout verification, and production build**

Run from `frontend/`:

```bash
npm test -- --run src/views/dashboard/setup-state.test.ts src/views/dashboard/SetupStatusCard.test.ts src/views/dashboard/useSetupPolling.test.ts
npm run test:login-copy
npm run test:layout
npm run build
```

Expected: all commands exit 0; build may retain the existing large ECharts chunk warning.

- [ ] **Step 5: Commit the dashboard experience**

```bash
git add frontend/src/api/setup.ts frontend/src/views/dashboard/setup-state.ts frontend/src/views/dashboard/setup-state.test.ts frontend/src/views/dashboard/SetupStatusCard.vue frontend/src/views/dashboard/SetupStatusCard.test.ts frontend/src/views/dashboard/useSetupPolling.ts frontend/src/views/dashboard/useSetupPolling.test.ts frontend/src/views/dashboard/DashboardView.vue frontend/vite.config.ts frontend/package.json frontend/package-lock.json frontend/scripts/verify-spacious-layout.mjs
git commit -m "feat: guide administrators through first-time setup"
```

### Task 5: End-to-End Verification and Documentation Alignment

**Files:**
- Modify: `README.md`
- Verify: `docs/superpowers/specs/2026-07-15-guided-setup-pipeline-design.md`

**Interfaces:**
- Consumes: the complete setup API and dashboard flow.
- Produces: documented one-click setup behavior and verified application artifacts.

- [ ] **Step 1: Update the quick-start documentation**

Replace the command-line-only bootstrap instructions with the dashboard workflow while retaining the CLI as a fallback:

```markdown
### 首次数据初始化

使用管理员账户登录后，在看板点击「一键初始化并生成推荐」。系统会同步沪深 300 数据、训练并验证模型，然后生成首批推荐。该过程通常需要 30–60 分钟，刷新页面不会丢失进度。

命令行环境仍可在 `backend/` 运行 `python scripts/bootstrap_data.py`，它与页面使用同一套 SetupPipeline。
```

- [ ] **Step 2: Run fresh backend and frontend verification**

Run:

```bash
cd backend && .venv/bin/pytest -q
cd frontend && npm test -- --run
cd frontend && npm run test:login-copy
cd frontend && npm run test:layout
cd frontend && npm run build
git diff --check
```

Expected: all commands exit 0 and no whitespace errors are reported.

- [ ] **Step 3: Apply migrations and perform local HTTP smoke checks**

With the local services configured for PostgreSQL, run `alembic upgrade head`, start the API, and verify authenticated requests to setup status and setup start. Use injected or pre-seeded data for the completion path; do not start the real 30–60 minute market download as part of automated verification.

Expected: status returns the correct readiness object, a non-admin start returns 403, and an admin start returns a run ID without blocking the HTTP response.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md
git commit -m "docs: document one-click initial setup"
```
