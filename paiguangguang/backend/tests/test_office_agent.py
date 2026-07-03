from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.office_agent import OfficeAgentService, get_office_agent_service


def test_office_agent_generate_report_returns_steps_and_structured_output() -> None:
    service = OfficeAgentService()
    app.dependency_overrides[get_office_agent_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agents/office/run",
            json={
                "workflow": "generate_report",
                "prompt": "Create a project status report for the AI portfolio progress update.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None

    data = body["data"]
    assert data["workflow"] == "generate_report"
    assert data["final_output"]["artifact_type"] == "report"
    assert data["final_output"]["title"].endswith("Report")
    assert "Overview" in data["final_output"]["content"]
    assert len(data["steps"]) == 7
    assert data["steps"][2]["kind"] == "tool_call"
    assert data["steps"][4]["data"]["tool"] == "generate_report"
    assert data["steps"][6]["kind"] == "synthesis"


def test_office_agent_write_email_returns_structured_output() -> None:
    service = OfficeAgentService()
    app.dependency_overrides[get_office_agent_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agents/office/run",
            json={
                "workflow": "write_email",
                "prompt": "Draft a status email about the weekly portfolio release milestones.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["workflow"] == "write_email"
    assert data["final_output"]["artifact_type"] == "email"
    assert "stakeholders" == data["final_output"]["metadata"]["recipient"]
    assert "Hi team" in data["final_output"]["content"]
    assert len(data["steps"]) == 7
    assert data["steps"][4]["data"]["tool"] == "write_email"


def test_office_agent_summarize_data_returns_structured_output() -> None:
    service = OfficeAgentService()
    app.dependency_overrides[get_office_agent_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/agents/office/run",
            json={
                "workflow": "summarize_data",
                "prompt": "Summarize the deployment notes and key risks for the portfolio.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["workflow"] == "summarize_data"
    assert data["final_output"]["artifact_type"] == "summary"
    assert len(data["steps"]) == 5
    assert data["steps"][2]["data"]["tool"] == "summarize_data"
    assert data["steps"][-1]["kind"] == "synthesis"


def test_office_agent_rejects_unsupported_workflow_with_enveloped_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/agents/office/run",
        json={
            "workflow": "build_spreadsheet",
            "prompt": "Prepare a spreadsheet and send it to the team.",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "HTTP_ERROR"
    assert "Unsupported office workflow" in body["error"]["message"]
