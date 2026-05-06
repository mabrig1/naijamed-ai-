from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import BuyerType, Incoterms


class GlobalBuyer(Base):
    __tablename__ = "global_buyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    company_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    buyer_type: Mapped[BuyerType] = mapped_column(Enum(BuyerType, name="buyertype"), nullable=False)

    # List of preferred herb names stored as a JSON array
    preferred_herbs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    preferred_volume_kg_per_month: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    preferred_incoterms: Mapped[Incoterms | None] = mapped_column(Enum(Incoterms, name="incoterms"), nullable=True)

    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    freight_quotes: Mapped[list["FreightQuote"]] = relationship(back_populates="buyer")
