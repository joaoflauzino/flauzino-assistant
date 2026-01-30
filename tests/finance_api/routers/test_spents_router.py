from unittest.mock import AsyncMock, MagicMock

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.main import app
from finance_api.repositories.spents import SpentRepository

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_client():
    """Fixture to create a test client for the FastAPI app."""
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture
def mock_spent_repository():
    """Fixture for a mocked SpentRepository."""
    repo = MagicMock(spec=SpentRepository)
    repo.create = AsyncMock()
    repo.list = AsyncMock()
    return repo


async def test_create_spent_success(test_client, mock_spent_repository, mocker):
    """
    Test successful creation of a spent record.
    """

    # Arrange
    # Mock the dependency get_db to return our mocked repository
    async def override_get_db():
        yield MagicMock()  # Mock the session object itself

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    payload = {
        "category": "mercado",
        "amount": 150.50,
        "payment_method": "itau",
        "payment_owner": "joao_lucas",
        "location": "Supermarket",
    }
    mock_spent_repository.create.return_value = MagicMock(
        id=1, created_at="2023-01-01T12:00:00", **payload
    )

    # Act
    response = await test_client.post("/spents/", json=payload)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == 1
    assert response_data["category"] == payload["category"]
    assert response_data["amount"] == payload["amount"]
    mock_spent_repository.create.assert_awaited_once()

    # Cleanup dependency override
    app.dependency_overrides.clear()


async def test_list_spents_success(test_client, mock_spent_repository, mocker):
    """
    Test successful listing of spent records.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    mock_return_data = [
        MagicMock(
            id=1,
            category="mercado",
            amount=100.0,
            created_at="2023-01-01T12:00:00",
            payment_method="itau",
            payment_owner="joao_lucas",
            location="A",
        ),
        MagicMock(
            id=2,
            category="lazer",
            amount=50.0,
            created_at="2023-01-02T12:00:00",
            payment_method="c6",
            payment_owner="lailla",
            location="B",
        ),
    ]
    mock_spent_repository.list.return_value = mock_return_data

    # Act
    response = await test_client.get("/spents/")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["id"] == 1
    assert response_data[1]["id"] == 2
    mock_spent_repository.list.assert_awaited_once_with(0, 100)

    # Cleanup
    app.dependency_overrides.clear()


async def test_create_spent_repository_error(
    test_client, mock_spent_repository, mocker
):
    """
    Test handling of a 500 error when the repository fails.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    mock_spent_repository.create.side_effect = Exception("Database connection failed")
    payload = {
        "category": "mercado",
        "amount": 150.50,
        "payment_method": "itau",
        "payment_owner": "joao_lucas",
        "location": "Supermarket",
    }

    # Act
    response = await test_client.post("/spents/", json=payload)

    # Assert
    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal Server Error: Database connection failed"
    }

    # Cleanup
    app.dependency_overrides.clear()
