import asyncio
import socket

import httpx
import pytest

from app.core.errors import APIError
from app.modules.runtime.mcp_client import McpClient, validate_mcp_url


def _addr(ip: str, port: int = 443):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (ip, port))]


def test_validate_mcp_url_rejects_non_global_networks(monkeypatch):
    """CGNAT and special-use ranges must be denied like RFC1918 addresses."""

    for address in ("100.64.0.1", "198.18.0.1", "169.254.169.254", "fc00::1", "4000::1"):
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda host, port, *args, _address=address, **kwargs: _addr(_address, port),
        )
        with pytest.raises(APIError) as error:
            validate_mcp_url("https://mcp.example.test/rpc")
        assert error.value.code == "MCP_URL_BLOCKED"


def test_mixed_dns_answers_are_rejected(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda host, port, **kwargs: _addr("8.8.8.8", port) + _addr("127.0.0.1", port),
    )
    with pytest.raises(APIError) as error:
        validate_mcp_url("https://mcp.example.test/rpc")
    assert error.value.code == "MCP_URL_BLOCKED"


def test_client_rechecks_dns_before_connecting_after_registration(monkeypatch):
    """A DNS answer changing after registration must not reach the new private target."""

    answers = iter((_addr("93.184.216.34"), _addr("10.0.0.8")))

    def resolve(host, port, *args, **kwargs):
        try:
            return next(answers)
        except StopIteration:
            return _addr("10.0.0.8", port)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    # The first resolution represents the approved/registered endpoint.
    validate_mcp_url("https://mcp.example.test/rpc")

    original_connect = socket.socket.connect

    def fail_if_connected(_socket, address):
        # asyncio creates a local socket pair for its event loop; only reject
        # the simulated private MCP destination.
        host = address[0] if isinstance(address, tuple) else address
        if host == "10.0.0.8":
            raise AssertionError(f"network connection attempted for {address!r}")
        return original_connect(_socket, address)

    monkeypatch.setattr(socket.socket, "connect", fail_if_connected)
    client = McpClient("https://mcp.example.test/rpc", timeout=0.2)

    with pytest.raises(APIError) as error:
        asyncio.run(client.list_tools())

    assert error.value.code == "MCP_URL_BLOCKED"


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_redirect_is_rejected_without_forwarding_bearer_token(monkeypatch, status):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            status,
            headers={"location": "https://attacker.example.test/collect"},
            request=request,
        )

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *args, **kwargs: _addr("93.184.216.34", port),
    )
    client = McpClient(
        "https://mcp.example.test/rpc",
        token="secret-one",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(APIError) as error:
        asyncio.run(client.list_tools())

    assert error.value.code == "MCP_REDIRECT_BLOCKED"
    assert len(seen) == 1
    assert seen[0].headers["authorization"] == "Bearer secret-one"
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["host"] == "mcp.example.test"
    assert seen[0].extensions["sni_hostname"] == "mcp.example.test"


def test_each_client_keeps_bearer_token_isolated(monkeypatch):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
            request=request,
        )

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *args, **kwargs: _addr("93.184.216.34", port),
    )
    first = McpClient(
        "https://mcp.example.test/rpc",
        token="token-a",
        transport=httpx.MockTransport(handler),
    )
    second = McpClient(
        "https://mcp.example.test/rpc",
        token="token-b",
        transport=httpx.MockTransport(handler),
    )

    async def call_both() -> None:
        await asyncio.gather(first.list_tools(), second.list_tools())

    asyncio.run(call_both())

    assert {request.headers["authorization"] for request in requests} == {
        "Bearer token-a",
        "Bearer token-b",
    }


def test_http_client_does_not_trust_proxy_environment(monkeypatch):
    """MCP connections must not be redirected through ambient proxy variables."""

    captured: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, json, headers, **kwargs):
            request = httpx.Request("POST", url, json=json, headers=headers)
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": 1, "result": {"tools": []}},
                request=request,
            )

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *args, **kwargs: _addr("93.184.216.34", port),
    )

    asyncio.run(McpClient("https://mcp.example.test/rpc").list_tools())

    assert captured["trust_env"] is False
