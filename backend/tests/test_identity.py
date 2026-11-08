import secrets
import threading

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_user_password
from app.db import SessionLocal
from app.main import app
from app.modules.identity.models import AccountSequence, User
from app.repositories import utc_now


def new_client() -> TestClient:
    return TestClient(app)


def register(
    client: TestClient,
    *,
    password: str = "userpass",
    nickname: str = "",
    key: str | None = None,
):
    return client.post(
        "/api/v1/auth/register",
        json={"password": password, "passwordConfirm": password, "nickname": nickname},
        headers={
            "origin": "http://testserver",
            "idempotency-key": key or secrets.token_urlsafe(24),
        },
    )


def login(client: TestClient, account: str, password: str = "userpass"):
    return client.post(
        "/api/v1/auth/login",
        json={"accountNumber": account, "password": password},
        headers={"origin": "http://testserver"},
    )


def csrf(client: TestClient) -> str:
    token = client.cookies.get(settings.user_csrf_cookie_name)
    assert token
    return token


def headers(client: TestClient) -> dict[str, str]:
    return {"origin": "http://testserver", "x-csrf-token": csrf(client)}


def make_user(
    *,
    account: str,
    role: str = "USER",
    status: str = "ACTIVE",
    password: str = "userpass",
    nickname: str = "",
) -> str:
    with SessionLocal() as session:
        now = utc_now()
        user = User(
            account_number=account,
            password_hash=hash_user_password(password),
            nickname=nickname,
            role=role,
            status=status,
            version=1,
            authz_version=1,
            created_at=now,
            updated_at=now,
            activated_at=now if status == "ACTIVE" else None,
        )
        session.add(user)
        session.commit()
        return user.id


def make_admin(account: str = "1") -> str:
    return make_user(account=account, role="ADMIN", status="ACTIVE", password="adminpass123")


def test_register_starts_at_100_and_creates_pending_user():
    client = new_client()
    first = register(client)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["user"]["accountNumber"] == "100"
    assert body["user"]["status"] == "PENDING"
    assert body["user"]["role"] == "USER"
    assert body["recovery"]["displayMode"] == "ONE_TIME"
    assert body["recovery"]["code"].startswith("PGG-")
    assert body["sessionIssued"] is False

    second = register(client, password="anotherpass")
    assert second.json()["user"]["accountNumber"] == "101"


def test_register_idempotency_reuses_account_without_replaying_code():
    client = new_client()
    key = secrets.token_urlsafe(24)
    first = register(client, key=key)
    second = register(client, key=key)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["user"]["accountNumber"] == second.json()["user"]["accountNumber"]
    assert first.json()["recovery"]["code"]
    assert second.json()["recovery"] is None
    assert second.json()["replayed"] is True

    conflict = register(client, password="differentpass", key=key)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_register_crosses_decimal_boundaries_without_string_sorting():
    client = new_client()
    with SessionLocal() as session:
        sequence = session.get(AccountSequence, "user_account")
        if sequence is None:
            sequence = AccountSequence(
                name="user_account", next_account_number="100", updated_at=utc_now()
            )
            session.add(sequence)
            session.flush()
        sequence.next_account_number = "999"
        session.commit()
    assert register(client).json()["user"]["accountNumber"] == "999"
    assert register(client, password="anotherpass").json()["user"]["accountNumber"] == "1000"
    with SessionLocal() as session:
        sequence = session.get(AccountSequence, "user_account")
        sequence.next_account_number = "9999"
        session.commit()
    assert register(client, password="thirdpass").json()["user"]["accountNumber"] == "9999"
    assert register(client, password="fourthpass").json()["user"]["accountNumber"] == "10000"


def test_concurrent_registration_never_duplicates_accounts():
    results: list[int] = []
    lock = threading.Lock()

    def worker() -> None:
        response = register(new_client(), password="threadpass")
        with lock:
            results.append(response.status_code)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results == [201] * 6
    with SessionLocal() as session:
        accounts = sorted(
            session.scalars(select(User.account_number)).all(), key=int
        )
    assert accounts == ["100", "101", "102", "103", "104", "105"]


def test_password_policy_keeps_six_character_minimum_and_rejects_weak_values():
    client = new_client()
    short = register(client, password="12345")
    assert short.status_code == 422
    assert short.json()["error"]["code"] == "PASSWORD_TOO_SHORT"
    weak = register(client, password="123456")
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "PASSWORD_TOO_WEAK"
    ok = register(client, password="abc123")
    assert ok.status_code == 201
    forbidden = client.post(
        "/api/v1/auth/register",
        json={
            "password": "abc123",
            "passwordConfirm": "abc123",
            "role": "ADMIN",
            "accountNumber": "7",
        },
        headers={"origin": "http://testserver", "idempotency-key": secrets.token_urlsafe(24)},
    )
    assert forbidden.status_code == 422


def test_pending_session_is_restricted_until_admin_activates():
    user = new_client()
    created = register(user).json()
    pending_login = login(user, created["user"]["accountNumber"])
    assert pending_login.status_code == 200
    assert pending_login.json()["session"]["scope"] == "STATUS_ONLY"
    assert user.get("/api/v1/me/status").status_code == 200
    assert user.get("/api/v1/conversations").status_code == 403
    assert user.post(
        "/api/v1/conversations",
        json={"title": "blocked"},
        headers={"origin": "http://testserver"},
    ).status_code == 403

    make_admin()
    admin = new_client()
    assert login(admin, "1", "adminpass123").status_code == 200
    listing = admin.get("/api/v1/admin/users?status=PENDING")
    assert listing.status_code == 200
    item = listing.json()["items"][0]
    activated = admin.post(
        f"/api/v1/admin/users/{item['id']}/activate",
        json={"expectedVersion": item["version"], "reason": "审核通过"},
        headers=headers(admin),
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["user"]["status"] == "ACTIVE"

    fresh = new_client()
    full = login(fresh, created["user"]["accountNumber"])
    assert full.json()["session"]["scope"] == "FULL"
    conversation = fresh.post(
        "/api/v1/conversations",
        json={"title": "真实会话"},
        headers=headers(fresh),
    )
    assert conversation.status_code == 201

    other_browser = new_client()
    assert login(other_browser, created["user"]["accountNumber"]).status_code == 200
    listing = other_browser.get("/api/v1/conversations")
    assert [item["id"] for item in listing.json()["items"]] == [conversation.json()["id"]]


def test_second_user_cannot_read_first_user_conversation():
    first_account = register(new_client()).json()["user"]
    second_account = register(new_client(), password="secondpass").json()["user"]
    with SessionLocal() as session:
        for account in (first_account["accountNumber"], second_account["accountNumber"]):
            row = session.scalar(select(User).where(User.account_number == account))
            row.status = "ACTIVE"
            row.activated_at = utc_now()
        session.commit()
    first = new_client()
    login(first, first_account["accountNumber"])
    conversation = first.post(
        "/api/v1/conversations",
        json={"title": "A 的会话"},
        headers=headers(first),
    ).json()
    second = new_client()
    login(second, second_account["accountNumber"], "secondpass")
    assert second.get(f"/api/v1/conversations/{conversation['id']}").status_code == 404
    assert all(
        item["id"] != conversation["id"]
        for item in second.get("/api/v1/conversations").json()["items"]
    )


def test_disable_revokes_existing_session_immediately():
    account = register(new_client()).json()["user"]
    with SessionLocal() as session:
        row = session.scalar(select(User).where(User.account_number == account["accountNumber"]))
        row.status = "ACTIVE"
        session.commit()
    client = new_client()
    login(client, account["accountNumber"])
    assert client.get("/api/v1/conversations").status_code == 200
    make_admin()
    admin = new_client()
    login(admin, "1", "adminpass123")
    item = admin.get(f"/api/v1/admin/users/{account['id']}").json()
    disabled = admin.post(
        f"/api/v1/admin/users/{account['id']}/disable",
        json={"expectedVersion": item["version"], "reason": "违规"},
        headers=headers(admin),
    )
    assert disabled.status_code == 200
    assert client.get("/api/v1/conversations").status_code == 401


def test_recovery_code_is_one_time_and_revokes_old_sessions():
    account = register(new_client()).json()
    with SessionLocal() as session:
        row = session.scalar(
            select(User).where(User.account_number == account["user"]["accountNumber"])
        )
        row.status = "ACTIVE"
        session.commit()
    client = new_client()
    login(client, account["user"]["accountNumber"])
    assert client.get("/api/v1/conversations").status_code == 200

    recovered = client.post(
        "/api/v1/auth/recovery/complete",
        json={
            "accountNumber": account["user"]["accountNumber"],
            "recoveryCode": account["recovery"]["code"],
            "newPassword": "newpass1",
            "newPasswordConfirm": "newpass1",
        },
        headers={"origin": "http://testserver"},
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["recovery"]["code"] != account["recovery"]["code"]
    assert client.get("/api/v1/conversations").status_code == 401
    assert login(new_client(), account["user"]["accountNumber"], "userpass").status_code == 401
    assert login(new_client(), account["user"]["accountNumber"], "newpass1").status_code == 200
    replay = new_client().post(
        "/api/v1/auth/recovery/complete",
        json={
            "accountNumber": account["user"]["accountNumber"],
            "recoveryCode": account["recovery"]["code"],
            "newPassword": "another1",
            "newPasswordConfirm": "another1",
        },
        headers={"origin": "http://testserver"},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "RECOVERY_INVALID"


def test_anonymous_history_requires_signed_owner_and_explicit_claim():
    guest = new_client()
    conversation = guest.post(
        "/api/v1/conversations",
        json={"title": "匿名历史"},
        headers={"origin": "http://testserver"},
    ).json()
    account = register(new_client()).json()["user"]
    with SessionLocal() as session:
        row = session.scalar(select(User).where(User.account_number == account["accountNumber"]))
        row.status = "ACTIVE"
        session.commit()
    signed_owner = guest.cookies.get(settings.owner_cookie_name)

    attacker = new_client()
    login(attacker, account["accountNumber"])
    forged = attacker.post(
        "/api/v1/me/legacy-conversations/claim",
        json={"conversationIds": [conversation["id"]]},
        headers=headers(attacker),
    )
    assert forged.status_code == 400

    guest_owner = new_client()
    guest_owner.cookies.set(settings.owner_cookie_name, signed_owner, path="/")
    login(guest_owner, account["accountNumber"])
    claimed = guest_owner.post(
        "/api/v1/me/legacy-conversations/claim",
        json={"conversationIds": [conversation["id"]]},
        headers=headers(guest_owner),
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["claimed"] == 1
    assert guest_owner.get(f"/api/v1/conversations/{conversation['id']}").status_code == 200


def test_admin_mutations_require_csrf_and_protect_last_admin():
    admin_id = make_admin()
    admin = new_client()
    login(admin, "1", "adminpass123")
    user = admin.get(f"/api/v1/admin/users/{admin_id}").json()
    no_csrf = admin.post(
        f"/api/v1/admin/users/{admin_id}/disable",
        json={"expectedVersion": user["version"], "reason": "test"},
        headers={"origin": "http://testserver"},
    )
    assert no_csrf.status_code == 403
    protected = admin.post(
        f"/api/v1/admin/users/{admin_id}/disable",
        json={"expectedVersion": user["version"], "reason": "test"},
        headers=headers(admin),
    )
    assert protected.status_code == 409
    assert protected.json()["error"]["code"] == "LAST_ADMIN_PROTECTED"


def test_successful_logins_do_not_consume_failure_limit():
    make_user(account="810")
    for _ in range(6):
        assert login(new_client(), "810").status_code == 200


def test_repeated_login_failures_are_rate_limited():
    make_user(account="811")
    for _ in range(5):
        assert login(new_client(), "811", "wrongpass").status_code == 401
    limited = login(new_client(), "811", "wrongpass")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
