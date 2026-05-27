from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.trade.base import BrokerAdapter, PaperBroker, get_paper_broker
from app.services.trade.brokers.binance import BinanceBroker
from app.services.settings_service import get_settings_category
from app.services.account_service import get_or_create_account
import structlog

logger = structlog.get_logger()

_broker_cache: dict[str, BrokerAdapter] = {}


async def get_broker_for_user(db: AsyncSession, user_id: str, market: str = "") -> BrokerAdapter:
    account = await get_or_create_account(db, user_id)
    if account.mode == "paper":
        return get_paper_broker()

    broker = await _resolve_broker(db, user_id, market)
    return broker or get_paper_broker()


async def _resolve_broker(db: AsyncSession, user_id: str, market: str) -> BrokerAdapter | None:
    if market == "crypto":
        return await _get_binance_broker(db, user_id)
    if market == "us_stock":
        return await _get_alpaca_broker(db, user_id)
    return None


async def _get_binance_broker(db: AsyncSession, user_id: str) -> BinanceBroker | None:
    cache_key = f"binance:{user_id}"
    cached = _broker_cache.get(cache_key)
    if cached and isinstance(cached, BinanceBroker):
        return cached

    config = await get_settings_category(db, user_id, "broker:binance")
    api_key = config.get("api_key", "")
    api_secret = config.get("api_secret", "")
    if not api_key or not api_secret:
        logger.warning("broker.no_credentials", broker="binance", user_id=user_id)
        return None

    import json
    extra = config.get("extra_params", "{}")
    try:
        params = json.loads(extra) if isinstance(extra, str) else extra
    except (json.JSONDecodeError, TypeError):
        params = {}
    testnet = params.get("testnet", False)

    broker = BinanceBroker(
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
    )
    _broker_cache[cache_key] = broker
    return broker


async def _get_alpaca_broker(db: AsyncSession, user_id: str) -> BrokerAdapter | None:
    from app.services.trade.brokers.alpaca import AlpacaBroker

    cache_key = f"alpaca:{user_id}"
    cached = _broker_cache.get(cache_key)
    if cached and isinstance(cached, AlpacaBroker):
        return cached

    config = await get_settings_category(db, user_id, "broker:alpaca")
    api_key = config.get("api_key", "")
    api_secret = config.get("api_secret", "")
    if not api_key or not api_secret:
        logger.warning("broker.no_credentials", broker="alpaca", user_id=user_id)
        return None

    broker = AlpacaBroker(api_key=api_key, api_secret=api_secret)
    _broker_cache[cache_key] = broker
    return broker


async def test_broker_connection(db: AsyncSession, user_id: str, broker_name: str) -> dict:
    if broker_name == "akshare":
        try:
            import akshare
            return {"connected": True}
        except ImportError:
            return {"connected": False, "error": "AKShare 未安装"}

    if broker_name == "binance":
        broker = await _get_binance_broker(db, user_id)
        if not broker:
            return {"connected": False, "error": "未配置 API Key"}
        ok = await broker.health_check()
        return {"connected": ok}

    if broker_name == "alpaca":
        broker = await _get_alpaca_broker(db, user_id)
        if not broker:
            return {"connected": False, "error": "未配置 API Key"}
        ok = await broker.health_check()
        return {"connected": ok}

    return {"connected": False, "error": "不支持的交易所"}


def invalidate_broker_cache(user_id: str, broker_name: str = "") -> None:
    if broker_name:
        key = f"{broker_name}:{user_id}"
        broker = _broker_cache.pop(key, None)
        if broker and isinstance(broker, BinanceBroker):
            import asyncio
            try:
                asyncio.get_event_loop().create_task(broker.close())
            except Exception:
                pass
    else:
        for key in list(_broker_cache.keys()):
            if user_id in key:
                broker = _broker_cache.pop(key, None)
                if broker and isinstance(broker, BinanceBroker):
                    import asyncio
                    try:
                        asyncio.get_event_loop().create_task(broker.close())
                    except Exception:
                        pass
