import pytest
from unittest.mock import AsyncMock, MagicMock

from finance_api.services.spents import SpentService
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.spents import SpentCreate
from finance_api.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_spent_creation_validates_category(mocker):
    """Test that creating a spent validates category exists."""
    # Mock repository
    mock_repo = MagicMock(spec=SpentRepository)
    mock_repo.db = AsyncMock()

    # Create service
    service = SpentService(mock_repo)

    # Mock CategoryRepository to return None (category doesn't exist)
    mocker.patch(
        "finance_api.services.spents.CategoryRepository"
    ).return_value.get_by_key = AsyncMock(return_value=None)

    # Should raise ValidationError
    with pytest.raises(ValidationError, match="does not exist"):
        await service.create(
            SpentCreate(
                category="nonexistent_category",
                amount=100.0,
                payment_method="itau",
                payment_owner="joao_lucas",
                location="Test Location",
            )
        )


@pytest.mark.asyncio
async def test_spent_creation_with_valid_category(mocker):
    """Test that creating a spent succeeds with valid category."""
    # Mock repository
    mock_repo = MagicMock(spec=SpentRepository)
    mock_repo.db = AsyncMock()

    # Create service
    service = SpentService(mock_repo)

    # Mock CategoryRepository to return a category (category exists)
    mock_category = MagicMock()
    mock_category.key = "test_cat"
    mocker.patch(
        "finance_api.services.spents.CategoryRepository"
    ).return_value.get_by_key = AsyncMock(return_value=mock_category)

    # Mock create
    mock_created_spent = MagicMock()
    mock_created_spent.category = "test_cat"
    mock_created_spent.amount = 100.0
    mock_repo.create = AsyncMock(return_value=mock_created_spent)

    # Create spent - should succeed
    spent = await service.create(
        SpentCreate(
            category="test_cat",
            amount=100.0,
            payment_method="itau",
            payment_owner="joao_lucas",
            location="Test",
        )
    )

    assert spent.category == "test_cat"
    assert spent.amount == 100.0


@pytest.mark.asyncio
async def test_spent_update_validates_category(mocker):
    """Test that updating a spent validates new category."""
    from finance_api.schemas.spents import SpentUpdate

    mock_repo = MagicMock(spec=SpentRepository)
    mock_repo.db = AsyncMock()

    service = SpentService(mock_repo)

    # Mock CategoryRepository to return None (category doesn't exist)
    mocker.patch(
        "finance_api.services.spents.CategoryRepository"
    ).return_value.get_by_key = AsyncMock(return_value=None)

    # Try to update with invalid category - should raise ValidationError
    with pytest.raises(ValidationError, match="does not exist"):
        await service.update("some-uuid", SpentUpdate(category="nonexistent"))
