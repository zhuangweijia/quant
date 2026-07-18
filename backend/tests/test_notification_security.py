from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from app.core.webhook_security import (
    ResolvedWebhookTarget,
    UnsafeWebhookURLError,
    resolve_public_webhook_target,
)
from app.schemas.settings import NotificationConfigRequest
from app.services import notification_service


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/hook",
        "http://10.0.0.8/hook",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/hook",
    ],
)
def test_notification_schema_rejects_unsafe_literal_webhook_urls(url):
    with pytest.raises(ValidationError):
        NotificationConfigRequest(webhook_enabled=True, webhook_url=url)


@pytest.mark.asyncio
async def test_webhook_resolution_rejects_private_or_rebinding_answers(monkeypatch):
    monkeypatch.setattr(
        "app.core.webhook_security._resolve_host_addresses",
        AsyncMock(return_value=["93.184.216.34", "10.0.0.8"]),
    )

    with pytest.raises(UnsafeWebhookURLError, match="公网"):
        await resolve_public_webhook_target("https://hooks.example.com/events")


@pytest.mark.asyncio
async def test_webhook_resolution_pins_a_validated_public_address(monkeypatch):
    monkeypatch.setattr(
        "app.core.webhook_security._resolve_host_addresses",
        AsyncMock(return_value=["93.184.216.34"]),
    )

    target = await resolve_public_webhook_target(
        "https://hooks.example.com:8443/events?source=quant"
    )

    assert target.request_url == "https://93.184.216.34:8443/events?source=quant"
    assert target.host_header == "hooks.example.com:8443"
    assert target.sni_hostname == "hooks.example.com"


@pytest.mark.asyncio
async def test_send_webhook_uses_the_pinned_target_without_redirects(monkeypatch):
    target = ResolvedWebhookTarget(
        request_url="https://93.184.216.34/events",
        host_header="hooks.example.com",
        sni_hostname="hooks.example.com",
    )
    monkeypatch.setattr(
        notification_service.settings_service,
        "get_settings_category",
        AsyncMock(
            return_value={
                "webhook_enabled": "true",
                "webhook_url": "https://hooks.example.com/events",
            }
        ),
    )
    monkeypatch.setattr(
        notification_service,
        "resolve_public_webhook_target",
        AsyncMock(return_value=target),
    )
    monkeypatch.setattr(notification_service, "_log_notification", AsyncMock())

    captured = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def build_request(self, method, url, **kwargs):
            captured.update(method=method, url=url, kwargs=kwargs)
            return SimpleNamespace()

        async def send(self, request, **kwargs):
            captured.update(request=request, send_kwargs=kwargs)
            return SimpleNamespace(status_code=200)

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    sent = await notification_service.send_webhook(
        SimpleNamespace(), "user-1", "test", {"message": "ok"}
    )

    assert sent is True
    assert captured["url"] == target.request_url
    assert captured["kwargs"]["headers"]["Host"] == target.host_header
    assert captured["kwargs"]["extensions"] == {"sni_hostname": target.sni_hostname}
    assert captured["send_kwargs"] == {"follow_redirects": False}
