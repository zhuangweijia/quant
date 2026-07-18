import time
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, func, select

from app.schemas.settings import SystemParams

logger = structlog.get_logger()

_BATCH_SIZE = 5000


def retention_days_by_table(params: SystemParams) -> dict[str, int]:
    return {
        "alerts": params.alert_retention_days,
        "notification_logs": params.data_retention_days,
        "market_data": params.data_retention_days,
        "audit_logs": params.data_retention_days,
    }


async def run_cleanup():
    from app.database import AsyncSessionLocal
    from app.services.settings_service import get_system_params

    start = time.monotonic()
    total_deleted = 0

    try:
        async with AsyncSessionLocal() as db:
            params = await get_system_params(db)
            retention = retention_days_by_table(params)

            tables_config = [
                ("alerts", "app.models.alert", "Alert", retention["alerts"]),
                (
                    "notification_logs",
                    "app.models.notification_log",
                    "NotificationLog",
                    retention["notification_logs"],
                ),
                (
                    "market_data",
                    "app.models.market_data",
                    "MarketData",
                    retention["market_data"],
                ),
                ("audit_logs", "app.models.audit_log", "AuditLog", retention["audit_logs"]),
            ]

            for table_name, module_path, class_name, retention_days in tables_config:
                try:
                    import importlib

                    module = importlib.import_module(module_path)
                    model_class = getattr(module, class_name)

                    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
                    table_total = 0

                    while True:
                        count_result = await db.execute(
                            select(func.count())
                            .select_from(model_class)
                            .where(model_class.created_at < cutoff)
                            .limit(1)
                        )
                        remaining = count_result.scalar() or 0
                        if remaining == 0:
                            break

                        result = await db.execute(
                            delete(model_class).where(
                                model_class.id.in_(
                                    select(model_class.id)
                                    .where(model_class.created_at < cutoff)
                                    .limit(_BATCH_SIZE)
                                )
                            )
                        )
                        table_total += result.rowcount
                        await db.commit()

                    if table_total > 0:
                        logger.info(
                            "cleanup.table_done",
                            table=table_name,
                            deleted=table_total,
                            retention_days=retention_days,
                        )
                    total_deleted += table_total

                except Exception as e:
                    logger.error("cleanup.table_failed", table=table_name, error=str(e))
                    await db.rollback()

    except Exception as e:
        logger.error("cleanup.failed", error=str(e))

    elapsed = round(time.monotonic() - start, 2)
    logger.info("cleanup.completed", total_deleted=total_deleted, elapsed_seconds=elapsed)
