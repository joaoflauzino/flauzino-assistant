from unittest.mock import AsyncMock, MagicMock

import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.spents import SpentCreate
from finance_api.services.spents import SpentService


@pytest.mark.asyncio
async def test_spent_creation_validates_payment_method(mocker):
    """Test that creating a spent validates payment_method exists."""
    # Mock repository
    mock_repo = MagicMock(spec=SpentRepository)
    mock_repo.db = AsyncMock()

    # Create service
    service = SpentService(mock_repo)

    # Mock CategoryRepository to return a category (category exists)
    mock_category = MagicMock()
    mock_category.key = "test_cat"
    mocker.patch("finance_api.services.spents.CategoryRepository").return_value.get_by_key = (
        AsyncMock(return_value=mock_category)
    )

    # Mock PaymentMethodRepository to return None (payment_method doesn't exist)
    mocker.patch("finance_api.services.spents.PaymentMethodRepository").return_value.get_by_key = (
        AsyncMock(return_value=None)
    )

    # Should raise ValidationError
    with pytest.raises(ValidationError, match="Método de pagamento 'nonexistent_pm' não existe"):
        await service.create(
            SpentCreate(
                category="test_cat",
                amount=100.0,
                item_bought="item1",
                payment_method="nonexistent_pm",
                location="Test Location",
            )
        )


@pytest.mark.asyncio
async def test_spent_update_validates_payment_method(mocker):
    """Test that updating a spent validates new payment_method."""
    from finance_api.schemas.spents import SpentUpdate

    mock_repo = MagicMock(spec=SpentRepository)
    mock_repo.db = AsyncMock()

    service = SpentService(mock_repo)

    # Mock CategoryRepository to return a category (category exists)
    mock_category = MagicMock()
    mock_category.key = "test_cat"
    mocker.patch("finance_api.services.spents.CategoryRepository").return_value.get_by_key = (
        AsyncMock(return_value=mock_category)
    )

    # Mock PaymentMethodRepository to return None (payment_method doesn't exist)
    mocker.patch("finance_api.services.spents.PaymentMethodRepository").return_value.get_by_key = (
        AsyncMock(return_value=None)
    )

    # Try to update with invalid payment_method - should raise ValidationError
    with pytest.raises(ValidationError, match="Método de pagamento 'nonexistent_pm' não existe"):
        await service.update("some-uuid", SpentUpdate(payment_method="nonexistent_pm"))
