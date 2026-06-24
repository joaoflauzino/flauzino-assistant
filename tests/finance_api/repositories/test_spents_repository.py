from unittest.mock import AsyncMock, MagicMock

import pytest

from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.enums import CardEnum, NameEnum
from finance_api.schemas.spents import SpentCreate


@pytest.fixture
def mock_db_session():
    """Fixture for a mocked async database session."""
    session = AsyncMock()
    # Mock the behavior of result.scalars().all()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    session.add = MagicMock()
    return session


async def test_create_spent(mock_db_session):
    """
    Test that the create method correctly adds a new spent record to the database.
    """
    # Arrange
    repo = SpentRepository(mock_db_session)
    spent_data = SpentCreate(
        category="mercado",  # Use string instead of CategoryEnum
        amount=150.75,
        item_bought="item1",
        payment_method=CardEnum.ITAU,
        payment_owner=NameEnum.JOAO_LUCAS,
        location="Supermarket",
    )

    # Act
    await repo.create(spent_data)

    # Assert
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()

    # Check the object passed to 'add'
    added_spent = mock_db_session.add.call_args[0][0]
    assert added_spent.category == spent_data.category
    assert added_spent.amount == spent_data.amount
    assert added_spent.location == spent_data.location


async def test_list_spents(mock_db_session):
    """
    Test that the list method correctly retrieves a list of spents.
    """
    # Arrange
    repo = SpentRepository(mock_db_session)
    mock_spent_list = [MagicMock(), MagicMock()]  # Mock two Spent objects

    # First call: count
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 10

    # Second call: list
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = mock_spent_list

    mock_db_session.execute.side_effect = [mock_count_result, mock_items_result]

    # Act
    result = await repo.list(skip=0, limit=10)

    # Assert
    assert mock_db_session.execute.await_count == 2
    items, total = result
    assert items == mock_spent_list
    assert total == 10
    assert len(items) == 2


async def test_get_installments_summary(mock_db_session):
    """
    Test that the get_installments_summary method correctly retrieves and maps the summary.
    """
    # Arrange
    repo = SpentRepository(mock_db_session)
    mock_row = MagicMock()
    mock_row.installment_id = "test-id"
    mock_row.category = "tecnologia"
    mock_row.item_bought = "Monitor"
    mock_row.amount = 100.0
    mock_row.total_installments = 10
    mock_row.passed_installments = 2

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    mock_db_session.execute.return_value = mock_result

    # Act
    result = await repo.get_installments_summary()

    # Assert
    mock_db_session.execute.assert_awaited_once()
    assert len(result) == 1
    assert result[0]["installment_id"] == "test-id"
    assert result[0]["category"] == "tecnologia"
    assert result[0]["item_bought"] == "Monitor"
    assert result[0]["amount"] == 100.0
    assert result[0]["total_installments"] == 10
    assert result[0]["passed_installments"] == 2
