from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.services.spents import SpentService
from finance_api.tests.fakes.fake_payment_resolver import FakePaymentResolver


def build_service(
    repo: AsyncMock,
    category_repo: AsyncMock,
    pm_repo: AsyncMock,
    resolver: FakePaymentResolver | None = None,
) -> SpentService:
    return SpentService(
        repo=repo,
        category_repo=category_repo,
        pm_repo=pm_repo,
        payment_resolver=resolver or FakePaymentResolver(),
        inv_service=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_spent_creation_validates_payment_method():
    """Test that creating a spent validates payment_method exists."""
    mock_repo = AsyncMock()
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = MagicMock(key="test_cat")

    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = None

    service = build_service(mock_repo, category_repo, pm_repo)

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

    mock_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_spent_update_validates_payment_method():
    """Test that updating a spent validates new payment_method."""
    mock_repo = AsyncMock()
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = MagicMock(key="test_cat")

    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = None

    service = build_service(mock_repo, category_repo, pm_repo)

    with pytest.raises(ValidationError, match="Método de pagamento 'nonexistent_pm' não existe"):
        await service.update(uuid4(), SpentUpdate(payment_method="nonexistent_pm"))

    mock_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_spent_creation_preserves_user_payment_type():
    """Test that creating a spent preserves explicitly provided payment_type like PIX."""
    account_id = uuid4()

    mock_repo = AsyncMock()
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = MagicMock(key="mercado")

    pm = PaymentMethod(
        id=account_id,
        key="nubank_joao",
        display_name="Nubank",
        is_credit_card=False,
    )
    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = pm

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
    mock_repo.create.return_value = spent_obj

    service = build_service(
        mock_repo,
        category_repo,
        pm_repo,
        resolver=FakePaymentResolver(
            {
                "nubank_joao": ResolvedPaymentTarget(
                    account_id=account_id,
                    credit_card_id=None,
                    payment_type="PIX",
                )
            }
        ),
    )

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
