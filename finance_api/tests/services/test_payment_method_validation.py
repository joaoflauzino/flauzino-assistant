from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.models.accounts import Account
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
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


@pytest.mark.asyncio
async def test_spent_creation_preserves_user_payment_type(mocker):
    """Test that creating a spent preserves explicitly provided payment_type like PIX."""
    mock_repo = MagicMock(spec=SpentRepository)
    mock_repo.db = AsyncMock()

    account_id = uuid4()
    fake_acc = Account(
        id=account_id,
        key="nubank_joao",
        name="Nubank",
        bank="nubank",
        owner="joao",
        type="CHECKING",
    )

    res_card = MagicMock()
    res_card.scalar_one_or_none.return_value = None
    res_acc = MagicMock()
    res_acc.scalar_one_or_none.return_value = fake_acc
    mock_repo.db.execute.side_effect = [res_card, res_acc]

    service = SpentService(mock_repo)

    mock_category = MagicMock()
    mock_category.key = "mercado"
    mocker.patch("finance_api.services.spents.CategoryRepository").return_value.get_by_key = (
        AsyncMock(return_value=mock_category)
    )

    pm = PaymentMethod(
        id=account_id,
        key="nubank_joao",
        display_name="Nubank",
        is_credit_card=False,
    )
    mocker.patch("finance_api.services.spents.PaymentMethodRepository").return_value.get_by_key = (
        AsyncMock(return_value=pm)
    )

    spent_obj = Spent(
        id=uuid4(),
        category="mercado",
        amount=50.0,
        item_bought="Frutas",
        payment_method="nubank_joao",
        payment_type="PIX",
        account_id=account_id,
        location="Feira",
    )
    mock_repo.create = AsyncMock(return_value=spent_obj)

    create_dto = SpentCreate(
        category="mercado",
        amount=50.0,
        item_bought="Frutas",
        payment_method="nubank_joao",
        payment_type="PIX",
        location="Feira",
    )

    result = await service.create(create_dto)
    assert result.payment_type == "PIX"
    assert create_dto.payment_type == "PIX"
    assert create_dto.account_id == account_id
