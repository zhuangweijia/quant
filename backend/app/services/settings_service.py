from collections.abc import Mapping

import structlog
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import Encryption
from app.models.setting import Setting
from app.schemas.settings import SystemParams

logger = structlog.get_logger()

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
    db: AsyncSession,
    user_id: str | None,
    category: str,
    key: str,
    value: str,
    encrypted: bool = False,
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
    candidate = {
        **default_data,
        **{key: value for key, value in overrides.items() if key in default_data},
    }

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
        select(Setting).where(
            Setting.user_id.is_(None),
            Setting.category == "system",
        )
    )
    overrides = {
        setting.key: setting.value
        for setting in result.scalars().all()
        if setting.value is not None
    }
    return merge_system_params(overrides)


async def save_system_params(db: AsyncSession, params: SystemParams) -> SystemParams:
    rows = [
        {
            "user_id": None,
            "category": "system",
            "key": key,
            "value": str(value),
            "encrypted": False,
        }
        for key, value in params.model_dump().items()
    ]
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        for row in rows:
            await set_setting(
                db,
                row["user_id"],
                row["category"],
                row["key"],
                row["value"],
            )
        return await get_system_params(db)

    statement = insert(Setting).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[Setting.category, Setting.key],
        index_where=Setting.user_id.is_(None),
        set_={
            "value": statement.excluded.value,
            "encrypted": statement.excluded.encrypted,
            "updated_at": func.now(),
        },
    )
    await db.execute(statement)
    return await get_system_params(db)


async def reset_system_params(db: AsyncSession) -> SystemParams:
    result = await db.execute(
        select(Setting).where(
            Setting.user_id.is_(None),
            Setting.category == "system",
        )
    )
    for s in result.scalars().all():
        await db.delete(s)
    await db.flush()
    return get_default_system_params()


async def load_runtime_system_params() -> SystemParams:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return await get_system_params(db)
