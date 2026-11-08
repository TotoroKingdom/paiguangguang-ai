import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.core.errors import APIError


def validate_mcp_url(url: str) -> str:
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
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port or 443)}
    except socket.gaierror as error:
        raise APIError(422, "MCP_URL_INVALID", "MCP 主机无法解析") from error
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise APIError(422, "MCP_URL_BLOCKED", "MCP 地址不能指向内网或保留地址")
    return value


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
        self.transport = transport
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
        async with httpx.AsyncClient(
            timeout=self.timeout,
            transport=self.transport,
            follow_redirects=False,
        ) as client:
            response = await client.post(self.endpoint_url, json=body, headers=headers)
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
