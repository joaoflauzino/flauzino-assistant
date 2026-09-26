import pytest
from fastapi.testclient import TestClient

from graph_api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_graph_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "graph_api"}


def test_graph_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests" in response.text or "python_info" in response.text
