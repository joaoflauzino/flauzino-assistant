from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.categories import Category
from finance_api.models.payment_methods import PaymentMethod
from finance_api.schemas.payment_resolution import ResolvedPaymentTarget
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.services.spents import SpentService
from finance_api.tests.fakes.fake_payment_resolver import FakePaymentResolver

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_category_repo():
    return AsyncMock()


@pytest.fixture
def mock_pm_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_repo, mock_category_repo, mock_pm_repo):
    return SpentService(
        repo=mock_repo,
        category_repo=mock_category_repo,
        pm_repo=mock_pm_repo,
        payment_resolver=FakePaymentResolver(),
        inv_service=AsyncMock(),
    )


def make_payment_method(key: str = "itau_joao") -> PaymentMethod:
    return PaymentMethod(id=uuid4(), key=key, display_name="Itaú", is_credit_card=False)


async def test_update_rejects_unknown_category(service, mock_repo, mock_category_repo):
    mock_category_repo.get_by_key.return_value = None

    with pytest.raises(ValidationError, match="não existe"):
        await service.update(uuid4(), SpentUpdate(category="inexistente"))

    mock_repo.update.assert_not_awaited()


async def test_update_rejects_unknown_payment_method(service, mock_repo, mock_pm_repo):
    mock_pm_repo.get_by_key.return_value = None

    with pytest.raises(ValidationError, match="não existe"):
        await service.update(uuid4(), SpentUpdate(payment_method="cartao_fantasma"))

    mock_repo.update.assert_not_awaited()


async def test_create_rejects_missing_payment_method(
    service,
    mock_repo,
    mock_category_repo,
    mock_pm_repo,
):
    mock_category_repo.get_by_key.return_value = Category(
        id=uuid4(), key="mercado", display_name="Mercado"
    )
    spent = SpentCreate(
        category="mercado",
        amount=20.0,
        item_bought="Pão",
        payment_method=None,
    )

    with pytest.raises(ValidationError, match="pagamento é obrigatório"):
        await service.create(spent)

    mock_pm_repo.get_by_key.assert_not_awaited()
    mock_repo.create.assert_not_awaited()


async def test_update_normalizes_category_key(service, mock_repo, mock_category_repo):
    spent_id = uuid4()
    mock_category_repo.get_by_key.return_value = Category(
        id=uuid4(), key="mercado", display_name="Mercado"
    )
    mock_repo.get_by_id.return_value = MagicMock(id=spent_id)
    mock_repo.update.return_value = MagicMock(id=spent_id)

    update_data = SpentUpdate(category="  Mercado ", amount=50.0)
    await service.update(spent_id, update_data)

    mock_category_repo.get_by_key.assert_awaited_once_with("mercado")
    mock_repo.update.assert_awaited_once_with(spent_id, update_data)
    assert update_data.category == "mercado"


async def test_update_resolves_payment_target(service, mock_repo, mock_pm_repo):
    spent_id = uuid4()
    account_id = uuid4()
    service.payment_resolver = FakePaymentResolver(
        {
            "pix_joao": ResolvedPaymentTarget(
                account_id=account_id, credit_card_id=None, payment_type="PIX"
            )
        }
    )
    mock_pm_repo.get_by_key.return_value = make_payment_method("pix_joao")
    mock_repo.get_by_id.return_value = MagicMock(id=spent_id)
    mock_repo.update.return_value = MagicMock(id=spent_id)

    update_data = SpentUpdate(payment_method="pix_joao")
    await service.update(spent_id, update_data)

    assert update_data.payment_method == "pix_joao"
    assert update_data.account_id == account_id
    assert update_data.payment_type == "PIX"


async def test_update_raises_when_spent_is_missing(service, mock_repo):
    spent_id = uuid4()
    mock_repo.get_by_id.return_value = None

    with pytest.raises(EntityNotFoundError, match="não encontrado"):
        await service.update(spent_id, SpentUpdate(amount=10.0))

    mock_repo.update.assert_not_awaited()


async def test_update_raises_when_repository_update_returns_none(service, mock_repo):
    spent_id = uuid4()
    mock_repo.get_by_id.return_value = MagicMock(id=spent_id)
    mock_repo.update.return_value = None

    with pytest.raises(EntityNotFoundError, match="não encontrado"):
        await service.update(spent_id, SpentUpdate(amount=10.0))
