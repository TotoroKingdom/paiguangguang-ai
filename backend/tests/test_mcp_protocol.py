import asyncio
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from app.core.errors import APIError
from app.modules.runtime.mcp_client import McpClient


class _LocalRouteTransport(httpx.AsyncBaseTransport):
    """Route only the already-validated test hostname to the local server."""

    def __init__(self):
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        routed_url = request.url.copy_with(host="127.0.0.1")
        routed_request = httpx.Request(
            request.method,
            routed_url,
            headers=request.headers,
            content=request.content,
            extensions=request.extensions,
        )
        return await self._inner.handle_async_request(routed_request)

    async def aclose(self) -> None:
        await self._inner.aclose()


class _ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]):
        self.chunks = chunks
        self.consumed = 0

    async def __aiter__(self):
        for chunk in self.chunks:
            self.consumed += 1
            yield chunk

    async def aclose(self) -> None:
        return None


class _EarlyStopTransport(httpx.AsyncBaseTransport):
    def __init__(self):
        self.sse_stream: _ChunkStream | None = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body["method"]
        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "stream", "version": "1"},
                    },
                },
                headers={"Mcp-Session-Id": "stream-session"},
                request=request,
            )
        if method == "notifications/initialized":
            return httpx.Response(202, request=request)
        if method == "tools/list":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "tools": [{"name": "search", "inputSchema": {"type": "object"}}]
                    },
                },
                request=request,
            )
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"content": [{"type": "text", "text": "stream-ok"}]},
            }
        ).encode()
        self.sse_stream = _ChunkStream(
            [b"event: message\ndata: " + payload + b"\n\n", b"x" * 1_100_000]
        )
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            stream=self.sse_stream,
            request=request,
        )

    async def aclose(self) -> None:
        return None


@contextmanager
def _local_streamable_server():
    observations: list[tuple[dict, dict[str, str]]] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            return

        def do_POST(self):  # noqa: N802 - stdlib handler hook
            length = int(self.headers.get("content-length", "0"))
            body = json.loads(self.rfile.read(length))
            observations.append((body, {key.lower(): value for key, value in self.headers.items()}))
            method = body.get("method")
            if method == "initialize":
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {"tools": {"listChanged": False}},
                            "serverInfo": {"name": "local-mcp", "version": "1"},
                        },
                    },
                    headers={"Mcp-Session-Id": "local-session-1"},
                )
            elif method == "notifications/initialized":
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
            elif method == "tools/list":
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {
                            "tools": [
                                {
                                    "name": "search",
                                    "description": "read-only search",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {"query": {"type": "string"}},
                                        "required": ["query"],
                                    },
                                }
                            ]
                        },
                    }
                )
            elif method == "tools/call":
                payload = json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {"content": [{"type": "text", "text": "local-ok"}]},
                    }
                ).encode()
                encoded = b"event: message\ndata: " + payload + b"\n\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            else:
                self.send_error(400)

        def _send_json(self, value: dict, headers: dict[str, str] | None = None):
            encoded = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, observations
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_streamable_http_initializes_discovers_and_calls_with_session(monkeypatch):
    with _local_streamable_server() as (port, observations):
        endpoint = f"http://mcp.example.test:{port}/rpc"
        original_getaddrinfo = socket.getaddrinfo
        dns_calls: list[tuple[str, int]] = []

        def public_dns(host, requested_port, *args, **kwargs):
            if host == "mcp.example.test":
                dns_calls.append((host, requested_port))
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", requested_port))]
            return original_getaddrinfo(host, requested_port, *args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", public_dns)
        client = McpClient(
            endpoint,
            token="local-token",
            transport=_LocalRouteTransport(),
            timeout=3,
        )
        negotiated = asyncio.run(client.initialize())
        tools = asyncio.run(client.list_tools())
        result = asyncio.run(client.call_tool("search", {"query": "policy"}))

    assert negotiated["protocolVersion"] == "2025-06-18"
    assert negotiated["capabilities"]["tools"]["listChanged"] is False
    assert negotiated["sessionId"] == "local-session-1"
    assert tools[0].name == "search"
    assert tools[0].input_schema["required"] == ["query"]
    assert result["content"][0]["text"] == "local-ok"
    assert [item[0]["method"] for item in observations] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    initialize, notification, listing, calling = observations
    assert initialize[0]["params"]["protocolVersion"] == "2025-06-18"
    assert "id" not in notification[0]
    assert listing[1]["mcp-session-id"] == "local-session-1"
    assert calling[1]["mcp-session-id"] == "local-session-1"
    assert calling[1]["mcp-protocol-version"] == "2025-06-18"
    assert calling[1]["authorization"] == "Bearer local-token"
    assert calling[1]["host"] == f"mcp.example.test:{port}"
    assert dns_calls


def test_sse_stops_after_matching_response(monkeypatch):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )
    transport = _EarlyStopTransport()
    client = McpClient("https://mcp.example.test/rpc", transport=transport)
    result = asyncio.run(client.call_tool("search", {}))
    assert result["content"][0]["text"] == "stream-ok"
    assert transport.sse_stream is not None
    assert transport.sse_stream.consumed == 1


def test_mcp_authentication_failure_is_distinct(monkeypatch):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request)

    with pytest.raises(APIError) as error:
        asyncio.run(
            McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler)).initialize()
        )
    assert error.value.code == "MCP_AUTH_FAILED"


def test_mcp_tool_business_failure_is_distinct(monkeypatch):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fixture", "version": "1"},
            }
        elif body["method"] == "notifications/initialized":
            return httpx.Response(202, request=request)
        elif body["method"] == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "write",
                        "description": "fixture",
                        "inputSchema": {"type": "object"},
                    }
                ]
            }
        else:
            result = {"isError": True, "content": [{"type": "text", "text": "denied"}]}
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body.get("id"), "result": result},
            request=request,
            headers={"Mcp-Session-Id": "session"} if body["method"] == "initialize" else {},
        )

    client = McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler))
    with pytest.raises(APIError) as error:
        asyncio.run(client.call_tool("write", {}))
    assert error.value.code == "MCP_TOOL_FAILED"


def test_initialize_without_negotiated_version_is_protocol_failure(monkeypatch):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body["id"], "result": {"capabilities": {}}},
            request=request,
        )

    with pytest.raises(APIError) as error:
        asyncio.run(
            McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler)).initialize()
        )
    assert error.value.code == "MCP_PROTOCOL_ERROR"


@pytest.mark.parametrize("version", ["2025-03-26", "unsupported"])
def test_only_current_protocol_version_is_accepted(monkeypatch, version):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "protocolVersion": version,
                    "capabilities": {},
                    "serverInfo": {"name": "fixture", "version": "1"},
                },
            },
            request=request,
        )

    with pytest.raises(APIError) as error:
        asyncio.run(
            McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler)).initialize()
        )
    assert error.value.code == "MCP_PROTOCOL_ERROR"


def test_expired_mcp_session_is_distinct(monkeypatch):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "fixture", "version": "1"},
                    },
                },
                headers={"Mcp-Session-Id": "expired-session"},
                request=request,
            )
        if body["method"] == "notifications/initialized":
            return httpx.Response(202, request=request)
        return httpx.Response(404, request=request)

    client = McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler))
    with pytest.raises(APIError) as error:
        asyncio.run(client.list_tools())
    assert error.value.code == "MCP_SESSION_EXPIRED"


@pytest.mark.parametrize(
    "schema",
    [
        {},
        {
            "type": "object",
            "$schema": "http://json-schema.org/draft-07/schema#",
        },
    ],
)
def test_tools_list_requires_current_object_input_schema(monkeypatch, schema):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["method"] == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fixture", "version": "1"},
            }
        elif body["method"] == "notifications/initialized":
            return httpx.Response(202, request=request)
        else:
            result = {"tools": [{"name": "bad", "inputSchema": schema}]}
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body.get("id"), "result": result},
            request=request,
        )

    client = McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler))
    with pytest.raises(APIError) as error:
        asyncio.run(client.list_tools())
    assert error.value.code == "MCP_PROTOCOL_ERROR"


def test_input_and_output_schema_are_enforced_before_and_after_call(monkeypatch):
    monkeypatch.setattr(
        "app.modules.runtime.mcp_client._resolve_mcp_url",
        lambda value: (value, "8.8.8.8"),
    )
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        method = body["method"]
        calls.append(method)
        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "schema-fixture", "version": "1"},
            }
            headers = {"Mcp-Session-Id": "schema-session"}
        elif method == "notifications/initialized":
            return httpx.Response(202, request=request)
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "search",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string", "minLength": 1}},
                            "required": ["query"],
                            "additionalProperties": False,
                        },
                        "outputSchema": {
                            "type": "object",
                            "properties": {"answer": {"type": "string"}},
                            "required": ["answer"],
                            "additionalProperties": False,
                        },
                    }
                ]
            }
            headers = {}
        else:
            result = {"content": [], "structuredContent": {"answer": 42}}
            headers = {}
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": body.get("id"), "result": result},
            headers=headers,
            request=request,
        )

    client = McpClient("https://mcp.example.test/rpc", transport=httpx.MockTransport(handler))
    asyncio.run(client.list_tools())
    with pytest.raises(APIError) as missing:
        asyncio.run(client.call_tool("search", {}))
    assert missing.value.code == "MCP_TOOL_INVALID"
    with pytest.raises(APIError) as extra:
        asyncio.run(client.call_tool("search", {"query": "policy", "extra": True}))
    assert extra.value.code == "MCP_TOOL_INVALID"
    with pytest.raises(APIError) as output:
        asyncio.run(client.call_tool("search", {"query": "policy"}))
    assert output.value.code == "MCP_PROTOCOL_ERROR"
    assert calls.count("tools/call") == 1
