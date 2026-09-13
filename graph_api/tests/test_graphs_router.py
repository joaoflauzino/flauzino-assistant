import pytest
from fastapi.testclient import TestClient

from graph_api.core.exceptions import GraphGenerationError
from graph_api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_generate_bar_graph_success(client):
    payload = {
        "balances": [
            {
                "category_display_name": "Mercado",
                "limit": 1000.0,
                "spent": 450.0,
                "available": 550.0,
            },
            {"category_display_name": "Lazer", "limit": 500.0, "spent": 120.0, "available": 380.0},
        ],
        "mode": "saldo",
    }
    response = client.post("/graphs/bar", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert isinstance(data["image_base64"], str)
    assert len(data["image_base64"]) > 0


def test_generate_pie_graph_success(client):
    payload = {
        "balances": [
            {
                "category_display_name": "Mercado",
                "limit": 1000.0,
                "spent": 450.0,
                "available": 550.0,
            },
            {"category_display_name": "Lazer", "limit": 500.0, "spent": 120.0, "available": 380.0},
        ],
        "title": "Gastos do Mês",
    }
    response = client.post("/graphs/pie", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert isinstance(data["image_base64"], str)
    assert len(data["image_base64"]) > 0


def test_generate_bar_graph_error_handling(client, mocker):
    mocker.patch(
        "graph_api.routers.graphs.graph_service.generate_balance_bar_chart",
        side_effect=GraphGenerationError("Falha na renderização"),
    )
    payload = {
        "balances": [
            {
                "category_display_name": "Mercado",
                "limit": 1000.0,
                "spent": 450.0,
                "available": 550.0,
            }
        ],
        "mode": "saldo",
    }
    response = client.post("/graphs/bar", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert data["message"] == "Graph Generation Error"
    assert "Falha na renderização" in data["detail"]
