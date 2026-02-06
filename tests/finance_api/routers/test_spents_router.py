from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from finance_api.core.database import get_db
from finance_api.main import app
from finance_api.repositories.spents import SpentRepository

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mock_category_repo(mocker):
    """Auto-use fixture that mocks CategoryRepository for all tests."""
    mock_category = MagicMock()
    mock_category.key = "mercado"
    mocker.patch(
        "finance_api.services.spents.CategoryRepository"
    ).return_value.get_by_key = AsyncMock(return_value=mock_category)
    return mock_category


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
    repo.db = AsyncMock()  # Add db attribute for CategoryRepository
    repo.create = AsyncMock()
    repo.list = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


async def test_create_spent_success(test_client, mock_spent_repository, mocker):
    """
    Test successful creation of a spent record.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    payload = {
        "category": "mercado",
        "amount": 150.50,
        "item_bought": "item1",
        "payment_method": "itau",
        "payment_owner": "joao_lucas",
        "location": "Supermarket",
    }
    fake_id = uuid4()
    mock_spent_repository.create.return_value = MagicMock(
        id=fake_id, created_at="2023-01-01T12:00:00", **payload
    )

    # Act
    response = await test_client.post("/spents/", json=payload)

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == str(fake_id)
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

    id1 = uuid4()
    id2 = uuid4()

    mock_return_data = [
        MagicMock(
            id=id1,
            category="mercado",
            amount=100.0,
            item_bought="item1",
            created_at="2023-01-01T12:00:00",
            payment_method="itau",
            payment_owner="joao_lucas",
            location="A",
        ),
        MagicMock(
            id=id2,
            category="lazer",
            amount=50.0,
            item_bought="item2",
            created_at="2023-01-02T12:00:00",
            payment_method="c6",
            payment_owner="lailla",
            location="B",
        ),
    ]
    mock_spent_repository.list.return_value = (mock_return_data, 2)

    # Act
    # Default page=1, size=10 -> skip=0, limit=10
    response = await test_client.get("/spents/")

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
    # Repository list now has 4 params: skip, limit, start_date, end_date
    mock_spent_repository.list.assert_awaited_once_with(0, 10, None, None)

    # Cleanup
    app.dependency_overrides.clear()


async def test_get_spent_by_id_success(test_client, mock_spent_repository, mocker):
    """Test successful retrieval of a spent record by ID."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    fake_id = uuid4()
    mock_spent = MagicMock(
        id=fake_id,
        category="mercado",
        amount=100.0,
        item_bought="item1",
        created_at="2023-01-01T12:00:00",
        payment_method="itau",
        payment_owner="joao_lucas",
        location="A",
    )
    mock_spent_repository.get_by_id.return_value = mock_spent

    # Act
    response = await test_client.get(f"/spents/{fake_id}")

    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == str(fake_id)
    mock_spent_repository.get_by_id.assert_awaited_once_with(fake_id)

    app.dependency_overrides.clear()


async def test_get_spent_by_id_not_found(test_client, mock_spent_repository, mocker):
    """Test retrieval of non-existent spent record returns 404."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    mock_spent_repository.get_by_id.return_value = None
    fake_id = uuid4()

    # Act
    response = await test_client.get(f"/spents/{fake_id}")

    # Assert
    assert response.status_code == 404
    mock_spent_repository.get_by_id.assert_awaited_once_with(fake_id)

    app.dependency_overrides.clear()


async def test_update_spent_success(test_client, mock_spent_repository, mocker):
    """Test successful update of a spent record."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    fake_id = uuid4()
    updated_mock = MagicMock(
        id=fake_id,
        category="lazer",
        amount=200.0,
        item_bought="item1",
        created_at="2023-01-01T12:00:00",
        payment_method="itau",
        payment_owner="joao_lucas",
        location="A",
    )
    mock_spent_repository.update.return_value = updated_mock

    payload = {"amount": 200.0, "category": "lazer"}

    # Act
    response = await test_client.patch(f"/spents/{fake_id}", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["amount"] == 200.0
    mock_spent_repository.update.assert_awaited_once()

    app.dependency_overrides.clear()


async def test_delete_spent_success(test_client, mock_spent_repository, mocker):
    """Test successful deletion of a spent record."""

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    mock_spent_repository.delete.return_value = True
    fake_id = uuid4()

    # Act
    response = await test_client.delete(f"/spents/{fake_id}")

    # Assert
    assert response.status_code == 204
    mock_spent_repository.delete.assert_awaited_once_with(fake_id)

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
        "item_bought": "item1",
        "payment_method": "itau",
        "payment_owner": "joao_lucas",
        "location": "Supermarket",
    }

    # Act
    response = await test_client.post("/spents/", json=payload)

    # Assert
    assert response.status_code == 500
    response_json = response.json()
    assert response_json["message"] == "Internal Server Error"
    assert "Database connection failed" in response_json["detail"]

    # Cleanup
    app.dependency_overrides.clear()


async def test_list_spents_pagination(test_client, mock_spent_repository, mocker):
    """
    Test listing spent records with pagination.
    """

    # Arrange
    async def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db
    mocker.patch(
        "finance_api.routers.spents.SpentRepository", return_value=mock_spent_repository
    )

    id1 = uuid4()
    id2 = uuid4()
    mock_spents = [
        MagicMock(
            id=id1,
            category="mercado",
            amount=100.0,
            item_bought="item1",
            created_at="2023-01-01T12:00:00",
            payment_method="itau",
            payment_owner="joao_lucas",
            location="A",
        ),
        MagicMock(
            id=id2,
            category="lazer",
            amount=50.0,
            item_bought="item2",
            created_at="2023-01-02T12:00:00",
            payment_method="c6",
            payment_owner="lailla",
            location="B",
        ),
    ]
    # Simulate pagination returning only the first item, but total is 2
    mock_spent_repository.list.return_value = ([mock_spents[0]], 2)

    # Act
    # Requesting page=1, size=1 -> skip=0, limit=1
    response = await test_client.get("/spents/?page=1&size=1")

    # Assert
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["items"]) == 1
    assert response_data["items"][0]["id"] == str(id1)
    assert response_data["total"] == 2
    assert response_data["page"] == 1
    assert response_data["size"] == 1
    assert response_data["pages"] == 2
    # Repository list now has 4 params: skip, limit, start_date, end_date
    mock_spent_repository.list.assert_awaited_once_with(0, 1, None, None)

    # Cleanup
    app.dependency_overrides.clear()
