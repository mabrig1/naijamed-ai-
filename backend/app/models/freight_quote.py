from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import FreightChannel


class FreightQuote(Base):
    __tablename__ = "freight_quotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("export_listings.id", ondelete="CASCADE"), nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("global_buyers.id", ondelete="CASCADE"), nullable=False, index=True)

    freight_channel: Mapped[FreightChannel] = mapped_column(Enum(FreightChannel, name="freightchannel"), nullable=False)
    carrier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    origin: Mapped[str] = mapped_column(String(300), nullable=False)
    destination: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

    quoted_cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    transit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    ai_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    listing: Mapped["ExportListing"] = relationship(back_populates="freight_quotes")
    buyer: Mapped["GlobalBuyer"] = relationship(back_populates="freight_quotes")
