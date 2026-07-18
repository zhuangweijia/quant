import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UnsafeWebhookURLError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedWebhookTarget:
    request_url: str
    host_header: str
    sni_hostname: str


def _public_ip(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


def _parse_webhook_url(url: str) -> tuple[SplitResult, str, int | None]:
    value = url.strip()
    if not value:
        raise UnsafeWebhookURLError("Webhook URL 不能为空")

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeWebhookURLError("Webhook URL 仅支持 http 或 https")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeWebhookURLError("Webhook URL 不能包含用户名或密码")
    if parsed.fragment:
        raise UnsafeWebhookURLError("Webhook URL 不能包含片段")
    if not parsed.hostname:
        raise UnsafeWebhookURLError("Webhook URL 缺少主机名")

    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeWebhookURLError("Webhook URL 端口无效") from exc

    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UnsafeWebhookURLError("Webhook URL 主机名无效") from exc

    if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
        raise UnsafeWebhookURLError("Webhook URL 必须指向公网地址")

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        raise UnsafeWebhookURLError("Webhook URL 必须指向公网地址")

    return parsed, hostname, port


def validate_webhook_url(url: str) -> str:
    if not url.strip():
        return ""
    parsed, hostname, port = _parse_webhook_url(url)
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = f"{display_host}:{port}" if port is not None else display_host
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path, parsed.query, ""))


async def _resolve_host_addresses(hostname: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    records = await loop.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(record[4][0] for record in records))


async def resolve_public_webhook_target(url: str) -> ResolvedWebhookTarget:
    normalized = validate_webhook_url(url)
    parsed, hostname, explicit_port = _parse_webhook_url(normalized)
    port = explicit_port or (443 if parsed.scheme == "https" else 80)

    try:
        addresses = await _resolve_host_addresses(hostname, port)
    except OSError as exc:
        raise UnsafeWebhookURLError("Webhook 主机无法解析") from exc
    if not addresses or any(not _public_ip(address) for address in addresses):
        raise UnsafeWebhookURLError("Webhook URL 必须指向公网地址")

    address = addresses[0]
    pinned_host = f"[{address}]" if ":" in address else address
    request_netloc = (
        f"{pinned_host}:{explicit_port}" if explicit_port is not None else pinned_host
    )
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    host_header = f"{display_host}:{explicit_port}" if explicit_port is not None else display_host
    request_url = urlunsplit(
        (parsed.scheme, request_netloc, parsed.path or "/", parsed.query, "")
    )
    return ResolvedWebhookTarget(
        request_url=request_url,
        host_header=host_header,
        sni_hostname=hostname,
    )
