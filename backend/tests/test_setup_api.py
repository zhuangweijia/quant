from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1 import analysis as analysis_api
from app.api.v1 import setup as setup_api


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSetupDB:
    def __init__(self, counts=None, latest_run=None, active_model=None, analysis_run=None):
        self.counts = iter(counts or [0, 0, 0, 0])
        self.results = iter([
            FakeScalarResult(latest_run),
            FakeScalarResult(active_model),
            FakeScalarResult(analysis_run),
        ])

    async def scalar(self, _query):
        return next(self.counts)

    async def execute(self, _query):
        return next(self.results)


class FakeAnalysisDB:
    def __init__(self, stock_count=300, bar_count=1000, active_model=None, running=None):
        self.counts = iter([stock_count, bar_count])
        self.results = iter([
            FakeScalarResult(active_model),
            FakeScalarResult(running),
        ])

    async def scalar(self, _query):
        return next(self.counts)

    async def execute(self, _query):
        return next(self.results)


@pytest.mark.asyncio
async def test_setup_status_empty_database_is_uninitialized():
    user = SimpleNamespace(role="admin")

    response = await setup_api.get_setup_status(user=user, db=FakeSetupDB())

    assert response.data.readiness == "uninitialized"
    assert response.data.counts.stocks == 0
    assert response.data.can_start is True
    assert response.data.can_run_analysis is False


@pytest.mark.asyncio
async def test_admin_can_start_setup(monkeypatch):
    start = AsyncMock(return_value="setup_123")
    monkeypatch.setattr(setup_api.setup_pipeline, "start", start)

    response = await setup_api.start_setup(user=SimpleNamespace(role="admin"))

    assert response.data.run_id == "setup_123"
    start.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_non_admin_cannot_start_setup():
    with pytest.raises(HTTPException) as exc_info:
        await setup_api.start_setup(user=SimpleNamespace(role="user"))

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_analysis_without_active_model_returns_409():
    db = FakeAnalysisDB(active_model=None)

    with pytest.raises(HTTPException) as exc_info:
        await analysis_api.trigger_analysis(
            user=SimpleNamespace(role="admin"),
            db=db,
        )

    assert exc_info.value.status_code == 409
    assert "激活模型" in exc_info.value.detail


@pytest.mark.asyncio
async def test_analysis_returns_existing_running_run():
    running = SimpleNamespace(run_id="run_existing")
    db = FakeAnalysisDB(active_model="model_v1", running=running)

    response = await analysis_api.trigger_analysis(
        user=SimpleNamespace(role="admin"),
        db=db,
    )

    assert response.data.run_id == "run_existing"
