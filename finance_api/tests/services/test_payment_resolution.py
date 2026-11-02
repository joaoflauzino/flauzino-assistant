from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from finance_api.models.accounts import Account
from finance_api.models.credit_cards import CreditCard
from finance_api.repositories.accounts import AccountRepositoryProtocol
from finance_api.repositories.credit_cards import CreditCardRepositoryProtocol
from finance_api.services.payment_resolution import PaymentResolutionService


@pytest.mark.asyncio
async def test_resolve_empty_key():
    service = PaymentResolutionService()
    res = await service.resolve(None)
    assert res.account_id is None
    assert res.credit_card_id is None
    assert res.payment_type == "DEBIT"


@pytest.mark.asyncio
async def test_resolve_empty_key_with_credit_hint():
    service = PaymentResolutionService()
    res = await service.resolve("", is_credit_card_hint=True)
    assert res.payment_type == "CREDIT"


@pytest.mark.asyncio
async def test_resolve_matches_credit_card():
    card_repo = AsyncMock(spec=CreditCardRepositoryProtocol)
    account_repo = AsyncMock(spec=AccountRepositoryProtocol)

    card_id = uuid4()
    acc_id = uuid4()
    card = CreditCard(id=card_id, key="c6_card", name="C6 Carbon", account_id=acc_id)
    card_repo.get_by_key.return_value = card

    service = PaymentResolutionService(card_repo=card_repo, account_repo=account_repo)
    res = await service.resolve("c6_card")

    assert res.credit_card_id == card_id
    assert res.account_id == acc_id
    assert res.payment_type == "CREDIT"


@pytest.mark.asyncio
async def test_resolve_matches_account():
    card_repo = AsyncMock(spec=CreditCardRepositoryProtocol)
    account_repo = AsyncMock(spec=AccountRepositoryProtocol)

    card_repo.get_by_key.return_value = None

    acc_id = uuid4()
    account = Account(id=acc_id, key="itau_joao", name="Itaú CC")
    account_repo.get_by_key.return_value = account

    service = PaymentResolutionService(card_repo=card_repo, account_repo=account_repo)
    res = await service.resolve("itau_joao", requested_payment_type="PIX")

    assert res.credit_card_id is None
    assert res.account_id == acc_id
    assert res.payment_type == "PIX"


@pytest.mark.asyncio
async def test_resolve_fallback_when_not_found():
    card_repo = AsyncMock(spec=CreditCardRepositoryProtocol)
    account_repo = AsyncMock(spec=AccountRepositoryProtocol)

    card_repo.get_by_key.return_value = None
    account_repo.get_by_key.return_value = None

    service = PaymentResolutionService(card_repo=card_repo, account_repo=account_repo)
    res = await service.resolve("desconhecido")

    assert res.credit_card_id is None
    assert res.account_id is None
    assert res.payment_type == "DEBIT"


@pytest.mark.asyncio
async def test_resolve_account_with_invalid_payment_type_defaults_to_debit():
    card_repo = AsyncMock(spec=CreditCardRepositoryProtocol)
    account_repo = AsyncMock(spec=AccountRepositoryProtocol)
    card_repo.get_by_key.return_value = None
    account_repo.get_by_key.return_value = Account(
        id=uuid4(),
        key="itau_joao",
        name="Itaú CC",
    )

    service = PaymentResolutionService(card_repo=card_repo, account_repo=account_repo)
    res = await service.resolve("itau_joao", requested_payment_type="BOLETO")

    assert res.payment_type == "DEBIT"


@pytest.mark.asyncio
async def test_resolve_without_repositories_falls_back_without_lookup():
    service = PaymentResolutionService()

    res = await service.resolve("c6_card", requested_payment_type="PIX")

    assert res.account_id is None
    assert res.credit_card_id is None
    assert res.payment_type == "PIX"


@pytest.mark.asyncio
async def test_resolve_propagates_repository_errors():
    card_repo = AsyncMock(spec=CreditCardRepositoryProtocol)
    card_repo.get_by_key.side_effect = RuntimeError("db down")

    service = PaymentResolutionService(card_repo=card_repo)

    with pytest.raises(RuntimeError, match="db down"):
        await service.resolve("c6_card")


@pytest.mark.asyncio
async def test_resolve_normalizes_key_before_lookup():
    card_repo = AsyncMock(spec=CreditCardRepositoryProtocol)
    card = CreditCard(id=uuid4(), key="c6_card", name="C6 Carbon", account_id=uuid4())
    card_repo.get_by_key.return_value = card

    service = PaymentResolutionService(card_repo=card_repo)
    await service.resolve("  C6_CARD  ")

    card_repo.get_by_key.assert_awaited_once_with("c6_card")
