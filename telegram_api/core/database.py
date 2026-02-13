"""Database module for Telegram API using SQLAlchemy."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from telegram_api.settings import settings
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)

# Create Async Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    ...


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database (create tables if needed)."""
    # In production, we usually use migrations (Alembic).
    # For now, we can rely on init.sql or create_all.
    # Since table exists via init.sql, we might not need to do anything here
    # other than maybe checking connection.
    async with engine.begin():
        # await conn.run_sync(Base.metadata.create_all)
        ...
    logger.info("Database engine initialized")


async def close_db() -> None:
    """Close database engine."""
    await engine.dispose()
    logger.info("Database engine disposed")
