from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import ValidationError
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.services.spents import SpentService
from finance_api.tests.fakes.fake_payment_resolver import FakePaymentResolver


def build_service(
    repo: AsyncMock,
    category_repo: AsyncMock,
    pm_repo: AsyncMock | None = None,
) -> SpentService:
    return SpentService(
        repo=repo,
        category_repo=category_repo,
        pm_repo=pm_repo or AsyncMock(),
        payment_resolver=FakePaymentResolver(),
    )


@pytest.mark.asyncio
async def test_spent_creation_validates_category():
    """Test that creating a spent validates category exists."""
    mock_repo = AsyncMock()
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = None

    service = build_service(mock_repo, category_repo)

    with pytest.raises(ValidationError, match="não existe"):
        await service.create(
            SpentCreate(
                category="nonexistent_category",
                amount=100.0,
                item_bought="item1",
                payment_method="itau",
                location="Test Location",
            )
        )

    mock_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_spent_creation_with_valid_category():
    """Test that creating a spent succeeds with valid category."""
    mock_repo = AsyncMock()
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = MagicMock(key="test_cat")

    pm_repo = AsyncMock()
    pm_repo.get_by_key.return_value = MagicMock(key="itau", is_credit_card=False)

    mock_created_spent = MagicMock()
    mock_created_spent.category = "test_cat"
    mock_created_spent.amount = 100.0
    mock_repo.create.return_value = mock_created_spent

    service = build_service(mock_repo, category_repo, pm_repo)

    spent = await service.create(
        SpentCreate(
            category="test_cat",
            amount=100.0,
            item_bought="item1",
            payment_method="itau",
            location="Test",
        )
    )

    assert spent.category == "test_cat"
    assert spent.amount == 100.0


@pytest.mark.asyncio
async def test_spent_update_validates_category():
    """Test that updating a spent validates new category."""
    mock_repo = AsyncMock()
    category_repo = AsyncMock()
    category_repo.get_by_key.return_value = None

    service = build_service(mock_repo, category_repo)

    with pytest.raises(ValidationError, match="não existe"):
        await service.update(uuid4(), SpentUpdate(category="nonexistent"))

    mock_repo.update.assert_not_awaited()
