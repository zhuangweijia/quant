from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1 import settings as settings_api
from app.schemas.settings import (
    NotificationConfigRequest,
    ProfileResponse,
    SystemParams,
    SystemParamsRequest,
)
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


@pytest.mark.asyncio
async def test_profile_response_keeps_datetime_value():
    created_at = datetime(2026, 7, 18, tzinfo=UTC)

    response = await settings_api.get_profile(
        user=SimpleNamespace(
            username="alice",
            role="admin",
            is_active=True,
            created_at=created_at,
        ),
        db=SimpleNamespace(),
    )

    assert isinstance(response.data, ProfileResponse)
    assert response.data.created_at == created_at


def test_analysis_pipeline_parses_and_replaces_daily_schedule():
    pipeline = AnalysisPipeline()
    pipeline._started = True
    pipeline._scheduler.add_job = lambda *args, **kwargs: setattr(pipeline, "scheduled", kwargs)

    pipeline.reschedule("18:15")

    assert pipeline.scheduled["id"] == "analysis_pipeline_daily"
    assert str(pipeline.scheduled["trigger"]).startswith("cron[hour='18', minute='15'")
