# Settings Page Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the settings placeholder with working appearance, notification, administrator system-parameter, and account-security controls whose saved values affect the next relevant backend job.

**Architecture:** Keep `SettingsView.vue` as a thin page composer and move each settings domain into a focused card component. On the backend, validate system parameters with Pydantic, store database overrides on top of boot defaults, and pass immutable runtime snapshots into model operations while rescheduling the daily analysis job only after a successful commit.

**Tech Stack:** Vue 3, TypeScript, Pinia, Vee Validate/Zod, Reka UI components, Vitest, FastAPI, Pydantic 2, SQLAlchemy asyncio, pytest.

## Global Constraints

- Appearance preferences remain browser-local and apply immediately.
- Notification secrets are never returned as plaintext; blank secret inputs preserve existing encrypted values.
- Only administrators may read, save, or reset system parameters; ordinary users must not render or request them.
- Supported stock universe remains exactly `csi300`.
- Data and alert retention ranges are 7–3650 days.
- Model training window is 252–2520 trading days.
- Model validation window is 21–504 trading days and shorter than the training window.
- Forward-return window is 1–30 trading days.
- Forward-return threshold is greater than 0 and at most 1.
- Model IC threshold is 0–1.
- Analysis time uses valid `HH:mm` format.
- A running operation uses one immutable parameter snapshot; saved changes affect only subsequent operations.
- Password changes clear the local session but do not add server-side JWT revocation.
- Follow red-green-refactor for every task and commit only after the task's focused tests pass.

## File Structure

### Backend

- `backend/app/schemas/settings.py` — typed notification, profile, password, and system-parameter API contracts.
- `backend/app/services/settings_service.py` — encrypted setting persistence, validated default/override merge, and runtime parameter loading.
- `backend/app/api/v1/settings.py` — authenticated settings endpoints and post-commit schedule refresh.
- `backend/app/services/analysis_pipeline.py` — parameterized daily-analysis scheduling.
- `backend/app/main.py` — load persisted analysis time during application startup.
- `backend/app/services/ml_model.py` — consume an explicit validated parameter snapshot for labels, windows, and IC gates.
- `backend/app/api/v1/model.py` — load one snapshot for direct training and activation requests.
- `backend/app/services/setup_pipeline.py` — reuse one model-parameter snapshot throughout setup training and activation.
- `backend/tests/test_settings_schema_service.py` — schema validation, override parsing, and legacy fallback.
- `backend/tests/test_settings_api.py` — authorization, secret preservation, password validation, commit ordering, and rescheduling.
- `backend/tests/test_model_runtime_params.py` — threshold/window consumers and setup snapshot behavior.

### Frontend

- `frontend/src/api/client.ts` — retain structured 422 validation detail on normalized API errors.
- `frontend/src/api/client.test.ts` — normalized validation-error contract.
- `frontend/src/api/settings.ts` — typed settings DTOs and all settings endpoints.
- `frontend/src/api/settings.test.ts` — request paths and payload-contract tests.
- `frontend/src/views/settings/AppearanceSettingsCard.vue` — local theme controls.
- `frontend/src/views/settings/AppearanceSettingsCard.test.ts` — immediate theme persistence tests.
- `frontend/src/views/settings/NotificationSettingsCard.vue` — notification form, save, and test actions.
- `frontend/src/views/settings/NotificationSettingsCard.test.ts` — secret, dirty-state, and test-action behavior.
- `frontend/src/views/settings/SystemParamsCard.vue` — administrator parameter form and reset confirmation.
- `frontend/src/views/settings/SystemParamsCard.test.ts` — validation, save, and reset behavior.
- `frontend/src/views/settings/AccountSecurityCard.vue` — profile and password-change form.
- `frontend/src/views/settings/AccountSecurityCard.test.ts` — profile, validation, and logout redirect.
- `frontend/src/views/settings/SettingsView.vue` — role-aware composition only.
- `frontend/src/views/settings/SettingsView.test.ts` — administrator visibility and card isolation.

---

### Task 1: Add Typed System Settings and Runtime Override Parsing

**Files:**
- Create: `backend/app/schemas/settings.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/services/settings_service.py`
- Test: `backend/tests/test_settings_schema_service.py`

**Interfaces:**
- Produces: `SystemParams`, `SystemParamsRequest`, `NotificationConfigRequest`, `NotificationConfigResponse`, `ProfileResponse`, and `PasswordChangeRequest`.
- Produces: `get_default_system_params() -> SystemParams`, `merge_system_params(overrides: Mapping[str, str], defaults: SystemParams | None = None) -> SystemParams`, `get_system_params(db: AsyncSession) -> SystemParams`, and `load_runtime_system_params() -> SystemParams`.
- Consumes: existing `Setting`, `Encryption`, and `get_settings()` boot configuration.

- [ ] **Step 1: Write schema and merge tests that fail before the types exist**

```python
# backend/tests/test_settings_schema_service.py
import pytest
from pydantic import ValidationError

from app.schemas.settings import SystemParams
from app.services.settings_service import merge_system_params


def valid_params(**overrides):
    data = {
        "data_retention_days": 90,
        "alert_retention_days": 90,
        "model_train_window_days": 756,
        "model_val_window_days": 126,
        "forward_return_days": 5,
        "forward_return_threshold": 0.02,
        "model_ic_threshold": 0.02,
        "stock_universe": "csi300",
        "analysis_time": "17:00",
    }
    data.update(overrides)
    return data


def test_system_params_reject_invalid_ranges():
    with pytest.raises(ValidationError):
        SystemParams.model_validate(valid_params(data_retention_days=6))
    with pytest.raises(ValidationError):
        SystemParams.model_validate(valid_params(model_val_window_days=800))
    with pytest.raises(ValidationError):
        SystemParams.model_validate(valid_params(analysis_time="25:00"))


def test_system_params_reject_unknown_keys():
    with pytest.raises(ValidationError):
        SystemParams.model_validate({**valid_params(), "unused_flag": True})


def test_merge_system_params_coerces_database_strings():
    defaults = SystemParams.model_validate(valid_params())

    params = merge_system_params(
        {"forward_return_days": "10", "model_ic_threshold": "0.08"},
        defaults,
    )

    assert params.forward_return_days == 10
    assert params.model_ic_threshold == 0.08


def test_merge_system_params_replaces_bad_legacy_value_with_default():
    defaults = SystemParams.model_validate(valid_params())

    params = merge_system_params(
        {"analysis_time": "bad", "forward_return_days": "15"},
        defaults,
    )

    assert params.analysis_time == "17:00"
    assert params.forward_return_days == 15
```

- [ ] **Step 2: Run the new tests and verify the missing-module failure**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests/test_settings_schema_service.py -q'`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'app.schemas.settings'`.

- [ ] **Step 3: Implement complete Pydantic settings contracts**

```python
# backend/app/schemas/settings.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NotificationConfigRequest(StrictSettingsModel):
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = Field(default=465, ge=1, le=65535)
    email_sender: str = ""
    email_password: str = ""
    email_use_ssl: bool = True
    email_recipient: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_secret: str = ""
    notify_levels: list[Literal["info", "warning", "error"]] = Field(
        default_factory=lambda: ["warning", "error"]
    )


class NotificationConfigResponse(StrictSettingsModel):
    email_enabled: bool
    email_smtp_host: str
    email_smtp_port: int
    email_sender: str
    has_email_password: bool
    email_use_ssl: bool
    email_recipient: str
    webhook_enabled: bool
    webhook_url: str
    has_webhook_secret: bool
    notify_levels: list[str]


class SystemParams(StrictSettingsModel):
    data_retention_days: int = Field(ge=7, le=3650)
    alert_retention_days: int = Field(ge=7, le=3650)
    model_train_window_days: int = Field(ge=252, le=2520)
    model_val_window_days: int = Field(ge=21, le=504)
    forward_return_days: int = Field(ge=1, le=30)
    forward_return_threshold: float = Field(gt=0, le=1)
    model_ic_threshold: float = Field(ge=0, le=1)
    stock_universe: Literal["csi300"] = "csi300"
    analysis_time: str

    @field_validator("model_val_window_days")
    @classmethod
    def validation_window_is_shorter(cls, value: int, info):
        training = info.data.get("model_train_window_days")
        if training is not None and value >= training:
            raise ValueError("验证窗口必须短于训练窗口")
        return value

    @field_validator("analysis_time")
    @classmethod
    def valid_analysis_time(cls, value: str):
        from datetime import time

        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("分析时间必须为 HH:mm") from exc
        if len(value) != 5:
            raise ValueError("分析时间必须为 HH:mm")
        return value


class SystemParamsRequest(StrictSettingsModel):
    params: SystemParams


class ProfileResponse(StrictSettingsModel):
    username: str
    role: str
    is_active: bool
    created_at: datetime | None = None


class PasswordChangeRequest(StrictSettingsModel):
    old_password: str = Field(min_length=8, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)
    confirm_password: str = Field(min_length=8, max_length=64)
```

Export these names from `backend/app/schemas/__init__.py` without changing existing exports.

- [ ] **Step 4: Implement validated defaults, override fallback, and typed persistence**

```python
# backend/app/services/settings_service.py — replace _DEFAULT_PARAMS and typed system helpers
from collections.abc import Mapping

from pydantic import ValidationError

from app.config import get_settings
from app.schemas.settings import SystemParams


def get_default_system_params() -> SystemParams:
    settings = get_settings()
    return SystemParams(
        data_retention_days=90,
        alert_retention_days=90,
        model_train_window_days=settings.MODEL_TRAIN_WINDOW_DAYS,
        model_val_window_days=settings.MODEL_VAL_WINDOW_DAYS,
        forward_return_days=settings.FORWARD_RETURN_DAYS,
        forward_return_threshold=settings.FORWARD_RETURN_THRESHOLD,
        model_ic_threshold=settings.MODEL_IC_THRESHOLD,
        stock_universe=settings.STOCK_UNIVERSE,
        analysis_time=settings.ANALYSIS_TIME,
    )


def merge_system_params(
    overrides: Mapping[str, str],
    defaults: SystemParams | None = None,
) -> SystemParams:
    default_params = defaults or get_default_system_params()
    default_data = default_params.model_dump()
    candidate = {**default_data, **{key: value for key, value in overrides.items() if key in default_data}}

    for _ in range(len(default_data) + 1):
        try:
            return SystemParams.model_validate(candidate)
        except ValidationError as exc:
            invalid_fields = {error["loc"][0] for error in exc.errors() if error["loc"]}
            if not invalid_fields:
                logger.error("settings.params_invalid", errors=exc.errors())
                return default_params
            for field in invalid_fields:
                logger.error("settings.param_invalid", key=field, value=candidate.get(field))
                candidate[field] = default_data[field]
    return default_params


async def get_system_params(db: AsyncSession) -> SystemParams:
    result = await db.execute(
        select(Setting).where(Setting.user_id.is_(None), Setting.category == "system")
    )
    overrides = {setting.key: setting.value for setting in result.scalars().all()}
    return merge_system_params(overrides)


async def save_system_params(db: AsyncSession, params: SystemParams) -> SystemParams:
    for key, value in params.model_dump().items():
        await set_setting(db, None, "system", key, str(value))
    return await get_system_params(db)


async def reset_system_params(db: AsyncSession) -> SystemParams:
    result = await db.execute(
        select(Setting).where(Setting.user_id.is_(None), Setting.category == "system")
    )
    for setting in result.scalars().all():
        await db.delete(setting)
    await db.flush()
    return get_default_system_params()


async def load_runtime_system_params() -> SystemParams:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return await get_system_params(db)
```

- [ ] **Step 5: Run focused tests and the schema export contract**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests/test_settings_schema_service.py tests/test_core_contracts.py -q'`

Expected: all tests PASS.

- [ ] **Step 6: Commit Task 1**

```powershell
git add backend/app/schemas/settings.py backend/app/schemas/__init__.py backend/app/services/settings_service.py backend/tests/test_settings_schema_service.py
git commit -m "feat: validate runtime system settings"
```

---

### Task 2: Complete Settings Endpoints and Analysis Rescheduling

**Files:**
- Modify: `backend/app/api/v1/settings.py`
- Modify: `backend/app/services/analysis_pipeline.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings_api.py`

**Interfaces:**
- Consumes: Task 1 `SystemParamsRequest`, `get_system_params()`, `save_system_params()`, and `reset_system_params()`.
- Produces: `AnalysisPipeline.start(analysis_time: str) -> None` and `AnalysisPipeline.reschedule(analysis_time: str) -> None`.
- Preserves: current endpoint URLs and the `{ "params": ... }` system update request envelope.

- [ ] **Step 1: Write failing authorization, secret-preservation, commit-order, and scheduler tests**

```python
# backend/tests/test_settings_api.py
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1 import settings as settings_api
from app.schemas.settings import NotificationConfigRequest, SystemParams, SystemParamsRequest
from app.services.analysis_pipeline import AnalysisPipeline


def params(analysis_time="17:00"):
    return SystemParams(
        data_retention_days=90,
        alert_retention_days=90,
        model_train_window_days=756,
        model_val_window_days=126,
        forward_return_days=5,
        forward_return_threshold=0.02,
        model_ic_threshold=0.02,
        stock_universe="csi300",
        analysis_time=analysis_time,
    )


@pytest.mark.asyncio
async def test_non_admin_cannot_read_system_params():
    with pytest.raises(HTTPException) as exc_info:
        await settings_api.get_params(user=SimpleNamespace(role="user"), db=SimpleNamespace())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_blank_notification_secrets_are_not_overwritten(monkeypatch):
    set_setting = AsyncMock()
    monkeypatch.setattr("app.services.settings_service.set_setting", set_setting)
    payload = NotificationConfigRequest(email_enabled=True, email_smtp_host="smtp.example.com")

    await settings_api.save_notifications(
        user=SimpleNamespace(id="user-1"), db=SimpleNamespace(), payload=payload
    )

    saved_keys = [call.args[3] for call in set_setting.await_args_list]
    assert "email_password" not in saved_keys
    assert "webhook_secret" not in saved_keys


@pytest.mark.asyncio
async def test_system_save_commits_before_reschedule(monkeypatch):
    events = []
    db = SimpleNamespace(commit=AsyncMock(side_effect=lambda: events.append("commit")))
    monkeypatch.setattr(
        "app.services.settings_service.save_system_params",
        AsyncMock(return_value=params("18:15")),
    )
    monkeypatch.setattr(
        settings_api.analysis_pipeline,
        "reschedule",
        lambda value: events.append(f"schedule:{value}"),
    )
    monkeypatch.setattr(settings_api, "extract_request_info", lambda request: ("127.0.0.1", "test"))
    monkeypatch.setattr(settings_api, "log_action", AsyncMock())

    await settings_api.save_params(
        user=SimpleNamespace(id="user-1", role="admin"),
        db=db,
        payload=SystemParamsRequest(params=params("18:15")),
        request=SimpleNamespace(client=None, headers={}),
    )

    assert events == ["commit", "schedule:18:15"]


@pytest.mark.asyncio
async def test_system_save_does_not_reschedule_when_commit_fails(monkeypatch):
    scheduled = []
    db = SimpleNamespace(commit=AsyncMock(side_effect=RuntimeError("commit failed")))
    monkeypatch.setattr(
        "app.services.settings_service.save_system_params",
        AsyncMock(return_value=params("18:15")),
    )
    monkeypatch.setattr(settings_api.analysis_pipeline, "reschedule", scheduled.append)
    monkeypatch.setattr(settings_api, "extract_request_info", lambda request: ("127.0.0.1", "test"))
    monkeypatch.setattr(settings_api, "log_action", AsyncMock())

    with pytest.raises(RuntimeError, match="commit failed"):
        await settings_api.save_params(
            user=SimpleNamespace(id="user-1", role="admin"),
            db=db,
            payload=SystemParamsRequest(params=params("18:15")),
            request=SimpleNamespace(client=None, headers={}),
        )

    assert scheduled == []


@pytest.mark.asyncio
async def test_system_reset_commits_before_reschedule(monkeypatch):
    events = []
    db = SimpleNamespace(commit=AsyncMock(side_effect=lambda: events.append("commit")))
    monkeypatch.setattr(
        "app.services.settings_service.reset_system_params",
        AsyncMock(return_value=params("17:00")),
    )
    monkeypatch.setattr(
        settings_api.analysis_pipeline,
        "reschedule",
        lambda value: events.append(f"schedule:{value}"),
    )
    monkeypatch.setattr(settings_api, "extract_request_info", lambda request: ("127.0.0.1", "test"))
    monkeypatch.setattr(settings_api, "log_action", AsyncMock())

    await settings_api.reset_params(
        user=SimpleNamespace(id="user-1", role="admin"),
        db=db,
        request=SimpleNamespace(client=None, headers={}),
    )

    assert events == ["commit", "schedule:17:00"]


def test_analysis_pipeline_parses_and_replaces_daily_schedule():
    pipeline = AnalysisPipeline()
    pipeline._started = True
    pipeline._scheduler.add_job = lambda *args, **kwargs: setattr(pipeline, "scheduled", kwargs)

    pipeline.reschedule("18:15")

    assert pipeline.scheduled["id"] == "analysis_pipeline_daily"
    assert str(pipeline.scheduled["trigger"]).startswith("cron[hour='18', minute='15'")
```

- [ ] **Step 2: Run settings API tests and verify failures against current inline models and hard-coded schedule**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests/test_settings_api.py -q'`

Expected: FAIL because typed request models, module-level `analysis_pipeline`, explicit commit ordering, and `reschedule()` do not yet exist.

- [ ] **Step 3: Replace inline endpoint models with Task 1 schemas and typed responses**

```python
# backend/app/api/v1/settings.py — core endpoint shape
from app.schemas.settings import (
    NotificationConfigRequest,
    NotificationConfigResponse,
    PasswordChangeRequest,
    ProfileResponse,
    SystemParams,
    SystemParamsRequest,
)
from app.services.analysis_pipeline import analysis_pipeline


@router.get("/params", response_model=ResponseBase[SystemParams])
async def get_params(user: CurrentUser, db: DBSession):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作系统参数")
    from app.services.settings_service import get_system_params

    return ResponseBase(data=await get_system_params(db))


@router.put("/params", response_model=ResponseBase[SystemParams])
async def save_params(
    user: CurrentUser,
    db: DBSession,
    payload: SystemParamsRequest,
    request: Request,
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作系统参数")
    from app.services.settings_service import save_system_params

    params = await save_system_params(db, payload.params)
    ip, ua = extract_request_info(request)
    await log_action(
        db,
        user_id=user.id,
        action="settings.params_update",
        detail=params.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    analysis_pipeline.reschedule(params.analysis_time)
    return ResponseBase(data=params)
```

Apply the same typed response pattern to notification, reset, profile, and password endpoints. Keep the existing conditional `if payload.email_password` and `if payload.webhook_secret` branches exactly so blank fields preserve existing encrypted values. Use `payload.old_password`, `payload.new_password`, and `payload.confirm_password` in password validation.

Implement reset with the same post-commit scheduling rule, and return the real `datetime` profile value so `ProfileResponse` performs response validation:

```python
@router.post("/params/reset", response_model=ResponseBase[SystemParams])
async def reset_params(user: CurrentUser, db: DBSession, request: Request):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作系统参数")
    from app.services.settings_service import reset_system_params

    params = await reset_system_params(db)
    ip, ua = extract_request_info(request)
    await log_action(
        db,
        user_id=user.id,
        action="settings.params_reset",
        detail=params.model_dump(),
        ip_address=ip,
        user_agent=ua,
    )
    await db.commit()
    analysis_pipeline.reschedule(params.analysis_time)
    return ResponseBase(data=params)


@router.get("/profile", response_model=ResponseBase[ProfileResponse])
async def get_profile(user: CurrentUser):
    return ResponseBase(
        data=ProfileResponse(
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    )
```

- [ ] **Step 4: Implement parameterized scheduler methods**

```python
# backend/app/services/analysis_pipeline.py
    @staticmethod
    def _cron_trigger(analysis_time: str) -> CronTrigger:
        hour, minute = (int(part) for part in analysis_time.split(":"))
        return CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")

    def reschedule(self, analysis_time: str) -> None:
        self._analysis_time = analysis_time
        if not self._started:
            return
        self._scheduler.add_job(
            self._scheduled_run,
            trigger=self._cron_trigger(analysis_time),
            id="analysis_pipeline_daily",
            replace_existing=True,
        )

    def start(self, analysis_time: str = "17:00") -> None:
        if self._started:
            return
        self._scheduler.start()
        self._started = True
        self.reschedule(analysis_time)
        from app.services.data_sync_service import data_sync_service
        data_sync_service.register_schedules(self._scheduler)
        logger.info("analysis_pipeline.started", analysis_time=analysis_time)
```

Initialize `self._analysis_time = "17:00"` in `__init__` and remove the hard-coded 17:30 job registration.

- [ ] **Step 5: Load the persisted schedule at application startup**

```python
# backend/app/main.py — immediately before analysis_pipeline.start(...)
    from app.services.settings_service import get_system_params

    async with AsyncSessionLocal() as settings_db:
        runtime_params = await get_system_params(settings_db)

    from app.services.analysis_pipeline import analysis_pipeline

    analysis_pipeline.start(runtime_params.analysis_time)
```

- [ ] **Step 6: Run endpoint and scheduler tests**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests/test_settings_api.py tests/test_settings_schema_service.py -q'`

Expected: all tests PASS.

- [ ] **Step 7: Commit Task 2**

```powershell
git add backend/app/api/v1/settings.py backend/app/services/analysis_pipeline.py backend/app/main.py backend/tests/test_settings_api.py
git commit -m "feat: complete settings endpoints and scheduling"
```

---

### Task 3: Apply One Runtime Snapshot to Model Operations

**Files:**
- Modify: `backend/app/services/ml_model.py`
- Modify: `backend/app/api/v1/model.py`
- Modify: `backend/app/services/setup_pipeline.py`
- Modify: `backend/app/services/cleanup_service.py`
- Modify: `backend/tests/test_setup_pipeline.py`
- Test: `backend/tests/test_model_runtime_params.py`

**Interfaces:**
- Consumes: Task 1 `SystemParams`, `get_system_params(db)`, and `load_runtime_system_params()`.
- Produces: `MLModelService.train(params: SystemParams | None = None)`, `MLModelService.generate_labels(start_date, end_date, params)`, and `MLModelService.activate_model(db, version, params: SystemParams | None = None)`.
- Produces: setup model protocol methods `load_params()`, `train(params)`, and `activate(version, params)`.

- [ ] **Step 1: Write failing pure-consumer and setup snapshot tests**

```python
# backend/tests/test_model_runtime_params.py
from app.schemas.settings import SystemParams
from app.services.cleanup_service import retention_days_by_table
from app.services.ml_model import classify_relative_return, validation_cutoff


def params(**updates):
    data = {
        "data_retention_days": 90,
        "alert_retention_days": 90,
        "model_train_window_days": 756,
        "model_val_window_days": 126,
        "forward_return_days": 5,
        "forward_return_threshold": 0.02,
        "model_ic_threshold": 0.02,
        "stock_universe": "csi300",
        "analysis_time": "17:00",
    }
    data.update(updates)
    return SystemParams(**data)


def test_relative_return_classification_uses_runtime_threshold():
    runtime = params(forward_return_threshold=0.08)
    assert classify_relative_return(0.05, runtime) == 1
    assert classify_relative_return(0.09, runtime) == 2
    assert classify_relative_return(-0.09, runtime) == 0


def test_validation_cutoff_uses_runtime_window():
    dates = list(range(40))
    assert validation_cutoff(dates, params(model_val_window_days=21)) == 19


def test_cleanup_uses_runtime_retention_values():
    runtime = params(data_retention_days=45, alert_retention_days=120)
    assert retention_days_by_table(runtime) == {
        "alerts": 120,
        "notification_logs": 45,
        "market_data": 45,
        "audit_logs": 45,
    }
```

Add the snapshot assertion to the existing setup test file so it can use its local fakes without cross-test imports:

```python
# backend/tests/test_setup_pipeline.py — replace FakeModel and add the test below
class FakeModel:
    def __init__(self, activation_error=None):
        self.calls = []
        self.param_calls = []
        self.runtime_params = object()
        self.activation_error = activation_error

    async def load_params(self):
        self.calls.append("load_params")
        return self.runtime_params

    async def train(self, params):
        self.param_calls.append(("training", params))
        self.calls.append("training")
        return {"version": "model_v1", "ic": 0.05, "val_accuracy": 0.6}

    async def activate(self, version, params):
        self.param_calls.append(("activation", params))
        self.calls.append(f"activation:{version}")
        if self.activation_error:
            raise ValueError(self.activation_error)


@pytest.mark.asyncio
async def test_setup_pipeline_reuses_one_model_snapshot():
    model = FakeModel()
    pipeline = SetupPipeline(FakeStore(), FakeDataSync(), model, FakeAnalysis())

    await pipeline.start(wait=True)

    assert model.param_calls == [
        ("training", model.runtime_params),
        ("activation", model.runtime_params),
    ]
```

Update the existing order assertion to include the one new setup call:

```python
assert model.calls == ["load_params", "training", "activation:model_v1"]
```

- [ ] **Step 2: Run tests and verify missing helpers/signature failures**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests/test_model_runtime_params.py tests/test_setup_pipeline.py -q'`

Expected: FAIL because the helpers and parameterized setup model interface do not exist.

- [ ] **Step 3: Extract parameter-driven model helpers and thread the snapshot through training**

```python
# backend/app/services/ml_model.py
from app.schemas.settings import SystemParams


def classify_relative_return(relative_return: float, params: SystemParams) -> int:
    if relative_return > params.forward_return_threshold:
        return 2
    if relative_return < -params.forward_return_threshold:
        return 0
    return 1


def validation_cutoff(dates: list, params: SystemParams):
    if len(dates) > params.model_val_window_days:
        return dates[-params.model_val_window_days]
    return dates[len(dates) // 2]
```

Change `generate_labels()` to require `params` and call `classify_relative_return()` for indexed and fallback returns. Change `train(params=None)` to load `load_runtime_system_params()` once when absent, use `params.model_train_window_days`, `params.model_val_window_days`, and pass the same object to `generate_labels()`. Rename the nested LightGBM dictionary from `params` to `lgb_params` so it cannot be confused with the runtime snapshot. Keep `get_settings().MODEL_DIR` only for the non-editable model path. Change `activate_model(..., params=None)` to load `get_system_params(db)` when absent and compare IC against `params.model_ic_threshold`.

Update cleanup to consume the same typed object at the start of each run:

```python
# backend/app/services/cleanup_service.py
from app.schemas.settings import SystemParams


def retention_days_by_table(params: SystemParams) -> dict[str, int]:
    return {
        "alerts": params.alert_retention_days,
        "notification_logs": params.data_retention_days,
        "market_data": params.data_retention_days,
        "audit_logs": params.data_retention_days,
    }


# Inside run_cleanup(), after get_system_params(db)
retention = retention_days_by_table(params)
tables_config = [
    ("alerts", "app.models.alert", "Alert", retention["alerts"]),
    ("notification_logs", "app.models.notification_log", "NotificationLog", retention["notification_logs"]),
    ("market_data", "app.models.market_data", "MarketData", retention["market_data"]),
    ("audit_logs", "app.models.audit_log", "AuditLog", retention["audit_logs"]),
]
```

- [ ] **Step 4: Load snapshots in direct model APIs**

```python
# backend/app/api/v1/model.py
from app.services.settings_service import get_system_params

# training endpoint
runtime_params = await get_system_params(db)
result = await ml_model_service.train(runtime_params)

# activation endpoint
runtime_params = await get_system_params(db)
await ml_model_service.activate_model(db, version, runtime_params)
```

- [ ] **Step 5: Reuse one snapshot throughout setup training and activation**

```python
# backend/app/services/setup_pipeline.py
class ModelSetupAdapter:
    async def load_params(self):
        from app.services.settings_service import load_runtime_system_params
        return await load_runtime_system_params()

    async def train(self, params) -> dict:
        from app.services.ml_model import ml_model_service
        return await ml_model_service.train(params)

    async def activate(self, version: str, params) -> None:
        from app.services.ml_model import ml_model_service
        async with AsyncSessionLocal() as db:
            await ml_model_service.activate_model(db, version, params)
            await db.commit()


# At the start of SetupPipeline._run
runtime_params = await self.model_service.load_params()

# Training and activation closures
result = await self.model_service.train(runtime_params)
await self.model_service.activate(version, runtime_params)
```

Keep all existing setup order and failure-gate assertions; only adjust the expected call list for `load_params` as shown above.

- [ ] **Step 6: Run all model/setup tests**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests/test_model_runtime_params.py tests/test_setup_pipeline.py tests/test_setup_api.py -q'`

Expected: all tests PASS without importing or training a real LightGBM model.

- [ ] **Step 7: Commit Task 3**

```powershell
git add backend/app/services/ml_model.py backend/app/api/v1/model.py backend/app/services/setup_pipeline.py backend/app/services/cleanup_service.py backend/tests/test_setup_pipeline.py backend/tests/test_model_runtime_params.py
git commit -m "feat: apply runtime parameters to model operations"
```

---

### Task 4: Add Typed Frontend Settings API Contracts

**Files:**
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`
- Modify: `frontend/src/api/settings.ts`
- Test: `frontend/src/api/settings.test.ts`

**Interfaces:**
- Produces: `NotificationSettings`, `NotificationUpdate`, `SystemParams`, `ProfileSettings`, and `PasswordChange` TypeScript interfaces.
- Produces: `getNotifications`, `updateNotifications`, `testEmail`, `testWebhook`, typed parameter methods, `getProfile`, and corrected `changePassword`.

- [ ] **Step 1: Write request-contract tests**

```ts
// frontend/src/api/settings.test.ts
import { beforeEach, describe, expect, it, vi } from 'vitest'

import client from './client'
import { settingsApi } from './settings'

describe('settingsApi', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('sends password fields required by the backend', async () => {
    vi.spyOn(client, 'put').mockResolvedValue({ data: null } as never)

    await settingsApi.changePassword({
      old_password: 'oldpass1',
      new_password: 'newpass2',
      confirm_password: 'newpass2',
    })

    expect(client.put).toHaveBeenCalledWith('/api/v1/settings/password', {
      old_password: 'oldpass1',
      new_password: 'newpass2',
      confirm_password: 'newpass2',
    })
  })

  it('exposes notification save and test endpoints', async () => {
    vi.spyOn(client, 'put').mockResolvedValue({ data: { saved: true } } as never)
    vi.spyOn(client, 'post').mockResolvedValue({ data: { sent: true } } as never)
    const payload = {
      email_enabled: true,
      email_smtp_host: 'smtp.example.com',
      email_smtp_port: 465,
      email_sender: 'sender@example.com',
      email_password: '',
      email_use_ssl: true,
      email_recipient: 'alerts@example.com',
      webhook_enabled: false,
      webhook_url: '',
      webhook_secret: '',
      notify_levels: ['warning', 'error'],
    }

    await settingsApi.updateNotifications(payload)
    await settingsApi.testEmail()
    await settingsApi.testWebhook()

    expect(client.put).toHaveBeenCalledWith('/api/v1/settings/notifications', payload)
    expect(client.post).toHaveBeenCalledWith('/api/v1/settings/notifications/test-email')
    expect(client.post).toHaveBeenCalledWith('/api/v1/settings/notifications/test-webhook')
  })
})
```

Add a focused client-error test:

```ts
// frontend/src/api/client.test.ts
import { describe, expect, it } from 'vitest'
import { ApiError, apiErrorFromAxios } from './client'

describe('apiErrorFromAxios', () => {
  it('retains FastAPI field validation detail', () => {
    const detail = [{ loc: ['body', 'params', 'analysis_time'], msg: '分析时间必须为 HH:mm', type: 'value_error' }]
    const error = apiErrorFromAxios({
      message: 'Request failed with status code 422',
      response: { data: { detail } },
    } as never)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.detail).toEqual(detail)
  })
})
```

- [ ] **Step 2: Run API tests and verify missing methods/payload mismatch**

Run: `cd frontend && npm test -- --run src/api/settings.test.ts src/api/client.test.ts`

Expected: FAIL because notification methods are absent and `changePassword` accepts the old two-field shape.

- [ ] **Step 3: Implement typed DTOs and all client methods**

Preserve FastAPI validation detail while keeping the existing human-readable error behavior:

```ts
// frontend/src/api/client.ts
export interface ValidationIssue {
  loc: Array<string | number>
  msg: string
  type: string
}

export class ApiError extends Error {
  constructor(message: string, public readonly detail?: unknown) {
    super(message)
    this.name = 'ApiError'
  }
}

export function apiErrorFromAxios(error: AxiosError): ApiError {
  const body = error.response?.data as { message?: string; detail?: unknown } | undefined
  const message = body?.message || error.message || '网络错误'
  return new ApiError(message, body?.detail)
}

// In both the login/refresh rejection path and the final response-error branch,
// reject apiErrorFromAxios(error) instead of constructing a plain Error.
```

```ts
// frontend/src/api/settings.ts
import client from './client'
import type { ResponseBase } from '@/types/common'

export interface NotificationSettings {
  email_enabled: boolean
  email_smtp_host: string
  email_smtp_port: number
  email_sender: string
  has_email_password: boolean
  email_use_ssl: boolean
  email_recipient: string
  webhook_enabled: boolean
  webhook_url: string
  has_webhook_secret: boolean
  notify_levels: NotificationLevel[]
}

export type NotificationLevel = 'info' | 'warning' | 'error'

export type NotificationUpdate = Omit<
  NotificationSettings,
  'has_email_password' | 'has_webhook_secret'
> & { email_password: string; webhook_secret: string }

export interface SystemParams {
  data_retention_days: number
  alert_retention_days: number
  model_train_window_days: number
  model_val_window_days: number
  forward_return_days: number
  forward_return_threshold: number
  model_ic_threshold: number
  stock_universe: 'csi300'
  analysis_time: string
}

export interface ProfileSettings {
  username: string
  role: string
  is_active: boolean
  created_at: string | null
}

export interface PasswordChange {
  old_password: string
  new_password: string
  confirm_password: string
}

type ApiResult<T> = Promise<ResponseBase<T>>

export const settingsApi = {
  // client.ts unwraps AxiosResponse in its response interceptor, so expose that runtime shape.
  getNotifications: () => client.get<ResponseBase<NotificationSettings>>('/api/v1/settings/notifications') as unknown as ApiResult<NotificationSettings>,
  updateNotifications: (data: NotificationUpdate) => client.put<ResponseBase<{ saved: boolean }>>('/api/v1/settings/notifications', data) as unknown as ApiResult<{ saved: boolean }>,
  testEmail: () => client.post<ResponseBase<{ sent: boolean }>>('/api/v1/settings/notifications/test-email') as unknown as ApiResult<{ sent: boolean }>,
  testWebhook: () => client.post<ResponseBase<{ sent: boolean }>>('/api/v1/settings/notifications/test-webhook') as unknown as ApiResult<{ sent: boolean }>,
  getParams: () => client.get<ResponseBase<SystemParams>>('/api/v1/settings/params') as unknown as ApiResult<SystemParams>,
  updateParams: (params: SystemParams) => client.put<ResponseBase<SystemParams>>('/api/v1/settings/params', { params }) as unknown as ApiResult<SystemParams>,
  resetParams: () => client.post<ResponseBase<SystemParams>>('/api/v1/settings/params/reset') as unknown as ApiResult<SystemParams>,
  getProfile: () => client.get<ResponseBase<ProfileSettings>>('/api/v1/settings/profile') as unknown as ApiResult<ProfileSettings>,
  changePassword: (data: PasswordChange) => client.put<ResponseBase<null>>('/api/v1/settings/password', data) as unknown as ApiResult<null>,
}
```

- [ ] **Step 4: Run API tests and TypeScript build**

Run: `cd frontend && npm test -- --run src/api/settings.test.ts src/api/client.test.ts && npm run build`

Expected: API tests and production build PASS.

- [ ] **Step 5: Commit Task 4**

```powershell
git add frontend/src/api/client.ts frontend/src/api/client.test.ts frontend/src/api/settings.ts frontend/src/api/settings.test.ts
git commit -m "feat: type frontend settings API"
```

---

### Task 5: Build the Appearance Settings Card

**Files:**
- Create: `frontend/src/views/settings/AppearanceSettingsCard.vue`
- Test: `frontend/src/views/settings/AppearanceSettingsCard.test.ts`

**Interfaces:**
- Consumes: `useThemeStore()` with `theme`, `radius`, `colorMode`, `setTheme`, `setRadius`, and `setColorMode`.
- Produces: a self-contained card with stable test IDs `appearance-mode-*`, `appearance-color-*`, and `appearance-radius-*`.

- [ ] **Step 1: Write failing immediate-application tests**

```ts
// frontend/src/views/settings/AppearanceSettingsCard.test.ts
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useThemeStore } from '@/stores/theme'
import AppearanceSettingsCard from './AppearanceSettingsCard.vue'

describe('AppearanceSettingsCard', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('applies color mode immediately', async () => {
    const wrapper = mount(AppearanceSettingsCard)
    await wrapper.get('[data-testid="appearance-mode-dark"]').trigger('click')
    expect(useThemeStore().colorMode).toBe('dark')
    expect(localStorage.getItem('qp-color-mode')).toBe('dark')
  })

  it('applies theme color and radius immediately', async () => {
    const wrapper = mount(AppearanceSettingsCard)
    await wrapper.get('[data-testid="appearance-color-blue"]').trigger('click')
    await wrapper.get('[data-testid="appearance-radius-comfortable"]').trigger('click')
    const store = useThemeStore()
    expect(store.theme).toBe('blue')
    expect(store.radius).toBe(0.75)
  })
})
```

- [ ] **Step 2: Run the card test and verify the missing-component failure**

Run: `cd frontend && npm test -- --run src/views/settings/AppearanceSettingsCard.test.ts`

Expected: FAIL because `AppearanceSettingsCard.vue` does not exist.

- [ ] **Step 3: Implement the complete appearance card**

```vue
<!-- frontend/src/views/settings/AppearanceSettingsCard.vue -->
<script setup lang="ts">
import { Monitor, Moon, Palette, Sun } from 'lucide-vue-next'
import { useThemeStore, type ThemeColor } from '@/stores/theme'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const themeStore = useThemeStore()
const modes = [
  { value: 'light' as const, label: '亮色', icon: Sun },
  { value: 'dark' as const, label: '暗色', icon: Moon },
  { value: 'system' as const, label: '跟随系统', icon: Monitor },
]
const colors: Array<{ value: ThemeColor; label: string; swatch: string }> = [
  { value: 'zinc', label: '中性', swatch: 'bg-zinc-500' },
  { value: 'red', label: '红色', swatch: 'bg-red-500' },
  { value: 'rose', label: '玫红', swatch: 'bg-rose-500' },
  { value: 'orange', label: '橙色', swatch: 'bg-orange-500' },
  { value: 'green', label: '绿色', swatch: 'bg-green-500' },
  { value: 'blue', label: '蓝色', swatch: 'bg-blue-500' },
  { value: 'yellow', label: '黄色', swatch: 'bg-yellow-500' },
  { value: 'violet', label: '紫色', swatch: 'bg-violet-500' },
]
const radii = [
  { value: 0.375, key: 'compact', label: '紧凑' },
  { value: 0.625, key: 'default', label: '默认' },
  { value: 0.75, key: 'comfortable', label: '柔和' },
]
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2"><Palette class="size-4" />外观偏好</CardTitle>
      <CardDescription>仅保存在当前浏览器，修改后立即生效。</CardDescription>
    </CardHeader>
    <CardContent class="space-y-6">
      <section class="space-y-3">
        <p class="text-sm font-medium">显示模式</p>
        <div class="grid gap-2 sm:grid-cols-3">
          <Button v-for="mode in modes" :key="mode.value" :data-testid="`appearance-mode-${mode.value}`" :variant="themeStore.colorMode === mode.value ? 'default' : 'outline'" @click="themeStore.setColorMode(mode.value)">
            <component :is="mode.icon" />{{ mode.label }}
          </Button>
        </div>
      </section>
      <section class="space-y-3">
        <p class="text-sm font-medium">主题色</p>
        <div class="flex flex-wrap gap-2">
          <Button v-for="color in colors" :key="color.value" :data-testid="`appearance-color-${color.value}`" :variant="themeStore.theme === color.value ? 'secondary' : 'ghost'" @click="themeStore.setTheme(color.value)">
            <span :class="['size-3 rounded-full', color.swatch]" />{{ color.label }}
          </Button>
        </div>
      </section>
      <section class="space-y-3">
        <p class="text-sm font-medium">圆角密度</p>
        <div class="flex flex-wrap gap-2">
          <Button v-for="item in radii" :key="item.key" :data-testid="`appearance-radius-${item.key}`" :variant="themeStore.radius === item.value ? 'default' : 'outline'" @click="themeStore.setRadius(item.value)">{{ item.label }}</Button>
        </div>
      </section>
    </CardContent>
  </Card>
</template>
```

- [ ] **Step 4: Run the card tests**

Run: `cd frontend && npm test -- --run src/views/settings/AppearanceSettingsCard.test.ts`

Expected: 2 tests PASS.

- [ ] **Step 5: Commit Task 5**

```powershell
git add frontend/src/views/settings/AppearanceSettingsCard.vue frontend/src/views/settings/AppearanceSettingsCard.test.ts
git commit -m "feat: add appearance settings card"
```

---

### Task 6: Build the Notification Settings Card

**Files:**
- Create: `frontend/src/views/settings/NotificationSettingsCard.vue`
- Test: `frontend/src/views/settings/NotificationSettingsCard.test.ts`

**Interfaces:**
- Consumes: Task 4 notification interfaces and methods.
- Produces: one card that owns load, retry, dirty, save, test-email, and test-Webhook state.
- Stable test IDs: `notification-save`, `notification-test-email`, `notification-test-webhook`, `email-password-configured`, and `webhook-secret-configured`.

- [ ] **Step 1: Write failing secret and dirty-state tests**

```ts
// frontend/src/views/settings/NotificationSettingsCard.test.ts
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { settingsApi } from '@/api/settings'
import NotificationSettingsCard from './NotificationSettingsCard.vue'

const saved = {
  email_enabled: true,
  email_smtp_host: 'smtp.example.com',
  email_smtp_port: 465,
  email_sender: 'sender@example.com',
  has_email_password: true,
  email_use_ssl: true,
  email_recipient: 'alerts@example.com',
  webhook_enabled: false,
  webhook_url: '',
  has_webhook_secret: true,
  notify_levels: ['warning', 'error'],
}

describe('NotificationSettingsCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(settingsApi, 'getNotifications').mockResolvedValue({ data: saved } as never)
  })

  it('shows configured-secret status without filling plaintext inputs', async () => {
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    expect(wrapper.get('[data-testid="email-password-configured"]').text()).toContain('已配置')
    expect((wrapper.get('#email-password').element as HTMLInputElement).value).toBe('')
  })

  it('preserves secrets by submitting blank replacement fields', async () => {
    const update = vi.spyOn(settingsApi, 'updateNotifications').mockResolvedValue({ data: { saved: true } } as never)
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    await wrapper.get('#email-recipient').setValue('new@example.com')
    await wrapper.get('[data-testid="notification-save"]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(expect.objectContaining({ email_password: '', webhook_secret: '' }))
  })

  it('disables test email while the form is dirty', async () => {
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    await wrapper.get('#email-recipient').setValue('dirty@example.com')
    expect(wrapper.get('[data-testid="notification-test-email"]').attributes('disabled')).toBeDefined()
  })
})
```

- [ ] **Step 2: Run the tests and verify the missing-component failure**

Run: `cd frontend && npm test -- --run src/views/settings/NotificationSettingsCard.test.ts`

Expected: FAIL because the card does not exist.

- [ ] **Step 3: Implement notification state and actions**

```ts
// Core script state inside NotificationSettingsCard.vue
const loading = ref(true)
const saving = ref(false)
const testing = ref<'email' | 'webhook' | null>(null)
const loadError = ref('')
const form = reactive<NotificationUpdate>({
  email_enabled: false,
  email_smtp_host: '',
  email_smtp_port: 465,
  email_sender: '',
  email_password: '',
  email_use_ssl: true,
  email_recipient: '',
  webhook_enabled: false,
  webhook_url: '',
  webhook_secret: '',
  notify_levels: ['warning', 'error'],
})
const notificationLevels: NotificationLevel[] = ['info', 'warning', 'error']
const savedBaseline = ref('')
const hasEmailPassword = ref(false)
const hasWebhookSecret = ref(false)
const serialized = computed(() => JSON.stringify(form))
const dirty = computed(() => serialized.value !== savedBaseline.value)
const emailValid = computed(() => !form.email_enabled || (
  !!form.email_smtp_host && !!form.email_sender && !!form.email_recipient
  && form.email_smtp_port >= 1 && form.email_smtp_port <= 65535
  && (hasEmailPassword.value || !!form.email_password)
))
const webhookValid = computed(() => !form.webhook_enabled || (
  /^https?:\/\//.test(form.webhook_url) && (hasWebhookSecret.value || !!form.webhook_secret)
))
const valid = computed(() => emailValid.value && webhookValid.value && form.notify_levels.length > 0)

function toggleLevel(level: NotificationLevel, checked: boolean) {
  form.notify_levels = checked
    ? [...new Set([...form.notify_levels, level])]
    : form.notify_levels.filter(item => item !== level)
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await settingsApi.getNotifications()
    const data = response.data
    Object.assign(form, {
      email_enabled: data.email_enabled,
      email_smtp_host: data.email_smtp_host,
      email_smtp_port: data.email_smtp_port,
      email_sender: data.email_sender,
      email_password: '',
      email_use_ssl: data.email_use_ssl,
      email_recipient: data.email_recipient,
      webhook_enabled: data.webhook_enabled,
      webhook_url: data.webhook_url,
      webhook_secret: '',
      notify_levels: [...data.notify_levels],
    })
    hasEmailPassword.value = data.has_email_password
    hasWebhookSecret.value = data.has_webhook_secret
    savedBaseline.value = serialized.value
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '通知配置加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!dirty.value || !valid.value) return
  saving.value = true
  try {
    await settingsApi.updateNotifications({ ...form })
    if (form.email_password) hasEmailPassword.value = true
    if (form.webhook_secret) hasWebhookSecret.value = true
    form.email_password = ''
    form.webhook_secret = ''
    savedBaseline.value = serialized.value
    toast.success('通知配置已保存')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '通知配置保存失败')
  } finally {
    saving.value = false
  }
}

async function sendTest(channel: 'email' | 'webhook') {
  if (dirty.value) return
  testing.value = channel
  try {
    const response = channel === 'email' ? await settingsApi.testEmail() : await settingsApi.testWebhook()
    response.data.sent ? toast.success('测试通知已发送') : toast.error('测试通知发送失败')
  } finally {
    testing.value = null
  }
}

onMounted(load)
```

Use two bordered subsections and these exact bindings. Import `Card`, `CardContent`, `CardDescription`, `CardFooter`, `CardHeader`, `CardTitle`, `Button`, `Input`, `Label`, `Switch`, `Checkbox`, and `Badge` from the existing UI component barrels:

```vue
<template>
  <Card>
    <CardHeader>
      <CardTitle>通知配置</CardTitle>
      <CardDescription>配置邮件、Webhook 与告警等级。</CardDescription>
    </CardHeader>
    <CardContent v-if="loading">正在加载通知配置…</CardContent>
    <CardContent v-else-if="loadError" class="space-y-3">
      <p class="text-sm text-destructive">{{ loadError }}</p>
      <Button variant="outline" @click="load">重试</Button>
    </CardContent>
    <CardContent v-else class="space-y-5">
      <section class="space-y-4 rounded-lg border p-4">
        <div class="flex items-center justify-between"><Label for="email-enabled">邮件通知</Label><Switch id="email-enabled" v-model="form.email_enabled" /></div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-2"><Label for="email-host">SMTP 主机</Label><Input id="email-host" v-model="form.email_smtp_host" /></div>
          <div class="space-y-2"><Label for="email-port">端口</Label><Input id="email-port" v-model.number="form.email_smtp_port" type="number" min="1" max="65535" /></div>
          <div class="space-y-2"><Label for="email-sender">发件人</Label><Input id="email-sender" v-model="form.email_sender" type="email" /></div>
          <div class="space-y-2">
            <div class="flex items-center gap-2"><Label for="email-password">SMTP 密码</Label><Badge v-if="hasEmailPassword" data-testid="email-password-configured" variant="secondary">已配置</Badge></div>
            <Input id="email-password" v-model="form.email_password" type="password" placeholder="留空则保留原密码" />
          </div>
          <div class="space-y-2"><Label for="email-recipient">收件人</Label><Input id="email-recipient" v-model="form.email_recipient" type="email" /></div>
          <div class="flex items-center justify-between"><Label for="email-ssl">SSL</Label><Switch id="email-ssl" v-model="form.email_use_ssl" /></div>
        </div>
        <p v-if="form.email_enabled && !emailValid" class="text-sm text-destructive">请完整填写邮件服务器、发件人、收件人和凭据。</p>
        <Button data-testid="notification-test-email" variant="outline" :disabled="dirty || !valid || !form.email_enabled || testing !== null" @click="sendTest('email')">测试邮件</Button>
      </section>
      <section class="space-y-4 rounded-lg border p-4">
        <div class="flex items-center justify-between"><Label for="webhook-enabled">Webhook</Label><Switch id="webhook-enabled" v-model="form.webhook_enabled" /></div>
        <div class="space-y-2"><Label for="webhook-url">地址</Label><Input id="webhook-url" v-model="form.webhook_url" type="url" /></div>
        <div class="space-y-2">
          <div class="flex items-center gap-2"><Label for="webhook-secret">签名密钥</Label><Badge v-if="hasWebhookSecret" data-testid="webhook-secret-configured" variant="secondary">已配置</Badge></div>
          <Input id="webhook-secret" v-model="form.webhook_secret" type="password" placeholder="留空则保留原密钥" />
        </div>
        <p v-if="form.webhook_enabled && !webhookValid" class="text-sm text-destructive">请输入有效的 HTTP(S) 地址和签名密钥。</p>
        <Button data-testid="notification-test-webhook" variant="outline" :disabled="dirty || !valid || !form.webhook_enabled || testing !== null" @click="sendTest('webhook')">测试 Webhook</Button>
      </section>
      <fieldset class="space-y-2">
        <legend class="text-sm font-medium">通知等级</legend>
        <label v-for="level in notificationLevels" :key="level" class="flex items-center gap-2 text-sm">
          <Checkbox :model-value="form.notify_levels.includes(level)" @update:model-value="toggleLevel(level, $event === true)" />{{ level }}
        </label>
      </fieldset>
    </CardContent>
    <CardFooter v-if="!loading && !loadError" class="justify-end">
      <Button data-testid="notification-save" :disabled="!dirty || !valid || saving" @click="save">保存通知配置</Button>
    </CardFooter>
  </Card>
</template>
```

Add `toggleLevel(level, checked)` to replace `notify_levels` with a new array, so checkbox changes participate in the serialized dirty check.

- [ ] **Step 4: Run notification tests**

Run: `cd frontend && npm test -- --run src/views/settings/NotificationSettingsCard.test.ts`

Expected: 3 tests PASS.

- [ ] **Step 5: Commit Task 6**

```powershell
git add frontend/src/views/settings/NotificationSettingsCard.vue frontend/src/views/settings/NotificationSettingsCard.test.ts
git commit -m "feat: add notification settings card"
```

---

### Task 7: Build the Administrator System Parameters Card

**Files:**
- Create: `frontend/src/views/settings/SystemParamsCard.vue`
- Test: `frontend/src/views/settings/SystemParamsCard.test.ts`

**Interfaces:**
- Consumes: Task 4 `SystemParams` and parameter API methods.
- Produces: a self-contained administrator form with stable test IDs `system-params-save`, `system-params-reset`, and `system-params-reset-confirm`.

- [ ] **Step 1: Write failing load/save/reset tests**

```ts
// frontend/src/views/settings/SystemParamsCard.test.ts
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { settingsApi, type SystemParams } from '@/api/settings'
import SystemParamsCard from './SystemParamsCard.vue'

const defaults: SystemParams = {
  data_retention_days: 90,
  alert_retention_days: 90,
  model_train_window_days: 756,
  model_val_window_days: 126,
  forward_return_days: 5,
  forward_return_threshold: 0.02,
  model_ic_threshold: 0.02,
  stock_universe: 'csi300',
  analysis_time: '17:00',
}

describe('SystemParamsCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(settingsApi, 'getParams').mockResolvedValue({ data: defaults } as never)
  })

  it('saves a validated complete parameter object', async () => {
    const update = vi.spyOn(settingsApi, 'updateParams').mockResolvedValue({ data: { ...defaults, analysis_time: '18:15' } } as never)
    const wrapper = mount(SystemParamsCard, { global: { stubs: { Teleport: true } } })
    await flushPromises()
    await wrapper.get('#analysis-time').setValue('18:15')
    await wrapper.get('[data-testid="system-params-save"]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(expect.objectContaining({ analysis_time: '18:15', stock_universe: 'csi300' }))
  })

  it('prevents validation windows from matching the training window', async () => {
    const wrapper = mount(SystemParamsCard, { global: { stubs: { Teleport: true } } })
    await flushPromises()
    await wrapper.get('#model-val-window').setValue('756')
    expect(wrapper.text()).toContain('验证窗口必须短于训练窗口')
    expect(wrapper.get('[data-testid="system-params-save"]').attributes('disabled')).toBeDefined()
  })

  it('maps backend validation detail to the matching field', async () => {
    vi.spyOn(settingsApi, 'updateParams').mockRejectedValue(new ApiError('参数校验失败', [
      { loc: ['body', 'params', 'analysis_time'], msg: '分析时间不可用', type: 'value_error' },
    ]))
    const wrapper = mount(SystemParamsCard, { global: { stubs: { Teleport: true } } })
    await flushPromises()
    await wrapper.get('#analysis-time').setValue('18:15')
    await wrapper.get('[data-testid="system-params-save"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('分析时间不可用')
  })

  it('replaces the form with the server reset response', async () => {
    vi.spyOn(settingsApi, 'resetParams').mockResolvedValue({ data: defaults } as never)
    const wrapper = mount(SystemParamsCard, { global: { stubs: { Teleport: true } } })
    await flushPromises()
    await wrapper.get('[data-testid="system-params-reset"]').trigger('click')
    await wrapper.get('[data-testid="system-params-reset-confirm"]').trigger('click')
    await flushPromises()
    expect((wrapper.get('#analysis-time').element as HTMLInputElement).value).toBe('17:00')
  })
})
```

- [ ] **Step 2: Run tests and verify the missing-component failure**

Run: `cd frontend && npm test -- --run src/views/settings/SystemParamsCard.test.ts`

Expected: FAIL because the card does not exist.

- [ ] **Step 3: Implement typed form validation and actions**

Import `ApiError` and `ValidationIssue` from `@/api/client`, `SystemParams`/`settingsApi` from `@/api/settings`, and `watch` with the other Vue reactivity helpers.

```ts
// Core script state inside SystemParamsCard.vue
const loading = ref(true)
const saving = ref(false)
const resetting = ref(false)
const loadError = ref('')
const form = reactive<SystemParams>({
  data_retention_days: 90,
  alert_retention_days: 90,
  model_train_window_days: 756,
  model_val_window_days: 126,
  forward_return_days: 5,
  forward_return_threshold: 0.02,
  model_ic_threshold: 0.02,
  stock_universe: 'csi300',
  analysis_time: '17:00',
})
const savedBaseline = ref('')
const dirty = computed(() => JSON.stringify(form) !== savedBaseline.value)
const serverErrors = reactive<Partial<Record<keyof SystemParams, string>>>({})
const clientErrors = computed(() => ({
  data_retention_days: form.data_retention_days < 7 || form.data_retention_days > 3650 ? '请输入 7–3650 天' : '',
  alert_retention_days: form.alert_retention_days < 7 || form.alert_retention_days > 3650 ? '请输入 7–3650 天' : '',
  model_train_window_days: form.model_train_window_days < 252 || form.model_train_window_days > 2520 ? '请输入 252–2520 个交易日' : '',
  model_val_window_days: form.model_val_window_days >= form.model_train_window_days ? '验证窗口必须短于训练窗口' : (form.model_val_window_days < 21 || form.model_val_window_days > 504 ? '请输入 21–504 个交易日' : ''),
  forward_return_days: form.forward_return_days < 1 || form.forward_return_days > 30 ? '请输入 1–30 个交易日' : '',
  forward_return_threshold: form.forward_return_threshold <= 0 || form.forward_return_threshold > 1 ? '请输入大于 0 且不超过 1 的数值' : '',
  model_ic_threshold: form.model_ic_threshold < 0 || form.model_ic_threshold > 1 ? '请输入 0–1 的数值' : '',
  analysis_time: /^([01]\d|2[0-3]):[0-5]\d$/.test(form.analysis_time) ? '' : '请输入 HH:mm 时间',
}))
const errors = computed(() => ({ ...clientErrors.value, ...serverErrors }))
const valid = computed(() => Object.values(errors.value).every(value => !value))

watch(form, () => {
  for (const key of Object.keys(serverErrors) as Array<keyof SystemParams>) delete serverErrors[key]
}, { deep: true })

function applyServerValidation(error: unknown) {
  if (!(error instanceof ApiError) || !Array.isArray(error.detail)) return
  for (const issue of error.detail as ValidationIssue[]) {
    const field = issue.loc.at(-1)
    if (typeof field === 'string' && field in form) {
      serverErrors[field as keyof SystemParams] = issue.msg
    }
  }
}

function applyServerParams(params: SystemParams) {
  Object.assign(form, params)
  savedBaseline.value = JSON.stringify(form)
}

async function load() {
  loading.value = true
  loadError.value = ''
  try { applyServerParams((await settingsApi.getParams()).data) }
  catch (error) { loadError.value = error instanceof Error ? error.message : '系统参数加载失败' }
  finally { loading.value = false }
}

async function save() {
  if (!dirty.value || !valid.value) return
  saving.value = true
  try {
    applyServerParams((await settingsApi.updateParams({ ...form })).data)
    toast.success('系统参数已保存，将在后续任务中生效')
  } catch (error) {
    applyServerValidation(error)
    toast.error(error instanceof Error ? error.message : '系统参数保存失败')
  } finally { saving.value = false }
}

async function reset() {
  resetting.value = true
  try {
    applyServerParams((await settingsApi.resetParams()).data)
    toast.success('系统参数已恢复默认值')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '恢复默认参数失败')
  } finally { resetting.value = false }
}

onMounted(load)
```

Build grouped fieldsets for retention, model windows, prediction thresholds, and schedule. Every numeric `Input` must use `v-model.number` with the matching `min`, `max`, and `step`; the validation-window input is exactly `id="model-val-window"`, and the time input is exactly `id="analysis-time"`. Render `errors[field]` directly below its input. Display stock universe through a disabled input with value “沪深 300”.

```vue
<Card>
  <CardHeader><CardTitle>系统参数</CardTitle><CardDescription>保存后应用于后续分析或清理任务，不改变正在运行的任务。</CardDescription></CardHeader>
  <CardContent v-if="loading">正在加载系统参数…</CardContent>
  <CardContent v-else-if="loadError" class="space-y-3"><p class="text-sm text-destructive">{{ loadError }}</p><Button variant="outline" @click="load">重试</Button></CardContent>
  <CardContent v-else class="grid gap-6 lg:grid-cols-2">
    <fieldset class="space-y-4 rounded-lg border p-4">
      <legend class="px-1 text-sm font-medium">数据保留</legend>
      <div class="space-y-2"><Label for="data-retention">行情与日志（天）</Label><Input id="data-retention" v-model.number="form.data_retention_days" type="number" min="7" max="3650" step="1" /><p v-if="errors.data_retention_days" class="text-sm text-destructive">{{ errors.data_retention_days }}</p></div>
      <div class="space-y-2"><Label for="alert-retention">告警（天）</Label><Input id="alert-retention" v-model.number="form.alert_retention_days" type="number" min="7" max="3650" step="1" /><p v-if="errors.alert_retention_days" class="text-sm text-destructive">{{ errors.alert_retention_days }}</p></div>
    </fieldset>
    <fieldset class="space-y-4 rounded-lg border p-4">
      <legend class="px-1 text-sm font-medium">模型窗口</legend>
      <div class="space-y-2"><Label for="model-train-window">训练窗口（交易日）</Label><Input id="model-train-window" v-model.number="form.model_train_window_days" type="number" min="252" max="2520" step="1" /><p v-if="errors.model_train_window_days" class="text-sm text-destructive">{{ errors.model_train_window_days }}</p></div>
      <div class="space-y-2"><Label for="model-val-window">验证窗口（交易日）</Label><Input id="model-val-window" v-model.number="form.model_val_window_days" type="number" min="21" max="504" step="1" /><p v-if="errors.model_val_window_days" class="text-sm text-destructive">{{ errors.model_val_window_days }}</p></div>
    </fieldset>
    <fieldset class="space-y-4 rounded-lg border p-4">
      <legend class="px-1 text-sm font-medium">预测阈值</legend>
      <div class="space-y-2"><Label for="forward-return-days">前瞻窗口（交易日）</Label><Input id="forward-return-days" v-model.number="form.forward_return_days" type="number" min="1" max="30" step="1" /><p v-if="errors.forward_return_days" class="text-sm text-destructive">{{ errors.forward_return_days }}</p></div>
      <div class="space-y-2"><Label for="forward-return-threshold">收益阈值</Label><Input id="forward-return-threshold" v-model.number="form.forward_return_threshold" type="number" min="0.0001" max="1" step="0.001" /><p v-if="errors.forward_return_threshold" class="text-sm text-destructive">{{ errors.forward_return_threshold }}</p></div>
      <div class="space-y-2"><Label for="model-ic-threshold">IC 阈值</Label><Input id="model-ic-threshold" v-model.number="form.model_ic_threshold" type="number" min="0" max="1" step="0.001" /><p v-if="errors.model_ic_threshold" class="text-sm text-destructive">{{ errors.model_ic_threshold }}</p></div>
    </fieldset>
    <fieldset class="space-y-4 rounded-lg border p-4">
      <legend class="px-1 text-sm font-medium">范围与计划</legend>
      <div class="space-y-2"><Label for="stock-universe">股票池</Label><Input id="stock-universe" model-value="沪深 300" disabled /></div>
      <div class="space-y-2"><Label for="analysis-time">每日分析时间</Label><Input id="analysis-time" v-model="form.analysis_time" type="time" /><p v-if="errors.analysis_time" class="text-sm text-destructive">{{ errors.analysis_time }}</p></div>
    </fieldset>
  </CardContent>
  <CardFooter v-if="!loading && !loadError" class="justify-end gap-2">
    <AlertDialog>
      <AlertDialogTrigger as-child><Button data-testid="system-params-reset" variant="outline">恢复默认值</Button></AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader><AlertDialogTitle>恢复默认系统参数？</AlertDialogTitle><AlertDialogDescription>数据库中的参数覆盖将被移除，后续任务使用启动默认值。</AlertDialogDescription></AlertDialogHeader>
        <AlertDialogFooter><AlertDialogCancel>取消</AlertDialogCancel><AlertDialogAction data-testid="system-params-reset-confirm" :disabled="resetting" @click="reset">确认恢复</AlertDialogAction></AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    <Button data-testid="system-params-save" :disabled="!dirty || !valid || saving" @click="save">保存系统参数</Button>
  </CardFooter>
</Card>
```

Like the notification card, render loading, local `loadError`, and retry states inside the card so a failed system request does not replace the page.

- [ ] **Step 4: Run parameter-card tests**

Run: `cd frontend && npm test -- --run src/views/settings/SystemParamsCard.test.ts`

Expected: 4 tests PASS.

- [ ] **Step 5: Commit Task 7**

```powershell
git add frontend/src/views/settings/SystemParamsCard.vue frontend/src/views/settings/SystemParamsCard.test.ts
git commit -m "feat: add system parameter settings card"
```

---

### Task 8: Build the Account Security Card

**Files:**
- Create: `frontend/src/views/settings/AccountSecurityCard.vue`
- Test: `frontend/src/views/settings/AccountSecurityCard.test.ts`

**Interfaces:**
- Consumes: Task 4 profile and password methods, `useAuthStore().logout()`, and `useRouter().push()`.
- Produces: profile display plus stable test IDs `password-submit` and `profile-retry`.

- [ ] **Step 1: Write failing profile, validation, and logout tests**

```ts
// frontend/src/views/settings/AccountSecurityCard.test.ts
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { settingsApi } from '@/api/settings'
import { useAuthStore } from '@/stores/auth'
import AccountSecurityCard from './AccountSecurityCard.vue'

const { push } = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

describe('AccountSecurityCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    push.mockReset()
    setActivePinia(createPinia())
    vi.spyOn(settingsApi, 'getProfile').mockResolvedValue({ data: {
      username: 'alice', role: 'admin', is_active: true, created_at: '2026-07-18T00:00:00Z',
    } } as never)
  })

  it('renders profile data', async () => {
    const wrapper = mount(AccountSecurityCard)
    await flushPromises()
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('管理员')
  })

  it('rejects mismatched new passwords before calling the API', async () => {
    const change = vi.spyOn(settingsApi, 'changePassword')
    const wrapper = mount(AccountSecurityCard)
    await flushPromises()
    await wrapper.get('#old-password').setValue('oldpass1')
    await wrapper.get('#new-password').setValue('newpass2')
    await wrapper.get('#confirm-password').setValue('different3')
    await wrapper.get('[data-testid="password-submit"]').trigger('click')
    expect(change).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('两次密码不一致')
  })

  it('logs out and redirects after a successful password change', async () => {
    vi.spyOn(settingsApi, 'changePassword').mockResolvedValue({ data: null } as never)
    const auth = useAuthStore()
    const logout = vi.spyOn(auth, 'logout')
    const wrapper = mount(AccountSecurityCard)
    await flushPromises()
    await wrapper.get('#old-password').setValue('oldpass1')
    await wrapper.get('#new-password').setValue('newpass2')
    await wrapper.get('#confirm-password').setValue('newpass2')
    await wrapper.get('[data-testid="password-submit"]').trigger('click')
    await flushPromises()
    expect(logout).toHaveBeenCalledOnce()
    expect(push).toHaveBeenCalledWith('/login')
  })
})
```

- [ ] **Step 2: Run tests and verify the missing-component failure**

Run: `cd frontend && npm test -- --run src/views/settings/AccountSecurityCard.test.ts`

Expected: FAIL because the card does not exist.

- [ ] **Step 3: Implement profile loading and password change**

```ts
// Core script state inside AccountSecurityCard.vue
const router = useRouter()
const authStore = useAuthStore()
const profile = ref<ProfileSettings | null>(null)
const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)
const form = reactive<PasswordChange>({ old_password: '', new_password: '', confirm_password: '' })
const passwordError = computed(() => {
  if (!form.old_password && !form.new_password && !form.confirm_password) return ''
  if (form.old_password.length < 8) return '当前密码至少 8 位'
  if (form.new_password.length < 8 || form.new_password.length > 64) return '新密码需为 8–64 位'
  if (!/[A-Za-z]/.test(form.new_password) || !/\d/.test(form.new_password)) return '新密码需包含字母和数字'
  if (form.new_password !== form.confirm_password) return '两次密码不一致'
  return ''
})
const canSubmit = computed(() => !!form.old_password && !!form.new_password && !!form.confirm_password && !passwordError.value)

async function loadProfile() {
  loading.value = true
  loadError.value = ''
  try { profile.value = (await settingsApi.getProfile()).data }
  catch (error) { loadError.value = error instanceof Error ? error.message : '个人资料加载失败' }
  finally { loading.value = false }
}

async function submitPassword() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    await settingsApi.changePassword({ ...form })
    toast.success('密码已修改，请重新登录')
    authStore.logout()
    await router.push('/login')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '密码修改失败')
  } finally { submitting.value = false }
}

onMounted(loadProfile)
```

Build one card with a responsive two-column content area. The left side renders a definition list from `profile`: username, role (`管理员`/`用户`), state (`正常`/`停用`), and `dayjs(profile.created_at).format('YYYY-MM-DD HH:mm')` (or `—` when absent). On load failure, replace only this left section with the error and `<Button data-testid="profile-retry" @click="loadProfile">重试</Button>`.

The right side is a native `<form @submit.prevent="submitPassword">` with password inputs `old-password`, `new-password`, and `confirm-password`; print `passwordError` below them and use `<Button data-testid="password-submit" type="submit" :disabled="!canSubmit || submitting">修改密码</Button>`. Keep the form available even when profile loading fails.

```vue
<template>
  <Card>
    <CardHeader><CardTitle>账户安全</CardTitle><CardDescription>查看账户信息并修改登录密码。</CardDescription></CardHeader>
    <CardContent class="grid gap-8 lg:grid-cols-2">
      <section>
        <h3 class="mb-4 text-sm font-medium">个人资料</h3>
        <p v-if="loading" class="text-sm text-muted-foreground">正在加载个人资料…</p>
        <div v-else-if="loadError" class="space-y-3"><p class="text-sm text-destructive">{{ loadError }}</p><Button data-testid="profile-retry" variant="outline" @click="loadProfile">重试</Button></div>
        <dl v-else-if="profile" class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm">
          <dt class="text-muted-foreground">用户名</dt><dd>{{ profile.username }}</dd>
          <dt class="text-muted-foreground">角色</dt><dd>{{ profile.role === 'admin' ? '管理员' : '用户' }}</dd>
          <dt class="text-muted-foreground">状态</dt><dd>{{ profile.is_active ? '正常' : '停用' }}</dd>
          <dt class="text-muted-foreground">创建时间</dt><dd>{{ profile.created_at ? dayjs(profile.created_at).format('YYYY-MM-DD HH:mm') : '—' }}</dd>
        </dl>
      </section>
      <form class="space-y-4" @submit.prevent="submitPassword">
        <h3 class="text-sm font-medium">修改密码</h3>
        <div class="space-y-2"><Label for="old-password">当前密码</Label><Input id="old-password" v-model="form.old_password" type="password" autocomplete="current-password" /></div>
        <div class="space-y-2"><Label for="new-password">新密码</Label><Input id="new-password" v-model="form.new_password" type="password" autocomplete="new-password" /></div>
        <div class="space-y-2"><Label for="confirm-password">确认新密码</Label><Input id="confirm-password" v-model="form.confirm_password" type="password" autocomplete="new-password" /></div>
        <p v-if="passwordError" class="text-sm text-destructive">{{ passwordError }}</p>
        <Button data-testid="password-submit" type="submit" :disabled="!canSubmit || submitting">修改密码</Button>
      </form>
    </CardContent>
  </Card>
</template>
```

- [ ] **Step 4: Run account-card tests**

Run: `cd frontend && npm test -- --run src/views/settings/AccountSecurityCard.test.ts`

Expected: 3 tests PASS.

- [ ] **Step 5: Commit Task 8**

```powershell
git add frontend/src/views/settings/AccountSecurityCard.vue frontend/src/views/settings/AccountSecurityCard.test.ts
git commit -m "feat: add account security settings card"
```

---

### Task 9: Compose the Role-aware Settings Page and Verify End to End

**Files:**
- Modify: `frontend/src/views/settings/SettingsView.vue`
- Test: `frontend/src/views/settings/SettingsView.test.ts`

**Interfaces:**
- Consumes: Tasks 5–8 card components and `useAuthStore().role`.
- Produces: final `/settings` page with no placeholder text.

- [ ] **Step 1: Write failing role-aware composition tests**

```ts
// frontend/src/views/settings/SettingsView.test.ts
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import SettingsView from './SettingsView.vue'

const stubs = {
  BasicPage: { template: '<main><slot /></main>' },
  AppearanceSettingsCard: { template: '<div data-testid="appearance-card" />' },
  NotificationSettingsCard: { template: '<div data-testid="notification-card" />' },
  SystemParamsCard: { template: '<div data-testid="system-card" />' },
  AccountSecurityCard: { template: '<div data-testid="account-card" />' },
}

function mountPage(role: 'admin' | 'user') {
  const auth = useAuthStore()
  auth.user = { id: 'u1', username: 'alice', role, is_active: true, created_at: '' }
  return mount(SettingsView, { global: { stubs } })
}

describe('SettingsView', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows all four cards to administrators', () => {
    const wrapper = mountPage('admin')
    expect(wrapper.find('[data-testid="appearance-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="notification-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="system-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="account-card"]').exists()).toBe(true)
  })

  it('does not render system parameters for ordinary users', () => {
    const wrapper = mountPage('user')
    expect(wrapper.find('[data-testid="system-card"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="notification-card"]').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run the view test and verify it fails against the placeholder page**

Run: `cd frontend && npm test -- --run src/views/settings/SettingsView.test.ts`

Expected: FAIL because none of the new cards are composed.

- [ ] **Step 3: Replace the placeholder with role-aware composition**

```vue
<!-- frontend/src/views/settings/SettingsView.vue -->
<script setup lang="ts">
import { computed } from 'vue'
import { BasicPage } from '@/components/global-layout'
import { useAuthStore } from '@/stores/auth'
import AccountSecurityCard from './AccountSecurityCard.vue'
import AppearanceSettingsCard from './AppearanceSettingsCard.vue'
import NotificationSettingsCard from './NotificationSettingsCard.vue'
import SystemParamsCard from './SystemParamsCard.vue'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.role === 'admin')
</script>

<template>
  <BasicPage title="系统设置" description="管理外观、通知、分析参数与账户安全。">
    <div class="grid gap-6 xl:grid-cols-2">
      <AppearanceSettingsCard />
      <NotificationSettingsCard />
      <div v-if="isAdmin" class="xl:col-span-2"><SystemParamsCard /></div>
      <div class="xl:col-span-2"><AccountSecurityCard /></div>
    </div>
  </BasicPage>
</template>
```

- [ ] **Step 4: Run all frontend tests and the production build**

Run: `cd frontend && npm test -- --run && npm run test:login-copy && npm run test:layout && npm run build`

Expected: all Vitest files PASS, both verification scripts PASS, and Vite build exits 0. The existing large-chunk advisory may remain a warning.

- [ ] **Step 5: Run all backend tests and lint changed backend files**

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m pytest tests -q'`

Expected: all backend tests PASS.

Run from PowerShell: `wsl.exe bash -lc 'cd /mnt/c/Users/zhuan/quant/backend && venv/bin/python -m ruff check app/schemas/settings.py app/services/settings_service.py app/api/v1/settings.py app/services/analysis_pipeline.py app/services/ml_model.py app/api/v1/model.py app/services/setup_pipeline.py app/services/cleanup_service.py tests/test_settings_schema_service.py tests/test_settings_api.py tests/test_model_runtime_params.py'`

Expected: `All checks passed!`

- [ ] **Step 6: Verify authenticated browser behavior**

Start the application using the repository's documented startup path. In a local browser:

1. Sign in as an administrator and open `/settings`.
2. Confirm all four cards render with no “配置面板即将更新” text.
3. Change theme mode, color, and radius; reload and confirm browser-local persistence.
4. Save notification fields with blank secret replacements and confirm the UI still reports existing secrets.
5. Save a valid system parameter, reload, and confirm the server value remains.
6. Enter an invalid validation window and confirm inline rejection without a request.
7. Confirm reset requires the alert dialog and uses the returned defaults.
8. Confirm profile data renders and password mismatch is rejected locally.
9. Sign in as an ordinary user and confirm the system-parameter card is absent and no GET `/api/v1/settings/params` request occurs.
10. Inspect API responses and confirm no email password or Webhook secret plaintext is present.

Expected: each card works independently; failed actions show a local retry or toast without breaking other cards.

- [ ] **Step 7: Commit Task 9**

```powershell
git add frontend/src/views/settings/SettingsView.vue frontend/src/views/settings/SettingsView.test.ts
git commit -m "feat: complete the settings page"
```

- [ ] **Step 8: Record final status**

Run: `git status --short`

Expected: no output.

Summarize test counts, build result, browser verification, parameter runtime behavior, and the known Vite chunk-size warning in the handoff.
