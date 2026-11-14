import asyncio
import json
import socket
import ssl
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.core.errors import APIError
from app.modules.runtime.mcp_client import McpClient


def _public_addr(ip: str, port: int):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (ip, port))]


class LocalTlsRouteTransport(httpx.AsyncBaseTransport):
    """Route validated public test traffic to the local TLS listener."""

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


def _certificate(hostname: str) -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, hostname)]
    )
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(minutes=10))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(hostname)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return (
        certificate.public_bytes(serialization.Encoding.PEM),
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ),
    )


@contextmanager
def _tls_mcp_server(tmp_path: Path, certificate_pem: bytes, key_pem: bytes):
    certificate_path = tmp_path / "mcp-cert.pem"
    key_path = tmp_path / "mcp-key.pem"
    certificate_path.write_bytes(certificate_pem)
    key_path.write_bytes(key_pem)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate_path, key_path)
    observations: dict[str, object] = {"sni": None, "host": None, "request": None, "error": None}
    ready = threading.Event()
    stop = threading.Event()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    listener.settimeout(2)

    def capture_sni(_ssl_socket, server_name, _ssl_context):
        observations["sni"] = server_name

    context.set_servername_callback(capture_sni)

    def serve() -> None:
        ready.set()
        try:
            for _ in range(3):
                connection, _address = listener.accept()
                with context.wrap_socket(connection, server_side=True) as client:
                    client.settimeout(2)
                    chunks: list[bytes] = []
                    while b"\r\n\r\n" not in b"".join(chunks):
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    raw_request = b"".join(chunks)
                    if observations["request"] is None:
                        observations["request"] = raw_request
                    headers = raw_request.decode("latin-1").split("\r\n")
                    if observations["host"] is None:
                        observations["host"] = next(
                            (line.split(":", 1)[1].strip() for line in headers if line.lower().startswith("host:")),
                            None,
                        )
                    length = int(next(
                        (line.split(":", 1)[1].strip() for line in headers if line.lower().startswith("content-length:")),
                        "0",
                    ))
                    body = raw_request.split(b"\r\n\r\n", 1)[1]
                    while len(body) < length:
                        chunk = client.recv(4096)
                        if not chunk:
                            break
                        body += chunk
                    request = json.loads(body or b"{}")
                    if request.get("method") == "notifications/initialized":
                        client.sendall(b"HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
                        continue
                    if request.get("method") == "initialize":
                        result = {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "tls-local", "version": "1"},
                        }
                    else:
                        result = {"tools": []}
                    payload = json.dumps(
                        {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
                    ).encode()
                    client.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                        + f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
                        + payload
                    )
        except BaseException as error:  # surfaced to the test after the join
            observations["error"] = error
        finally:
            stop.set()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    ready.wait(2)
    try:
        yield listener.getsockname()[1], observations, certificate_pem
    finally:
        listener.close()
        thread.join(3)


def _trusted_context(certificate_pem: bytes) -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cadata=certificate_pem.decode("ascii"))
    context.check_hostname = True
    return context


def test_pinned_mcp_connection_preserves_host_and_sni(monkeypatch, tmp_path):
    certificate_pem, key_pem = _certificate("mcp.example.test")
    with _tls_mcp_server(tmp_path, certificate_pem, key_pem) as (port, observations, trusted_pem):
        endpoint = f"https://mcp.example.test:{port}/rpc"
        original_getaddrinfo = socket.getaddrinfo

        def public_dns(host, requested_port, *args, **kwargs):
            if host == "mcp.example.test":
                return _public_addr("93.184.216.34", requested_port)
            return original_getaddrinfo(host, requested_port, *args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", public_dns)
        monkeypatch.setattr(
            "httpx._transports.default.create_ssl_context",
            lambda **kwargs: _trusted_context(trusted_pem),
        )

        assert asyncio.run(
            McpClient(endpoint, transport=LocalTlsRouteTransport(), timeout=3).list_tools()
        ) == []

    assert observations["error"] is None
    assert observations["sni"] == "mcp.example.test"
    assert observations["host"] == f"mcp.example.test:{port}"
    assert observations["request"]


def test_mcp_tls_rejects_certificate_for_different_hostname(monkeypatch, tmp_path):
    certificate_pem, key_pem = _certificate("wrong.example.test")
    with _tls_mcp_server(tmp_path, certificate_pem, key_pem) as (port, observations, trusted_pem):
        endpoint = f"https://mcp.example.test:{port}/rpc"
        original_getaddrinfo = socket.getaddrinfo

        def public_dns(host, requested_port, *args, **kwargs):
            if host == "mcp.example.test":
                return _public_addr("93.184.216.34", requested_port)
            return original_getaddrinfo(host, requested_port, *args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", public_dns)
        monkeypatch.setattr(
            "httpx._transports.default.create_ssl_context",
            lambda **kwargs: _trusted_context(trusted_pem),
        )

        with pytest.raises(APIError) as error:
            asyncio.run(
                McpClient(endpoint, transport=LocalTlsRouteTransport(), timeout=3).list_tools()
            )

    assert error.value.code == "MCP_UNAVAILABLE"
    assert observations["sni"] == "mcp.example.test"
    assert observations["request"] in (None, b"")
