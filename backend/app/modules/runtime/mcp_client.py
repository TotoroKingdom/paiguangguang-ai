"""Small MCP Streamable HTTP client."""

import hashlib
import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

import httpx
from jsonschema import Draft202012Validator, FormatChecker, SchemaError

from app.config import settings
from app.core.errors import APIError

MCP_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({MCP_PROTOCOL_VERSION})
MCP_TRANSPORT_STREAMABLE_HTTP = "http"
MCP_CLIENT_NAME = "paiguangguang-ai"
MCP_CLIENT_VERSION = "s2"
MAX_MCP_RESPONSE_BYTES = 1_000_000

_transport_factory: Callable[[], httpx.AsyncBaseTransport | None] | None = None


def set_transport_factory(factory: Callable[[], httpx.AsyncBaseTransport | None] | None) -> None:
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


@dataclass(frozen=True)
class McpTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None


def mcp_tool_fingerprint(tool: McpTool) -> str:
    payload = {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.input_schema,
        "outputSchema": tool.output_schema,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class _SchemaValidationError(ValueError):
    pass


def _schema_validator(schema: Any) -> Draft202012Validator:
    """Compile a JSON Schema without allowing remote reference resolution."""
    if not isinstance(schema, dict):
        raise _SchemaValidationError("schema must be an object")
    raw = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > 100_000:
        raise _SchemaValidationError("schema is too large")
    declared_draft = schema.get("$schema")
    if declared_draft is not None and declared_draft not in {
        "https://json-schema.org/draft/2020-12/schema",
        "http://json-schema.org/draft/2020-12/schema",
    }:
        raise _SchemaValidationError("schema must use JSON Schema 2020-12")
    if any(key in raw for key in ("\"$ref\"", "\"$dynamicRef\"", "\"$recursiveRef\"")):
        raise _SchemaValidationError("remote or recursive references are not supported")
    try:
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema, format_checker=FormatChecker())
    except SchemaError as error:
        raise _SchemaValidationError("schema is invalid") from error


class McpClient:
    """MCP 2025-06-18 client over the Streamable HTTP transport."""

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
        self._initialized = False
        self.session_id: str | None = None
        self.protocol_version: str | None = None
        self.server_info: dict[str, Any] = {}
        self.server_capabilities: dict[str, Any] = {}
        self._tools: dict[str, McpTool] = {}
        self._input_validators: dict[str, Draft202012Validator] = {}
        self._output_validators: dict[str, Draft202012Validator] = {}

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        return headers

    @staticmethod
    def _sse_payload(content: bytes, expected_id: int | None) -> dict[str, Any]:
        text = content.decode("utf-8", errors="strict")
        events: list[dict[str, Any]] = []
        data_lines: list[str] = []
        for line in text.replace("\r\n", "\n").split("\n") + [""]:
            if line == "":
                if data_lines:
                    data = "\n".join(data_lines)
                    if data != "[DONE]":
                        try:
                            item = json.loads(data)
                        except (TypeError, ValueError) as error:
                            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP SSE 数据不是 JSON") from error
                        if isinstance(item, dict):
                            events.append(item)
                    data_lines = []
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        for item in events:
            if expected_id is not None and item.get("id") == expected_id:
                return item
        for item in events:
            if "result" in item or "error" in item:
                return item
        raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP SSE 响应缺少 JSON-RPC 结果")

    @classmethod
    def _decode_payload(
        cls,
        response: httpx.Response,
        *,
        expected_id: int | None,
        allow_empty: bool,
    ) -> dict[str, Any]:
        if not response.content:
            if allow_empty:
                return {}
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应为空")
        content_type = response.headers.get("content-type", "").lower()
        if not (
            "application/json" in content_type
            or "text/event-stream" in content_type
        ):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应 Content-Type 不受支持")
        try:
            if "text/event-stream" in content_type:
                payload = cls._sse_payload(response.content, expected_id)
            else:
                payload = response.json()
        except APIError:
            raise
        except (UnicodeDecodeError, ValueError, TypeError) as error:
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应不是 JSON") from error
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应缺少 JSON-RPC 版本")
        if expected_id is not None and payload.get("id") != expected_id:
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应 ID 不匹配")
        return payload

    async def _request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        notification: bool = False,
    ) -> dict[str, Any]:
        request_id: int | None = None
        if not notification:
            self._counter += 1
            request_id = self._counter
        body: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        if request_id is not None:
            body["id"] = request_id
        headers = self._headers()
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
                stream_kwargs = {
                    "json": body,
                    "headers": headers,
                    "extensions": {"sni_hostname": original.host},
                }
                stream_method = getattr(client, "stream", None)
                if stream_method is None:
                    # Small test transports may only expose post().
                    response = await client.post(pinned, **stream_kwargs)
                else:
                    async with stream_method("POST", pinned, **stream_kwargs) as streamed:
                        chunks: list[bytes] = []
                        total = 0
                        is_sse = "text/event-stream" in streamed.headers.get("content-type", "").lower()
                        async for chunk in streamed.aiter_bytes():
                            total += len(chunk)
                            if total > MAX_MCP_RESPONSE_BYTES:
                                raise APIError(502, "MCP_RESPONSE_TOO_LARGE", "MCP 响应超过大小限制")
                            chunks.append(chunk)
                            if is_sse:
                                try:
                                    candidate = self._sse_payload(b"".join(chunks), request_id)
                                except APIError as error:
                                    if error.code != "MCP_PROTOCOL_ERROR" or "缺少 JSON-RPC 结果" not in error.message:
                                        raise
                                else:
                                    if request_id is None or candidate.get("id") == request_id:
                                        break
                        response = httpx.Response(
                            streamed.status_code,
                            headers=streamed.headers,
                            content=b"".join(chunks),
                            request=streamed.request,
                        )
        except httpx.TimeoutException as error:
            raise APIError(504, "MCP_TIMEOUT", "MCP 服务超时") from error
        except httpx.HTTPError as error:
            raise APIError(502, "MCP_UNAVAILABLE", "MCP 服务不可达") from error

        if response.status_code in {301, 302, 303, 307, 308}:
            raise APIError(502, "MCP_REDIRECT_BLOCKED", "MCP 服务返回重定向，已拒绝")
        if response.status_code in {401, 403}:
            raise APIError(401, "MCP_AUTH_FAILED", "MCP 服务鉴权失败")
        if response.status_code == 404 and self.session_id:
            raise APIError(409, "MCP_SESSION_EXPIRED", "MCP 会话已失效")
        if response.status_code >= 400:
            raise APIError(502, "MCP_UPSTREAM_ERROR", "MCP 服务返回错误")
        if len(response.content) > MAX_MCP_RESPONSE_BYTES:
            raise APIError(502, "MCP_RESPONSE_TOO_LARGE", "MCP 响应超过大小限制")

        if notification and response.status_code == 202 and not response.content:
            return {}
        payload = self._decode_payload(
            response,
            expected_id=request_id,
            allow_empty=notification,
        )
        if response.headers.get("Mcp-Session-Id"):
            self.session_id = response.headers["Mcp-Session-Id"]
        if payload.get("error"):
            error = payload["error"]
            if isinstance(error, dict):
                raise APIError(
                    502,
                    "MCP_PROTOCOL_ERROR",
                    "MCP 调用失败",
                    {"rpcCode": error.get("code"), "rpcMessage": str(error.get("message", ""))[:200]},
                )
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 调用失败")
        result = payload.get("result")
        if notification:
            return result if isinstance(result, dict) else {}
        if not isinstance(result, dict):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 响应缺少 result")
        return result

    async def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Backward-compatible low-level RPC seam used by older integrations."""
        return await self._request(method, params)

    async def initialize(self) -> dict[str, Any]:
        await self._ensure_initialized()
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": self.server_capabilities,
            "serverInfo": self.server_info,
            "sessionId": self.session_id,
        }

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        try:
            result = await self._request(
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": MCP_CLIENT_NAME, "version": MCP_CLIENT_VERSION},
                },
            )
        except APIError:
            raise
        version = result.get("protocolVersion")
        if not isinstance(version, str) or version not in SUPPORTED_PROTOCOL_VERSIONS:
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 协议版本不受支持")
        capabilities = result.get("capabilities")
        server_info = result.get("serverInfo")
        if (
            not isinstance(capabilities, dict)
            or not isinstance(server_info, dict)
            or "capabilities" not in result
            or "serverInfo" not in result
            or not isinstance(server_info.get("name"), str)
            or not server_info["name"]
            or not isinstance(server_info.get("version"), str)
            or not server_info["version"]
        ):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 能力协商响应无效")
        self.protocol_version = version
        self.server_capabilities = capabilities
        self.server_info = server_info
        await self._request("notifications/initialized", notification=True)
        self._initialized = True

    async def list_tools(self) -> list[McpTool]:
        await self._ensure_initialized()
        result = await self._request("tools/list")
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "tools/list 响应缺少 tools")
        parsed: list[McpTool] = []
        input_validators: dict[str, Draft202012Validator] = {}
        output_validators: dict[str, Draft202012Validator] = {}
        for item in tools:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"]:
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具定义无效")
            if item["name"] in input_validators:
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具名称重复")
            description = item.get("description", "")
            if not isinstance(description, str):
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具描述无效")
            schema = item.get("inputSchema")
            if not isinstance(schema, dict) or schema.get("type") != "object":
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具输入 Schema 必须是 object")
            output_schema = item.get("outputSchema")
            if output_schema is not None and not isinstance(output_schema, dict):
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具输出 Schema 无效")
            try:
                input_validator = _schema_validator(schema)
                output_validator = (
                    _schema_validator(output_schema) if output_schema is not None else None
                )
            except _SchemaValidationError as error:
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具 Schema 不受支持") from error
            parsed.append(
                McpTool(
                    name=item["name"],
                    description=description,
                    input_schema=schema,
                    output_schema=output_schema,
                )
            )
            input_validators[item["name"]] = input_validator
            if output_validator is not None:
                output_validators[item["name"]] = output_validator
        self._tools = {tool.name: tool for tool in parsed}
        self._input_validators = input_validators
        self._output_validators = output_validators
        return parsed

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_initialized()
        if not isinstance(name, str) or not name.strip():
            raise APIError(422, "MCP_TOOL_INVALID", "MCP 工具名称无效")
        if not isinstance(arguments, dict):
            raise APIError(422, "MCP_TOOL_INVALID", "MCP 工具参数必须是对象")
        if not self._tools:
            await self.list_tools()
        tool = self._tools.get(name)
        if tool is None:
            raise APIError(422, "MCP_TOOL_INVALID", "MCP 工具未在发现列表中")
        input_validator = self._input_validators.get(name)
        if input_validator is None:
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 输入 Schema 未编译")
        input_error = next(input_validator.iter_errors(arguments), None)
        if input_error is not None:
            raise APIError(422, "MCP_TOOL_INVALID", "MCP 工具参数不符合输入 Schema") from input_error
        result = await self._request("tools/call", {"name": name, "arguments": arguments})
        if "isError" in result and not isinstance(result["isError"], bool):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具 isError 无效")
        if result.get("isError") is True:
            raise APIError(502, "MCP_TOOL_FAILED", "MCP 工具业务执行失败")
        content = result.get("content")
        if not isinstance(content, list):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具输出 content 无效")
        if "structuredContent" in result and not isinstance(result["structuredContent"], dict):
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具结构化输出无效")
        if tool.output_schema is not None and "structuredContent" not in result:
            raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具缺少结构化输出")
        if tool.output_schema is not None and "structuredContent" in result:
            output_validator = self._output_validators.get(name)
            if output_validator is None:
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 输出 Schema 未编译")
            output_error = next(output_validator.iter_errors(result["structuredContent"]), None)
            if output_error is not None:
                raise APIError(502, "MCP_PROTOCOL_ERROR", "MCP 工具输出不符合 Schema") from output_error
        return result
