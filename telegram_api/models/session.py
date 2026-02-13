import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from telegram_api.core.database import Base


class TelegramSession(Base):
    """Model for storing Telegram chat session IDs."""

    __tablename__ = "telegram_sessions"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
