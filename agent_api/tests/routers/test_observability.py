import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from agent_api.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_agent_health_check(test_client):
    response = await test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agent_api"}


async def test_agent_metrics_endpoint(test_client):
    response = await test_client.get("/metrics")
    assert response.status_code == 200
    assert (
        "http_requests" in response.text
        or "python_info" in response.text
        or "flauzino_" in response.text
    )
