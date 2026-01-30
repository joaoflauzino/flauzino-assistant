from unittest.mock import AsyncMock, MagicMock

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.main import app
from finance_api.repositories.limits import SpendingLimitRepository

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
def mock_limit_repository():
    """Fixture for a mocked SpendingLimitRepository."""
    repo = MagicMock(spec=SpendingLimitRepository)
    repo.create_or_update = AsyncMock()
    repo.list = AsyncMock()
    repo.get_by_category = AsyncMock()
    return repo


async def test_create_or_update_limit_success(
    test_client, mock_limit_repository, mocker
):
    """
    Test successful creation or update of a spending limit.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    payload = {
        "category": "mercado",
        "amount": 2000.00,
    }
    mock_limit_repository.create_or_update.return_value = MagicMock(id=1, **payload)

    # Act
    response = await test_client.post("/limits/", json=payload)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == 1
    assert response_data["category"] == payload["category"]
    assert response_data["amount"] == payload["amount"]
    mock_limit_repository.create_or_update.assert_awaited_once()

    # Cleanup
    app.dependency_overrides.clear()


async def test_list_limits_success(test_client, mock_limit_repository, mocker):
    """
    Test successful listing of spending limits.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    mock_return_data = [
        MagicMock(id=1, category="mercado", amount=2000.00),
        MagicMock(id=2, category="lazer", amount=500.00),
    ]
    mock_limit_repository.list.return_value = mock_return_data

    # Act
    response = await test_client.get("/limits/")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 2
    assert response_data[0]["id"] == 1
    assert response_data[1]["id"] == 2
    mock_limit_repository.list.assert_awaited_once()

    # Cleanup
    app.dependency_overrides.clear()


async def test_create_limit_repository_error(
    test_client, mock_limit_repository, mocker
):
    """
    Test handling of a 500 error when the repository fails.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    mock_limit_repository.create_or_update.side_effect = Exception("Database error")
    payload = {
        "category": "mercado",
        "amount": 2000.00,
    }

    # Act
    response = await test_client.post("/limits/", json=payload)

    # Assert
    assert response.status_code == 500
    # Verifying specific error format from global exception handler
    assert response.json() == {"detail": "Internal Server Error: Database error"}

    # Cleanup
    app.dependency_overrides.clear()
