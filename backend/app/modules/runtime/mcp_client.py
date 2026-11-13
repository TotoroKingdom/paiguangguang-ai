import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.core.errors import APIError

_transport_factory: Callable[[], httpx.AsyncBaseTransport | None] | None = None


def set_transport_factory(
    factory: Callable[[], httpx.AsyncBaseTransport | None] | None,
) -> None:
    """Test seam for MCP protocol tests without external network calls."""
    global _transport_factory
    _transport_factory = factory


def default_transport() -> httpx.AsyncBaseTransport | None:
    return _transport_factory() if _transport_factory is not None else None


def _resolve_mcp_url(url: str) -> tuple[str, str]:
    value = (url or "").strip()
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise APIError(422, "MCP_URL_INVALID", "MCP 地址不能包含凭据")
    if parsed.scheme not in {"https", "http"}:
        raise APIError(422, "MCP_URL_INVALID", "MCP 地址必须使用 HTTPS")
    if settings.environment.lower() in {"production", "prod"} and parsed.scheme != "https":
        raise APIError(422, "MCP_URL_INVALID", "生产环境 MCP 必须使用 HTTPS")
    host = parsed.hostname or ""
    if not host:
        raise APIError(422, "MCP_URL_INVALID", "MCP 地址缺少主机")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = {info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except (socket.gaierror, ValueError) as error:
        raise APIError(422, "MCP_URL_INVALID", "MCP 主机无法解析") from error
    if not addresses:
        raise APIError(422, "MCP_URL_INVALID", "MCP 主机无法解析")
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as error:
            raise APIError(422, "MCP_URL_INVALID", "MCP 主机解析结果无效") from error
        mapped = getattr(ip, "ipv4_mapped", None)
        if (
            not ip.is_global
            or ip.is_reserved
            or ip.is_multicast
            or (mapped is not None and (not mapped.is_global or mapped.is_reserved))
        ):
            raise APIError(422, "MCP_URL_BLOCKED", "MCP 地址不能指向内网或保留地址")
    return value, sorted(addresses)[0]


def validate_mcp_url(url: str) -> str:
    return _resolve_mcp_url(url)[0]


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any]


class McpClient:
    def __init__(
        self,
        endpoint_url: str,
        *,
        token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 20,
    ):
        self.endpoint_url = endpoint_url
        self.token = token
        self.transport = transport if transport is not None else default_transport()
        self.timeout = timeout
        self._counter = 0

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._counter += 1
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = {
            "jsonrpc": "2.0",
            "id": self._counter,
            "method": method,
            "params": params or {},
        }
        try:
            endpoint, address = _resolve_mcp_url(self.endpoint_url)
            original = httpx.URL(endpoint)
            pinned = original.copy_with(host=address)
            headers["Host"] = original.netloc.decode("ascii")
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = await client.post(
                    pinned, json=body, headers=headers,
                    extensions={"sni_hostname": original.host},
                )
        except httpx.TimeoutException as error:
            raise APIError(504, "MCP_TIMEOUT", "MCP 服务超时") from error
        except httpx.HTTPError as error:
            raise APIError(502, "MCP_UNAVAILABLE", "MCP 服务不可达") from error
        if response.status_code in {301, 302, 303, 307, 308}:
            raise APIError(502, "MCP_REDIRECT_BLOCKED", "MCP 服务返回重定向，已拒绝")
        if response.status_code >= 400:
            raise APIError(502, "MCP_UPSTREAM_ERROR", "MCP 服务返回错误")
        try:
            payload = response.json()
        except ValueError as error:
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应不是 JSON") from error
        if payload.get("error"):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 调用失败")
        return payload.get("result") or {}

    async def list_tools(self) -> list[McpTool]:
        result = await self._rpc("tools/list")
        return [
            McpTool(
                name=str(item.get("name", "")),
                description=str(item.get("description", "")),
                input_schema=item.get("inputSchema") or {},
            )
            for item in result.get("tools", [])
            if item.get("name")
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self._rpc("tools/call", {"name": name, "arguments": arguments})
