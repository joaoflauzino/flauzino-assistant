from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from finance_api.core.service_dependencies import get_spending_limit_service
from finance_api.main import app
from finance_api.services.limits import SpendingLimitService

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_category_repo():
    """Fixture for a category repository double used by the limit service."""
    repo = AsyncMock()
    repo.get_by_key.return_value = MagicMock(key="mercado")
    return repo


@pytest.fixture
def mock_limit_repository():
    """Fixture for a mocked SpendingLimitRepository."""
    return AsyncMock()


@pytest.fixture(autouse=True)
def limit_service_override(mock_limit_repository, mock_category_repo):
    """Injects a real SpendingLimitService backed by repository doubles."""
    app.dependency_overrides[get_spending_limit_service] = lambda: SpendingLimitService(
        repo=mock_limit_repository,
        category_repo=mock_category_repo,
    )
    yield
    app.dependency_overrides.pop(get_spending_limit_service, None)


@pytest.fixture
async def test_client():
    """Fixture to create a test client for the FastAPI app."""
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_create_limit_success(test_client, mock_limit_repository):
    """
    Test successful creation of a spending limit.
    """
    payload = {
        "category": "mercado",
        "amount": 2000.00,
    }
    fake_id = uuid4()
    mock_limit_repository.create.return_value = MagicMock(id=fake_id, **payload)

    response = await test_client.post("/limits/", json=payload)

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["id"] == str(fake_id)
    assert response_data["category"] == payload["category"]
    assert response_data["amount"] == payload["amount"]
    mock_limit_repository.create.assert_awaited_once()


async def test_list_limits_success(test_client, mock_limit_repository):
    """
    Test successful listing of spending limit records.
    """
    id1 = uuid4()
    id2 = uuid4()
    mock_return_data = [
        MagicMock(id=id1, category="mercado", amount=2000.00),
        MagicMock(id=id2, category="lazer", amount=500.00),
    ]
    mock_limit_repository.list.return_value = (mock_return_data, 2)

    # Default page=1, size=10 -> skip=0, limit=10
    response = await test_client.get("/limits/")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 2
    assert response_data["items"][0]["id"] == str(id1)
    assert response_data["items"][1]["id"] == str(id2)
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 10
    assert response_data["pages"] == 1
    # Repository list now has 4 params: skip, limit, start_date, end_date
    mock_limit_repository.list.assert_awaited_once_with(0, 10, None, None)


async def test_get_limit_by_id_success(test_client, mock_limit_repository):
    """Test successful retrieval of a spending limit by ID."""
    fake_id = uuid4()
    mock_limit_repository.get_by_id.return_value = MagicMock(
        id=fake_id, category="mercado", amount=2000.00
    )

    response = await test_client.get(f"/limits/{fake_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(fake_id)
    mock_limit_repository.get_by_id.assert_awaited_once_with(fake_id)


async def test_get_limit_by_id_not_found(test_client, mock_limit_repository):
    """Test retrieval of non-existent spending limit returns 404."""
    mock_limit_repository.get_by_id.return_value = None
    fake_id = uuid4()

    response = await test_client.get(f"/limits/{fake_id}")

    assert response.status_code == 404
    mock_limit_repository.get_by_id.assert_awaited_once_with(fake_id)


async def test_update_limit_success(test_client, mock_limit_repository):
    """Test successful update of a spending limit."""
    fake_id = uuid4()
    mock_limit_repository.update.return_value = MagicMock(
        id=fake_id, category="mercado", amount=3000.00
    )

    payload = {"amount": 3000.00}

    response = await test_client.patch(f"/limits/{fake_id}", json=payload)

    assert response.status_code == 200
    assert response.json()["amount"] == 3000.00
    mock_limit_repository.update.assert_awaited_once()


async def test_delete_limit_success(test_client, mock_limit_repository):
    """Test successful deletion of a spending limit."""
    mock_limit_repository.delete.return_value = True
    fake_id = uuid4()

    response = await test_client.delete(f"/limits/{fake_id}")

    assert response.status_code == 204
    mock_limit_repository.delete.assert_awaited_once_with(fake_id)


async def test_create_limit_conflict(test_client, mock_limit_repository):
    """
    Test creation of a spending limit with duplicate category returns 409.
    """
    # Simulate IntegrityError which happens when unique constraint is violated
    mock_limit_repository.create.side_effect = IntegrityError("mock", {}, Exception("mock"))
    payload = {
        "category": "mercado",
        "amount": 2000.00,
    }

    response = await test_client.post("/limits/", json=payload)

    assert response.status_code == 409
    assert response.json() == {
        "message": "Conflict",
        "detail": "Resource already exists.",
    }


async def test_list_limits_pagination(test_client, mock_limit_repository):
    """
    Test listing spending limits with pagination.
    """
    mock_limits = [
        MagicMock(id=uuid4(), category="mercado", amount=2000.00),
        MagicMock(id=uuid4(), category="lazer", amount=500.00),
    ]
    # Simulate pagination returning only the first item, but total is 2
    mock_limit_repository.list.return_value = ([mock_limits[0]], 2)

    # Requesting page=1, size=1 -> skip=0, limit=1
    response = await test_client.get("/limits/?page=1&size=1")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["category"] == "mercado"
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 1
    assert response_data["pages"] == 2
    # Repository list now has 4 params: skip, limit, start_date, end_date
    mock_limit_repository.list.assert_awaited_once_with(0, 1, None, None)
