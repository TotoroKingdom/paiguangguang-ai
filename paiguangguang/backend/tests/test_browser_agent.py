from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.browser_agent import BrowserAgentService, get_browser_agent_service
from app.tools.browser_search import MockBrowserSearchTool


def test_mock_browser_search_tool_is_deterministic() -> None:
    tool = MockBrowserSearchTool()

    first = tool.search("How does the portfolio architecture use React Flow?", top_k=3)
    second = tool.search("How does the portfolio architecture use React Flow?", top_k=3)

    assert first == second
    assert len(first) == 3
    assert first[0].title == "Portfolio Architecture Overview"
    assert first[0].score >= first[1].score


def test_browser_agent_run_returns_steps_and_final_answer() -> None:
    service = BrowserAgentService(search_tool=MockBrowserSearchTool())
    app.dependency_overrides[get_browser_agent_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agents/browser/run",
            json={
                "prompt": "How does the portfolio use React Flow to explain the system architecture?",
                "top_k": 3,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None

    data = body["data"]
    assert data["prompt"] == "How does the portfolio use React Flow to explain the system architecture?"
    assert data["search_query"] == "portfolio react flow explain system architecture"
    assert isinstance(data["final_answer"], str)
    assert len(data["steps"]) >= 6
    assert data["steps"][0]["kind"] == "plan"
    assert data["steps"][3]["kind"] == "tool_call"
    assert data["steps"][4]["kind"] == "observation"
    assert data["steps"][5]["kind"] == "synthesis"
    assert data["search_results"][0]["title"] == "Portfolio Architecture Overview"
    assert "Supporting references include" in data["final_answer"]
