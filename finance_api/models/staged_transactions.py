from datetime import date, datetime
from decimal import Decimal
from typing import Any
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finance_api.core.database import Base


class StagedTransaction(Base):
    __tablename__ = "staged_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    raw_title: Mapped[str] = mapped_column(String, nullable=False)
    raw_description: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_row: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # IN, OUT
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # EXPENSE, INCOME, TRANSFER, INVOICE_PAYMENT, REFUND
    payment_type: Mapped[str] = mapped_column(String(20), default="OTHER", nullable=False)
    suggested_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    suggestion_source: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )  # RULE, MEMORY, LLM
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    current_installment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_installments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_last_digits: Mapped[str | None] = mapped_column(String(10), nullable=True)
    competence_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    possible_duplicate_of_spent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    possible_duplicate_of_income_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    committed_spent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    committed_income_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )

    batch: Mapped[Any] = relationship("ImportBatch", back_populates="transactions")
