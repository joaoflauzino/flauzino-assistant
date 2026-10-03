import uuid
from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.core.database import Base
from finance_api.models.credit_cards import CreditCard


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank: Mapped[str] = mapped_column(String(50), nullable=False, default="outro")
    owner: Mapped[str] = mapped_column(String(50), nullable=False, default="joao")
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="CHECKING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    credit_cards: Mapped[List[CreditCard]] = relationship(
        "CreditCard", back_populates="account", cascade="all, delete-orphan", lazy="selectin"
    )
