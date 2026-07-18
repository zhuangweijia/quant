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
