import asyncio

import pytest
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.main import app, request_guard
from test_platform import headers, login, make_user, new_client


async def _post_raw(
    *, headers: list[tuple[bytes, bytes]], body: bytes, path: str = "/api/v1/auth/login",
    chunk_size: int | None = None,
) -> int:
    sent: list[dict] = []
    offset = 0

    async def receive() -> dict:
        nonlocal offset
        if offset >= len(body):
            return {"type": "http.disconnect"}
        chunk = body[offset:offset + (chunk_size or len(body))]
        offset += len(chunk)
        return {"type": "http.request", "body": chunk, "more_body": offset < len(body)}

    async def send(message: dict) -> None:
        sent.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("test", 1234),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


@pytest.mark.parametrize("chunk_size", [None, 16384])
def test_body_without_content_length_is_limited(chunk_size):
    body = b'{"accountNumber":"' + (b"a" * (300 * 1024)) + b'","password":"x"}'
    status = asyncio.run(
        _post_raw(headers=[(b"content-type", b"application/json")], body=body, chunk_size=chunk_size)
    )
    assert status == 413


def test_forged_content_length_does_not_bypass_body_limit():
    body = b'{"accountNumber":"' + (b"a" * (300 * 1024)) + b'","password":"x"}'
    status = asyncio.run(
        _post_raw(
            headers=[(b"content-type", b"application/json"), (b"content-length", b"1")],
            body=body,
        )
    )
    assert status == 413


@pytest.mark.parametrize("content_length", [None, b"1"])
@pytest.mark.parametrize("chunk_size", [None, 16384])
def test_upload_body_limit_uses_actual_bytes(content_length: bytes | None, chunk_size):
    body = b"x" * (5 * 1024 * 1024 + 64 * 1024 + 1)
    headers = [(b"content-type", b"multipart/form-data; boundary=ignored")]
    if content_length is not None:
        headers.append((b"content-length", content_length))
    status = asyncio.run(
        _post_raw(headers=headers, body=body, path="/api/v1/me/files", chunk_size=chunk_size)
    )
    assert status == 413


def test_replayed_body_does_not_fake_stream_disconnect():
    async def scenario() -> list[dict]:
        release = asyncio.Event()
        first_sent = asyncio.Event()
        disconnect = asyncio.Event()
        received_body = False
        sent: list[dict] = []

        async def receive() -> dict:
            nonlocal received_body
            if not received_body:
                received_body = True
                return {"type": "http.request", "body": b"{}", "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict) -> None:
            sent.append(message)
            if message["type"] == "http.response.body" and message.get("body") == b"first":
                first_sent.set()

        async def call_next(_: Request) -> StreamingResponse:
            async def stream():
                yield b"first"
                await release.wait()
                yield b"second"

            return StreamingResponse(stream(), media_type="text/event-stream")

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/auth/login",
            "raw_path": b"/api/v1/auth/login",
            "query_string": b"",
            "headers": [(b"content-type", b"application/json")],
            "client": ("test", 1234),
            "server": ("testserver", 80),
        }
        request = Request(scope, receive)

        async def run() -> None:
            response = await request_guard(request, call_next)
            await response(scope, request.receive, send)

        task = asyncio.create_task(run())
        await first_sent.wait()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        disconnect.set()
        await task
        return sent

    sent = asyncio.run(scenario())
    assert any(message.get("body") == b"second" for message in sent)


def test_text_upload_above_global_json_limit_is_allowed():
    make_user("901")
    client = new_client()
    login(client, "901")

    payload = ("a" * (300 * 1024)).encode("utf-8")
    response = client.post(
        "/api/v1/me/files",
        files={"file": ("large-notes.txt", payload, "text/plain")},
        headers=headers(client),
    )

    assert response.status_code == 201, response.text
    assert response.json()["sizeBytes"] == len(payload)


def test_upload_over_five_mib_is_rejected():
    make_user("902")
    client = new_client()
    login(client, "902")

    payload = b"x" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/me/files",
        files={"file": ("too-large.txt", payload, "text/plain")},
        headers=headers(client),
    )

    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_binary_file_type_is_rejected():
    make_user("903")
    client = new_client()
    login(client, "903")

    response = client.post(
        "/api/v1/me/files",
        files={"file": ("payload.exe", b"MZ\x00\x01", "application/octet-stream")},
        headers=headers(client),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "FILE_TYPE_UNSUPPORTED"


def test_markdown_generic_mime_is_allowed_after_text_validation():
    make_user("905")
    client = new_client()
    login(client, "905")

    response = client.post(
        "/api/v1/me/files",
        files={"file": ("notes.md", b"# valid markdown\n", "application/octet-stream")},
        headers=headers(client),
    )

    assert response.status_code == 201, response.text


def test_invalid_utf8_text_is_rejected():
    make_user("904")
    client = new_client()
    login(client, "904")

    response = client.post(
        "/api/v1/me/files",
        files={"file": ("broken.txt", b"valid prefix\xff\xfe", "text/plain")},
        headers=headers(client),
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "FILE_CONTENT_INVALID"
