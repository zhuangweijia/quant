from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.core.security import Encryption
import structlog

logger = structlog.get_logger()

_DEFAULT_PARAMS = {
    "data_retention_days": "90",
    "alert_retention_days": "90",
    "model_train_window_days": "756",
    "model_val_window_days": "126",
    "forward_return_days": "5",
    "forward_return_threshold": "0.02",
    "model_ic_threshold": "0.02",
    "stock_universe": "csi300",
    "analysis_time": "17:00",
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
            logger.error("settings.decrypt_failed", key=key, category=category)
            return None
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
        store_value = Encryption.encrypt(value)

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
                logger.error("settings.decrypt_failed", key=s.key, category=category)
                data[s.key] = None
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
