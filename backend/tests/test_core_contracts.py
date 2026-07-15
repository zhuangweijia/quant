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
