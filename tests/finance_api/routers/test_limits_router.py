from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.main import app
from finance_api.repositories.limits import SpendingLimitRepository
from sqlalchemy.exc import IntegrityError

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
    repo.create = AsyncMock()
    repo.list = AsyncMock()
    repo.get_by_category = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


async def test_create_limit_success(test_client, mock_limit_repository, mocker):
    """
    Test successful creation of a spending limit.
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
    fake_id = uuid4()
    mock_limit_repository.create.return_value = MagicMock(id=fake_id, **payload)

    # Act
    response = await test_client.post("/limits/", json=payload)

    # Assert
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["id"] == str(fake_id)
    assert response_data["category"] == payload["category"]
    assert response_data["amount"] == payload["amount"]
    mock_limit_repository.create.assert_awaited_once()

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

    id1 = uuid4()
    id2 = uuid4()
    mock_return_data = [
        MagicMock(id=id1, category="mercado", amount=2000.00),
        MagicMock(id=id2, category="lazer", amount=500.00),
    ]
    mock_limit_repository.list.return_value = (mock_return_data, 2)

    # Act
    # Default page=1, size=10 -> skip=0, limit=10
    response = await test_client.get("/limits/")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 2
    assert response_data["items"][0]["id"] == str(id1)
    assert response_data["items"][1]["id"] == str(id2)
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 10
    assert response_data["pages"] == 1
    mock_limit_repository.list.assert_awaited_once_with(0, 10)

    # Cleanup
    app.dependency_overrides.clear()


async def test_get_limit_by_id_success(test_client, mock_limit_repository, mocker):
    """Test successful retrieval of a spending limit by ID."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    fake_id = uuid4()
    mock_limit = MagicMock(id=fake_id, category="mercado", amount=2000.00)
    mock_limit_repository.get_by_id.return_value = mock_limit

    # Act
    response = await test_client.get(f"/limits/{fake_id}")

    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == str(fake_id)
    mock_limit_repository.get_by_id.assert_awaited_once_with(fake_id)

    app.dependency_overrides.clear()


async def test_get_limit_by_id_not_found(test_client, mock_limit_repository, mocker):
    """Test retrieval of non-existent spending limit returns 404."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    mock_limit_repository.get_by_id.return_value = None
    fake_id = uuid4()

    # Act
    response = await test_client.get(f"/limits/{fake_id}")

    # Assert
    assert response.status_code == 404
    mock_limit_repository.get_by_id.assert_awaited_once_with(fake_id)

    app.dependency_overrides.clear()


async def test_update_limit_success(test_client, mock_limit_repository, mocker):
    """Test successful update of a spending limit."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    fake_id = uuid4()
    updated_mock = MagicMock(id=fake_id, category="mercado", amount=3000.00)
    mock_limit_repository.update.return_value = updated_mock

    payload = {"amount": 3000.00}

    # Act
    response = await test_client.patch(f"/limits/{fake_id}", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["amount"] == 3000.00
    mock_limit_repository.update.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_delete_limit_success(test_client, mock_limit_repository, mocker):
    """Test successful deletion of a spending limit."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    mock_limit_repository.delete.return_value = True
    fake_id = uuid4()

    # Act
    response = await test_client.delete(f"/limits/{fake_id}")

    # Assert
    assert response.status_code == 204
    mock_limit_repository.delete.assert_awaited_once_with(fake_id)

    app.dependency_overrides.clear()


async def test_create_limit_conflict(test_client, mock_limit_repository, mocker):
    """
    Test creation of a spending limit with duplicate category returns 409.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    # Simulate IntegrityError which happens when unique constraint is violated
    mock_limit_repository.create.side_effect = IntegrityError("mock", "mock", "mock")
    payload = {
        "category": "mercado",
        "amount": 2000.00,
    }

    # Act
    response = await test_client.post("/limits/", json=payload)

    # Assert
    assert response.status_code == 409
    assert response.json() == {
        "message": "Conflict",
        "detail": "Resource already exists.",
    }

    # Cleanup
    app.dependency_overrides.clear()


async def test_list_limits_pagination(test_client, mock_limit_repository, mocker):
    """
    Test listing spending limits with pagination.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.limits.SpendingLimitRepository",
        return_value=mock_limit_repository,
    )

    mock_limits = [
        MagicMock(id=uuid4(), category="mercado", amount=2000.00),
        MagicMock(id=uuid4(), category="lazer", amount=500.00),
    ]
    # Simulate pagination returning only the first item, but total is 2
    mock_limit_repository.list.return_value = ([mock_limits[0]], 2)

    # Act
    # Requesting page=1, size=1 -> skip=0, limit=1
    response = await test_client.get("/limits/?page=1&size=1")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["category"] == "mercado"
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 1
    assert response_data["pages"] == 2
    mock_limit_repository.list.assert_awaited_once_with(0, 1)

    # Cleanup
    app.dependency_overrides.clear()
