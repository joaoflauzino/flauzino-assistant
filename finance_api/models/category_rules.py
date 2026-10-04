from datetime import datetime
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from finance_api.core.database import Base


class CategoryRule(Base):
    __tablename__ = "category_rules"
    __table_args__ = (
        UniqueConstraint("pattern", "direction", name="uq_category_rules_pattern_direction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    pattern: Mapped[str] = mapped_column(String, nullable=False)
    match_type: Mapped[str] = mapped_column(String(10), default="CONTAINS", nullable=False)
    direction: Mapped[str] = mapped_column(String(3), nullable=False)  # IN, OUT
    kind: Mapped[str] = mapped_column(String(20), default="EXPENSE", nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(
        String(10), default="LEARNED", nullable=False
    )  # SEED, LEARNED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
        onupdate=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")),
    )
