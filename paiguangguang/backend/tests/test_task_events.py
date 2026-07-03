from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.task import TaskStateData
from app.services.browser_agent import BrowserAgentService, get_browser_agent_service
from app.services.task_service import TaskService, get_task_service
from app.storage.task_store import InMemoryTaskStore
from app.tools.browser_search import MockBrowserSearchTool


def _make_task_service() -> TaskService:
    return TaskService(task_store=InMemoryTaskStore())


def test_task_state_endpoint_returns_current_state() -> None:
    service = _make_task_service()
    task_id = service.start_task(
        task_type="browser_agent",
        title="Browser research workflow",
        metadata={"prompt": "How does the portfolio use React Flow?"},
    )
    service.record_step(
        task_id,
        step={
            "step_id": "step-1",
            "kind": "plan",
            "title": "Create research plan",
            "detail": "Identify the research focus.",
            "data": {"prompt": "How does the portfolio use React Flow?"},
        },
        index=1,
        total=2,
    )
    service.complete_task(
        task_id,
        output={
            "task_id": task_id,
            "final_answer": "Mock final answer",
        },
    )

    app.dependency_overrides[get_task_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/tasks/{task_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = TaskStateData.model_validate(body["data"])
    assert data.task_id == task_id
    assert data.status == "completed"
    assert data.event_count == 4
    assert data.output["final_answer"] == "Mock final answer"
    assert data.latest_event is not None
    assert data.latest_event.event_type == "output"


def test_task_events_endpoint_streams_sse_payload() -> None:
    service = _make_task_service()
    task_id = service.start_task(
        task_type="office_agent",
        title="Office automation workflow",
        metadata={"workflow": "generate_report"},
    )
    service.record_step(
        task_id,
        step={
            "step_id": "step-1",
            "kind": "plan",
            "title": "Define office workflow",
            "detail": "Translate the request into a workflow.",
            "data": {"workflow": "generate_report"},
        },
        index=1,
        total=2,
    )
    service.complete_task(
        task_id,
        output={
            "task_id": task_id,
            "artifact_type": "report",
        },
    )

    app.dependency_overrides[get_task_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.get(f"/api/v1/tasks/{task_id}/events")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: created" in body
    assert "event: status_changed" in body
    assert "event: progress" in body
    assert "event: output" in body
    assert f'"task_id": "{task_id}"' in body


def test_browser_agent_run_returns_task_id_and_publishes_task_state() -> None:
    task_service = _make_task_service()
    browser_service = BrowserAgentService(
        search_tool=MockBrowserSearchTool(),
        task_service=task_service,
    )
    app.dependency_overrides[get_browser_agent_service] = lambda: browser_service
    app.dependency_overrides[get_task_service] = lambda: task_service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agents/browser/run",
            json={
                "prompt": "How does the portfolio use React Flow to explain the system architecture?",
                "top_k": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["task_id"]

        task_response = client.get(f"/api/v1/tasks/{data['task_id']}")
        assert task_response.status_code == 200
        task_state = TaskStateData.model_validate(task_response.json()["data"])
        assert task_state.status == "completed"
        assert task_state.output["prompt"] == "How does the portfolio use React Flow to explain the system architecture?"
        assert task_state.event_count >= 8
    finally:
        app.dependency_overrides.clear()
