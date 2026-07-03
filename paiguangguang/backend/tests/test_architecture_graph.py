from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_architecture_graph_returns_standard_response_envelope() -> None:
    response = client.get("/api/v1/architecture/graphs/system")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert set(body["data"].keys()) == {"nodes", "edges"}


def test_architecture_graph_is_stable_and_shape_complete() -> None:
    first_response = client.get("/api/v1/architecture/graphs/system")
    second_response = client.get("/api/v1/architecture/graphs/system")

    assert first_response.json() == second_response.json()

    nodes = first_response.json()["data"]["nodes"]
    edges = first_response.json()["data"]["edges"]

    assert len(nodes) == 10
    assert len(edges) == 12

    required_node_fields = {"id", "type", "position", "data"}
    required_node_data_fields = {"title", "type", "phase", "description"}
    required_edge_fields = {"id", "source", "target", "type", "animated"}

    for node in nodes:
        assert required_node_fields.issubset(node.keys())
        assert required_node_data_fields.issubset(node["data"].keys())
        assert isinstance(node["position"]["x"], int)
        assert isinstance(node["position"]["y"], int)

    for edge in edges:
        assert required_edge_fields.issubset(edge.keys())

    frontend_node = next(node for node in nodes if node["id"] == "frontend-shell")
    assert frontend_node["data"] == {
        "title": "Frontend App Shell",
        "type": "frontend",
        "phase": "Frontend",
        "description": "Next.js app router shell that hosts the portfolio and agent surfaces.",
    }

    query_node = next(node for node in nodes if node["id"] == "rag-query-service")
    assert query_node["data"]["title"] == "RAG Query Service"
    assert query_node["data"]["phase"] == "Backend"
