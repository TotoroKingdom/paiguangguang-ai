from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Message


def create_conversation(client: TestClient, title: str = "新对话") -> dict:
    response = client.post("/api/v1/conversations", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


def turn_payload(turn_id: str = "turn-1", text: str = "你好") -> dict:
    return {
        "clientTurnId": turn_id,
        "text": text,
        "capability": {"id": "tool-1", "kind": "tool", "name": "网页搜索"},
        "attachments": [{"id": "file-1", "name": "需求.md"}],
        "request": {
            "conversationId": None,
            "text": text,
            "capability": {"id": "tool-1", "kind": "tool", "name": "网页搜索"},
            "fileIds": ["file-1"],
            "simulateFailure": False,
        },
    }


def test_create_turn_is_idempotent_and_persists_snapshots():
    client = TestClient(app)
    conversation = create_conversation(client)
    path = f"/api/v1/conversations/{conversation['id']}/turns"

    first = client.post(path, json=turn_payload())
    second = client.post(path, json=turn_payload())

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    detail = client.get(f"/api/v1/conversations/{conversation['id']}")
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2
    assert detail.json()["messages"][0]["attachments"] == [{"id": "file-1", "name": "需求.md"}]
    assert detail.json()["messages"][0]["request"]["fileIds"] == ["file-1"]
    assert detail.json()["title"] == "你好"


def test_owner_isolation_and_missing_resources_are_404():
    first = TestClient(app)
    second = TestClient(app)
    conversation = create_conversation(first, "只属于第一个浏览器")

    assert second.get(f"/api/v1/conversations/{conversation['id']}").status_code == 404
    assert second.patch(
        f"/api/v1/conversations/{conversation['id']}",
        json={"title": "越权", "version": 1},
    ).status_code == 404
    assert second.delete(f"/api/v1/conversations/{conversation['id']}").status_code == 404
    assert first.get(f"/api/v1/conversations/{conversation['id']}").status_code == 200


def test_list_search_cursor_and_stable_ordering():
    client = TestClient(app)
    created = [create_conversation(client, f"聊天 {index}") for index in range(5)]

    first = client.get("/api/v1/conversations?limit=2")
    assert first.status_code == 200
    assert len(first.json()["items"]) == 2
    assert first.json()["nextCursor"]
    second = client.get(f"/api/v1/conversations?limit=2&cursor={first.json()['nextCursor']}")
    assert second.status_code == 200
    assert {item["id"] for item in first.json()["items"]}.isdisjoint(
        item["id"] for item in second.json()["items"]
    )
    search = client.get("/api/v1/conversations?q=聊天 3")
    assert [item["id"] for item in search.json()["items"]] == [created[3]["id"]]


def test_rename_uses_optimistic_version_and_delete_cascades_messages():
    client = TestClient(app)
    conversation = create_conversation(client)
    client.post(f"/api/v1/conversations/{conversation['id']}/turns", json=turn_payload())
    current = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    renamed = client.patch(
        f"/api/v1/conversations/{conversation['id']}",
        json={"title": "新的名字", "version": current["version"]},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "新的名字"
    assert client.patch(
        f"/api/v1/conversations/{conversation['id']}",
        json={"title": "冲突名字", "version": conversation["version"]},
    ).status_code == 409
    assert client.delete(f"/api/v1/conversations/{conversation['id']}").status_code == 204
    with SessionLocal() as session:
        assert session.query(Message).count() == 0


def test_generating_message_is_recovered_and_can_finish_or_stop():
    client = TestClient(app)
    conversation = create_conversation(client)
    created = client.post(
        f"/api/v1/conversations/{conversation['id']}/turns", json=turn_payload()
    ).json()
    assistant = created["assistantMessage"]
    detail = client.get(f"/api/v1/conversations/{conversation['id']}").json()
    assert detail["messages"][1]["status"] == "stopped"

    completed = client.patch(
        f"/api/v1/conversations/{conversation['id']}/messages/{assistant['id']}",
        json={"content": "", "status": "generating", "steps": []},
    )
    assert completed.status_code == 200
    completed = client.patch(
        f"/api/v1/conversations/{conversation['id']}/messages/{assistant['id']}",
        json={"content": "完成", "status": "complete", "steps": [{"title": "完成", "detail": "已保存"}]},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "complete"
    stopped = client.patch(
        f"/api/v1/conversations/{conversation['id']}/messages/{assistant['id']}",
        json={"content": "停止", "status": "stopped", "steps": []},
    )
    assert stopped.status_code == 409


def test_input_origin_and_content_type_guards():
    client = TestClient(app)
    assert client.post("/api/v1/conversations", content="{}", headers={"content-type": "text/plain"}).status_code == 415
    assert client.post(
        "/api/v1/conversations", json={}, headers={"origin": "https://not-the-site.example"}
    ).status_code == 403
    assert client.get("/api/v1/conversations?limit=0").status_code == 422
    assert client.get("/api/v1/conversations?cursor=bad").status_code == 400


def test_migration_key_is_idempotent_for_one_owner():
    client = TestClient(app)
    first = client.post(
        "/api/v1/conversations", json={"title": "旧聊天", "migrationKey": "legacy:old-id"}
    )
    second = client.post(
        "/api/v1/conversations", json={"title": "不应重复", "migrationKey": "legacy:old-id"}
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]


def test_persisted_rows_survive_a_new_session_and_owner_cookie():
    client = TestClient(app)
    conversation = create_conversation(client, "持久化验证")
    client.post(f"/api/v1/conversations/{conversation['id']}/turns", json=turn_payload())
    client.close()

    restarted = TestClient(app)
    restarted.cookies.update({"paiguangguang_owner": client.cookies.get("paiguangguang_owner")})
    detail = restarted.get(f"/api/v1/conversations/{conversation['id']}")

    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2

