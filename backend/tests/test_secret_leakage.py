import logging
import secrets

from fastapi.testclient import TestClient

from app.main import app


def new_client() -> TestClient:
    return TestClient(app)


def register(client: TestClient, *, password: str = "userpass"):
    return client.post(
        "/api/v1/auth/register",
        json={"password": password, "passwordConfirm": password, "nickname": ""},
        headers={
            "origin": "http://testserver",
            "idempotency-key": secrets.token_urlsafe(24),
        },
    )


def test_sensitive_api_responses_disable_browser_and_proxy_caching():
    client = new_client()
    registered = register(client)
    assert registered.status_code == 201, registered.text

    logged_in = client.post(
        "/api/v1/auth/login",
        json={
            "accountNumber": registered.json()["user"]["accountNumber"],
            "password": "userpass",
        },
        headers={"origin": "http://testserver"},
    )
    assert logged_in.status_code == 200, logged_in.text
    session = client.get("/api/v1/auth/session")
    assert session.status_code == 200, session.text

    for response in (registered, logged_in, session):
        assert response.headers["cache-control"] == "no-store, max-age=0"
        assert response.headers["pragma"] == "no-cache"
        assert response.headers["expires"] == "0"


def test_secrets_do_not_appear_in_auth_errors_cookies_or_logs(caplog):
    client = new_client()
    password = "safe-pass-9381"
    unknown_password = "wrong-pass-5274"
    unknown_recovery = "PGG-UNKNOWN-SECRET-9381"

    with caplog.at_level(logging.DEBUG):
        registered = register(client, password=password)
        assert registered.status_code == 201, registered.text
        recovery = registered.json()["recovery"]["code"]
        account = registered.json()["user"]["accountNumber"]

        failed_login = client.post(
            "/api/v1/auth/login",
            json={"accountNumber": account, "password": unknown_password},
            headers={"origin": "http://testserver"},
        )
        assert failed_login.status_code == 401

        failed_recovery = client.post(
            "/api/v1/auth/recovery/complete",
            json={
                "accountNumber": account,
                "recoveryCode": unknown_recovery,
                "newPassword": "newpass1",
                "newPasswordConfirm": "newpass1",
            },
            headers={"origin": "http://testserver"},
        )
        assert failed_recovery.status_code == 401

    error_responses = failed_login.text + failed_recovery.text
    assert recovery not in error_responses
    assert password not in error_responses
    assert unknown_password not in error_responses
    assert unknown_recovery not in error_responses

    cookies = client.cookies
    assert all(recovery not in (cookies.get(name) or "") for name in cookies.keys())

    assert recovery not in caplog.text
    assert password not in caplog.text
    assert unknown_password not in caplog.text
    assert unknown_recovery not in caplog.text
