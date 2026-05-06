from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base


class FarmListing(Base):
    __tablename__ = "farm_listings"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="ck_farm_listing_quantity_positive"),
        CheckConstraint("price_per_kg > 0", name="ck_farm_listing_price_positive"),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 10)",
            name="ck_farm_listing_quality_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farmer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    herb_id: Mapped[int] = mapped_column(
        ForeignKey("herbs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Numeric(12,3) avoids floating-point rounding errors for quantities and prices
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    harvest_date: Mapped[date] = mapped_column(Date, nullable=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    farmer: Mapped["User"] = relationship(back_populates="farm_listings")
    herb: Mapped["Herb"] = relationship(back_populates="farm_listings")

    def __repr__(self) -> str:
        return f"<FarmListing id={self.id} herb_id={self.herb_id} qty={self.quantity_kg}kg>"
