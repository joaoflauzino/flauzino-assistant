import enum
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from finance_api.core.database import Base


class InvoiceStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PAID = "PAID"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    payment_method_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_cards.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    reference_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    real_closing_date: Mapped[date] = mapped_column(Date, nullable=False)
    real_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, length=20),
        default=InvoiceStatus.OPEN,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
