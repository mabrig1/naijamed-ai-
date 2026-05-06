from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import FreightChannel


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("export_orders.id", ondelete="RESTRICT"), nullable=False, index=True)

    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    carrier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    freight_channel: Mapped[FreightChannel] = mapped_column(Enum(FreightChannel, name="freightchannel"), nullable=False)

    origin_port: Mapped[str | None] = mapped_column(String(200), nullable=True)
    destination_port: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vessel_or_flight: Mapped[str | None] = mapped_column(String(200), nullable=True)
    container_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_arrival: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_arrival: Mapped[date | None] = mapped_column(Date, nullable=True)

    current_status: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    last_gps_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    last_gps_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    customs_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    order: Mapped["ExportOrder"] = relationship(back_populates="shipments")
    events: Mapped[list["ShipmentEvent"]] = relationship(back_populates="shipment", order_by="ShipmentEvent.event_timestamp")
