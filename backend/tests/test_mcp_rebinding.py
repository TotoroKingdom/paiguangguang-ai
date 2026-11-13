import asyncio
import socket

import httpx
import pytest

from app.core.errors import APIError
from app.modules.runtime.mcp_client import McpClient, validate_mcp_url


def test_dns_change_to_private_address_is_rejected_before_request(monkeypatch):
    addresses = iter(["8.8.8.8", "127.0.0.1"])
    monkeypatch.setattr(
        socket, "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(addresses), 443))],
    )
    requests = []
    client = McpClient(
        "https://mcp.example.test/rpc",
        transport=httpx.MockTransport(lambda request: requests.append(request) or httpx.Response(200, json={"result": {}})),
    )
    validate_mcp_url(client.endpoint_url)
    with pytest.raises(APIError) as error:
        asyncio.run(client.list_tools())
    assert error.value.code == "MCP_URL_BLOCKED"
    assert requests == []
