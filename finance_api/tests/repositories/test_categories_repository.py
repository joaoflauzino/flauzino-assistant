import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.categories import CategoryCreate, CategoryUpdate


@pytest.fixture
def mock_db_session():
    """Fixture for a mocked async database session."""
    session = AsyncMock()
    # Mock default execute behavior
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.rowcount = 1
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_create_category(mock_db_session):
    """Test creating a new category."""
    repo = CategoryRepository(mock_db_session)
    category_data = CategoryCreate(key="pets", display_name="Pets")

    category = await repo.create(category_data)

    assert category.key == "pets"
    assert category.display_name == "Pets"

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()
    mock_db_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_categories(mock_db_session):
    """Test listing all categories."""
    repo = CategoryRepository(mock_db_session)

    # Mock count result (first execute call)
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2

    # Mock list items result (second execute call)
    mock_items_result = MagicMock()
    c1 = MagicMock()
    c1.key = "test1"
    c2 = MagicMock()
    c2.key = "test2"
    mock_items_result.scalars.return_value.all.return_value = [c1, c2]

    mock_db_session.execute.side_effect = [mock_count_result, mock_items_result]

    items, total = await repo.list()

    assert total == 2
    assert len(items) == 2
    assert items[0].key == "test1"
    assert items[1].key == "test2"
    assert mock_db_session.execute.await_count == 2


@pytest.mark.asyncio
async def test_get_by_key(mock_db_session):
    """Test getting category by key."""
    repo = CategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_category = MagicMock()
    mock_category.key = "gaming"
    mock_result.scalar_one_or_none.return_value = mock_category

    mock_db_session.execute.return_value = mock_result

    found = await repo.get_by_key("gaming")

    assert found is not None
    assert found.key == "gaming"
    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id(mock_db_session):
    """Test getting category by ID."""
    repo = CategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_category = MagicMock()
    mock_category.key = "travel"
    mock_result.scalar_one_or_none.return_value = mock_category

    mock_db_session.execute.return_value = mock_result

    cat_id = uuid4()
    found = await repo.get_by_id(cat_id)

    assert found is not None
    assert found.key == "travel"
    mock_db_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_category(mock_db_session):
    """Test updating a category."""
    repo = CategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_category = MagicMock()
    mock_category.display_name = "Food & Dining"
    mock_category.key = "food"
    mock_result.scalar_one_or_none.return_value = mock_category

    mock_db_session.execute.return_value = mock_result

    cat_id = uuid4()
    updated = await repo.update(cat_id, CategoryUpdate(display_name="Food & Dining"))

    assert updated is not None
    assert updated.display_name == "Food & Dining"
    assert updated.key == "food"
    mock_db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_category(mock_db_session):
    """Test deleting a category."""
    repo = CategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db_session.execute.return_value = mock_result

    cat_id = uuid4()
    result = await repo.delete(cat_id)

    assert result is True
    mock_db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_nonexistent_category(mock_db_session):
    """Test getting category that doesn't exist."""
    repo = CategoryRepository(mock_db_session)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    # By key
    found = await repo.get_by_key("nonexistent")
    assert found is None

    # By ID
    found_by_id = await repo.get_by_id(uuid4())
    assert found_by_id is None
