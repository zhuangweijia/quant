from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
import structlog

logger = structlog.get_logger()


async def log_action(
    db: AsyncSession,
    *,
    user_id: UUID | str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    uid = UUID(str(user_id)) if user_id and not isinstance(user_id, UUID) else user_id
    log = AuditLog(
        user_id=uid,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()


def extract_request_info(request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    ua = request.headers.get("User-Agent")
    if ua and len(ua) > 512:
        ua = ua[:512]
    return ip, ua
