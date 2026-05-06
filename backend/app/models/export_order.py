from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import (
    FreightChannel, Incoterms, OrderStatus, PaymentMethod, PaymentStatus,
)


class ExportOrder(Base):
    __tablename__ = "export_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("export_listings.id", ondelete="RESTRICT"), nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    agreed_price_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    freight_channel: Mapped[FreightChannel] = mapped_column(Enum(FreightChannel, name="freightchannel"), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_port: Mapped[str | None] = mapped_column(String(200), nullable=True)
    incoterms: Mapped[Incoterms] = mapped_column(Enum(Incoterms, name="incoterms"), nullable=False)

    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="paymentmethod"), nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="paymentstatus"), nullable=False, default=PaymentStatus.pending,
    )
    order_status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="orderstatus"), nullable=False, default=OrderStatus.placed,
    )

    estimated_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    listing: Mapped["ExportListing"] = relationship(back_populates="orders")
    buyer = relationship("User", foreign_keys=[buyer_id])
    shipments: Mapped[list["Shipment"]] = relationship(back_populates="order")
    documents: Mapped[list["ExportDocument"]] = relationship(back_populates="order")
    escrow: Mapped["EscrowTransaction | None"] = relationship(back_populates="order", uselist=False)
