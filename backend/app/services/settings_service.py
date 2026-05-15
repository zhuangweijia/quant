from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.core.security import Encryption
import structlog

logger = structlog.get_logger()

_DEFAULT_PARAMS = {
    "max_strategies_per_user": "50",
    "max_running_strategies": "10",
    "max_concurrent_backtests": "3",
    "backtest_timeout": "600",
    "order_timeout": "30",
    "paper_initial_capital": "1000000",
    "default_commission_a_stock": "0.00025",
    "default_commission_us_stock": "0.005",
    "default_commission_crypto": "0.001",
    "data_retention_days": "30",
    "alert_retention_days": "90",
}


async def get_setting(db: AsyncSession, user_id: str | None, category: str, key: str) -> str | None:
    result = await db.execute(
        select(Setting).where(
            Setting.user_id == user_id,
            Setting.category == category,
            Setting.key == key,
        )
    )
    setting = result.scalar_one_or_none()
    if setting and setting.encrypted and setting.value:
        try:
            return Encryption.decrypt(setting.value)
        except Exception:
            return setting.value
    return setting.value if setting else None


async def set_setting(
    db: AsyncSession, user_id: str | None, category: str, key: str,
    value: str, encrypted: bool = False,
) -> Setting:
    result = await db.execute(
        select(Setting).where(
            Setting.user_id == user_id,
            Setting.category == category,
            Setting.key == key,
        )
    )
    setting = result.scalar_one_or_none()

    store_value = value
    if encrypted and value:
        try:
            store_value = Encryption.encrypt(value)
        except Exception:
            logger.warning("settings.encrypt_failed", key=key)

    if setting:
        setting.value = store_value
        setting.encrypted = encrypted
    else:
        setting = Setting(
            user_id=user_id,
            category=category,
            key=key,
            value=store_value,
            encrypted=encrypted,
        )
        db.add(setting)

    await db.flush()
    return setting


async def get_settings_category(db: AsyncSession, user_id: str | None, category: str) -> dict:
    result = await db.execute(
        select(Setting).where(
            Setting.user_id == user_id,
            Setting.category == category,
        )
    )
    settings = result.scalars().all()
    data = {}
    for s in settings:
        if s.encrypted and s.value:
            try:
                data[s.key] = Encryption.decrypt(s.value)
            except Exception:
                data[s.key] = s.value
        else:
            data[s.key] = s.value
    return data


async def get_system_params(db: AsyncSession) -> dict:
    result = await db.execute(
        select(Setting).where(
            Setting.user_id.is_(None),
            Setting.category == "system",
        )
    )
    settings = result.scalars().all()
    data = dict(_DEFAULT_PARAMS)
    for s in settings:
        data[s.key] = s.value
    return data


async def save_system_params(db: AsyncSession, params: dict) -> dict:
    for key, value in params.items():
        if key in _DEFAULT_PARAMS:
            await set_setting(db, None, "system", key, str(value))
    return await get_system_params(db)


async def reset_system_params(db: AsyncSession) -> dict:
    result = await db.execute(
        select(Setting).where(
            Setting.user_id.is_(None),
            Setting.category == "system",
        )
    )
    for s in result.scalars().all():
        await db.delete(s)
    await db.flush()
    return dict(_DEFAULT_PARAMS)
