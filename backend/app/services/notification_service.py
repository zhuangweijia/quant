import asyncio
import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.settings_service as settings_service
from app.core.webhook_security import resolve_public_webhook_target
from app.models.notification_log import NotificationLog

logger = structlog.get_logger()


async def send_email(db: AsyncSession, user_id: str, subject: str, body: str) -> bool:
    config = await settings_service.get_settings_category(db, user_id, "notification")
    if str(config.get("email_enabled", "false")).lower() != "true":
        return False

    smtp_host = config.get("email_smtp_host", "")
    smtp_port = int(config.get("email_smtp_port", "465"))
    sender = config.get("email_sender", "")
    password = config.get("email_password", "")
    recipient = config.get("email_recipient", "")

    if not all([smtp_host, sender, password, recipient]):
        await _log_notification(
            db, user_id, "email", "email", subject, body, "failed", "邮件配置不完整"
        )
        return False

    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))

        use_ssl = config.get("email_use_ssl", "true").lower() == "true"

        def _send_smtp():
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
            server.quit()

        await asyncio.to_thread(_send_smtp)

        await _log_notification(db, user_id, "email", "email", subject, body, "sent")
        return True
    except Exception as e:
        await _log_notification(db, user_id, "email", "email", subject, body, "failed", str(e))
        return False


async def send_webhook(db: AsyncSession, user_id: str, event_type: str, data: dict) -> bool:
    config = await settings_service.get_settings_category(db, user_id, "notification")
    if str(config.get("webhook_enabled", "false")).lower() != "true":
        return False

    url = config.get("webhook_url", "")
    if not url:
        await _log_notification(
            db, user_id, "webhook", event_type, "", json.dumps(data), "failed", "Webhook URL 未配置"
        )
        return False

    try:
        import httpx

        secret = config.get("webhook_secret", "")
        headers = {"Content-Type": "application/json"}
        if secret:
            import hashlib
            import hmac

            payload = json.dumps(data, default=str)
            signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            headers["X-Signature"] = signature

        target = await resolve_public_webhook_target(url)
        headers["Host"] = target.host_header
        async with httpx.AsyncClient() as client:
            request = client.build_request(
                "POST",
                target.request_url,
                json=data,
                headers=headers,
                timeout=10,
                extensions={"sni_hostname": target.sni_hostname},
            )
            resp = await client.send(request, follow_redirects=False)

        if resp.status_code < 400:
            await _log_notification(
                db, user_id, "webhook", event_type, "", json.dumps(data), "sent"
            )
            return True
        else:
            await _log_notification(
                db,
                user_id,
                "webhook",
                event_type,
                "",
                json.dumps(data),
                "failed",
                f"HTTP {resp.status_code}",
            )
            return False
    except Exception as e:
        await _log_notification(
            db, user_id, "webhook", event_type, "", json.dumps(data), "failed", str(e)
        )
        return False


async def _log_notification(
    db: AsyncSession,
    user_id: str,
    channel: str,
    event_type: str,
    title: str | None,
    content: str | None,
    status: str,
    error: str | None = None,
):
    log = NotificationLog(
        user_id=user_id,
        channel=channel,
        event_type=event_type,
        title=title,
        content=content,
        status=status,
        error=error,
    )
    db.add(log)
    await db.flush()
