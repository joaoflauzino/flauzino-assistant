import pytest
from fastapi.testclient import TestClient

from graph_api.core.exceptions import GraphGenerationError
from graph_api.main import app
from graph_api.schemas.graphs import ChartMode
from graph_api.services.chart_strategies import (
    BalanceStackedBarChartStrategy,
    ExpensePieChartStrategy,
    LimitsBarChartStrategy,
)
from graph_api.services.graph_service import (
    GraphRendererService,
    get_graph_renderer_service,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_generate_bar_graph_success(client: TestClient) -> None:
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


def test_generate_limits_bar_graph_success(client: TestClient) -> None:
    payload = {
        "balances": [
            {
                "category_display_name": "Mercado",
                "limit": 1000.0,
                "spent": 450.0,
                "available": 550.0,
            },
        ],
        "mode": "limites",
    }
    response = client.post("/graphs/bar", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert len(data["image_base64"]) > 0


def test_generate_pie_graph_success(client: TestClient) -> None:
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


def test_generate_bar_graph_error_handling(client: TestClient, mocker) -> None:
    mock_renderer = mocker.MagicMock(spec=GraphRendererService)
    mock_renderer.render = mocker.AsyncMock(
        side_effect=GraphGenerationError("Falha na renderização")
    )
    app.dependency_overrides[get_graph_renderer_service] = lambda: mock_renderer
    try:
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
    finally:
        app.dependency_overrides.clear()


def test_chart_strategies_build_figures_independently() -> None:
    balances = [
        {"category_display_name": "Mercado", "limit": 1000.0, "spent": 450.0, "available": 550.0},
        {"category_display_name": "Lazer", "limit": 500.0, "spent": 0.0, "available": 500.0},
    ]

    limits_fig = LimitsBarChartStrategy().build_figure(balances, "Meus Limites")
    assert limits_fig.layout.title.text == "Meus Limites"
    assert len(limits_fig.data) == 1

    saldo_fig = BalanceStackedBarChartStrategy().build_figure(balances, "Meu Saldo")
    assert saldo_fig.layout.title.text == "Meu Saldo"
    assert saldo_fig.layout.barmode == "stack"
    assert len(saldo_fig.data) == 2

    pie_fig = ExpensePieChartStrategy().build_figure(balances, "Pizza")
    assert pie_fig.layout.title.text == "Pizza"
    assert len(pie_fig.data) == 1

    empty_pie_fig = ExpensePieChartStrategy().build_figure(
        [{"category_display_name": "Lazer", "limit": 500.0, "spent": 0.0, "available": 500.0}],
        "Sem Gastos",
    )
    assert empty_pie_fig.layout.title.text == "Nenhum gasto registrado"


@pytest.mark.asyncio
async def test_graph_renderer_service_missing_strategy_raises() -> None:
    renderer = GraphRendererService(strategies={ChartMode.LIMITES: LimitsBarChartStrategy()})
    with pytest.raises(GraphGenerationError, match="Unsupported chart mode"):
        await renderer.render(balances=[], title="Teste", mode=ChartMode.PIE)
