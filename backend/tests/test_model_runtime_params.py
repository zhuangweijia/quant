from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.api.v1 import model as model_api
from app.schemas.settings import SystemParams
from app.services import cleanup_service
from app.services.cleanup_service import retention_days_by_table, run_cleanup
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


@pytest.mark.asyncio
async def test_scheduled_cleanup_loads_the_current_runtime_snapshot(monkeypatch):
    runtime = params(data_retention_days=45, alert_retention_days=120)

    class EmptyResult:
        def scalar(self):
            return 0

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def execute(self, _statement):
            return EmptyResult()

        async def rollback(self):
            return None

    monkeypatch.setattr("app.database.AsyncSessionLocal", FakeSession)
    load_params = AsyncMock(return_value=runtime)
    monkeypatch.setattr("app.services.settings_service.get_system_params", load_params)
    retention = Mock(wraps=retention_days_by_table)
    monkeypatch.setattr(cleanup_service, "retention_days_by_table", retention)

    await run_cleanup()

    load_params.assert_awaited_once()
    retention.assert_called_once_with(runtime)


@pytest.mark.asyncio
async def test_direct_training_api_passes_loaded_snapshot(monkeypatch):
    runtime = params(model_val_window_days=63)
    train = AsyncMock(return_value={"version": "v1", "ic": 0.05, "val_accuracy": 0.6})
    monkeypatch.setattr(
        "app.services.settings_service.get_system_params",
        AsyncMock(return_value=runtime),
    )
    monkeypatch.setattr("app.services.ml_model.ml_model_service.train", train)

    await model_api.trigger_training(
        user=SimpleNamespace(role="admin"),
        db=SimpleNamespace(),
    )

    train.assert_awaited_once_with(runtime)


@pytest.mark.asyncio
async def test_direct_activation_api_passes_loaded_snapshot(monkeypatch):
    runtime = params(model_ic_threshold=0.08)
    activate = AsyncMock()
    db = SimpleNamespace()
    monkeypatch.setattr(
        "app.services.settings_service.get_system_params",
        AsyncMock(return_value=runtime),
    )
    monkeypatch.setattr("app.services.ml_model.ml_model_service.activate_model", activate)

    await model_api.activate_model(
        version="v1",
        user=SimpleNamespace(role="admin"),
        db=db,
    )

    activate.assert_awaited_once_with(db, "v1", runtime)
