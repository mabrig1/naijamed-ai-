from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import MarketRegion


class ExportPriceIndex(Base):
    __tablename__ = "export_price_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    herb_id: Mapped[int] = mapped_column(ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False, index=True)

    market_region: Mapped[MarketRegion] = mapped_column(Enum(MarketRegion, name="marketregion"), nullable=False)
    price_per_kg_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    herb = relationship("Herb", foreign_keys=[herb_id])
