from uuid import UUID

from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.categories import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class CategoryService:
    def __init__(self, repo: CategoryRepository):
        self.repo = repo

    async def create(self, category_data: CategoryCreate) -> CategoryResponse:
        # Check if category with this key already exists
        existing = await self.repo.get_by_key(category_data.key)
        if existing:
            raise ValueError(f"Category with key '{category_data.key}' already exists")

        logger.info(f"Creating category: {category_data.key}")
        category = await self.repo.create(category_data)
        return CategoryResponse.model_validate(category)

    async def list(
        self, page: int = 1, size: int = 100
    ) -> tuple[list[CategoryResponse], int]:
        skip = (page - 1) * size
        logger.info(f"Listing categories page {page} size {size}")
        items, total = await self.repo.list(skip, size)
        return [CategoryResponse.model_validate(item) for item in items], total

    async def get_by_id(self, category_id: UUID) -> CategoryResponse | None:
        logger.info(f"Getting category: {category_id}")
        category = await self.repo.get_by_id(category_id)
        return CategoryResponse.model_validate(category) if category else None

    async def update(
        self, category_id: UUID, update_data: CategoryUpdate
    ) -> CategoryResponse | None:
        # If updating key, check if new key already exists
        if update_data.key:
            existing = await self.repo.get_by_key(update_data.key)
            if existing and existing.id != category_id:
                raise ValueError(
                    f"Category with key '{update_data.key}' already exists"
                )

        logger.info(f"Updating category: {category_id}")
        category = await self.repo.update(category_id, update_data)
        return CategoryResponse.model_validate(category) if category else None

    async def delete(self, category_id: UUID) -> bool:
        logger.info(f"Deleting category: {category_id}")
        return await self.repo.delete(category_id)
