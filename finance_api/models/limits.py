from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from finance_api.core.database import Base


class SpendingLimit(Base):
    __tablename__ = "spending_limits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String, unique=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
