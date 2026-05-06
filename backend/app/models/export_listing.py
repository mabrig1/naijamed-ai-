from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import FreightChannel, HerbGrade, Incoterms, PackagingType


class ExportListing(Base):
    __tablename__ = "export_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    herb_id: Mapped[int] = mapped_column(ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False, index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    price_per_kg_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    minimum_order_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)

    herb_grade: Mapped[HerbGrade] = mapped_column(Enum(HerbGrade, name="herbgrade"), nullable=False)
    packaging_type: Mapped[PackagingType] = mapped_column(Enum(PackagingType, name="packagingtype"), nullable=False)

    available_from_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Certification references (certificate numbers / URLs)
    certificate_nafdac: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_naqs: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_nepc: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_organic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    origin_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origin_lga: Mapped[str | None] = mapped_column(String(100), nullable=True)
    farm_gps_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    farm_gps_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    export_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    herb = relationship("Herb", foreign_keys=[herb_id])
    seller = relationship("User", foreign_keys=[seller_id])
    orders: Mapped[list["ExportOrder"]] = relationship(back_populates="listing")
    freight_quotes: Mapped[list["FreightQuote"]] = relationship(back_populates="listing")
