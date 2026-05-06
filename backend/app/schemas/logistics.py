from datetime import datetime, date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from app.models.export_enums import (
    ExportDocType, FreightChannel, Incoterms, PaymentMethod, ShipmentEventType,
)


# ---------------------------------------------------------------------------
# Freight Quotes
# ---------------------------------------------------------------------------

class FreightQuoteRequest(BaseModel):
    listing_id: int
    origin_state: str
    destination_country: str
    quantity_kg: float
    herb_type: str

    model_config = {"str_strip_whitespace": True}


class AIFreightQuoteItem(BaseModel):
    channel: str
    carrier: str
    estimated_cost_usd: float
    transit_days: int
    recommended_for: str
    pros: list[str]
    cons: list[str]
    departure_airport: str
    ai_recommended: bool


class FreightQuotesResponse(BaseModel):
    listing_id: int
    quotes: list[AIFreightQuoteItem]
    recommendation: dict[str, Any] | None = None
    saved_quote_ids: list[int] = []


class FreightQuoteRead(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    freight_channel: FreightChannel
    carrier_name: str | None
    origin: str
    destination: str
    quantity_kg: Decimal
    quoted_cost_usd: Decimal
    transit_days: int | None
    valid_until: date | None
    ai_recommended: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QuoteAcceptBody(BaseModel):
    incoterms: Incoterms
    payment_method: PaymentMethod
    destination_port: str | None = None

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------

class ShipmentCreate(BaseModel):
    order_id: int
    freight_channel: FreightChannel
    tracking_number: str | None = None
    carrier_name: str | None = None
    origin_port: str | None = None
    destination_port: str | None = None
    vessel_or_flight: str | None = None
    container_number: str | None = None
    departure_date: date | None = None
    estimated_arrival: date | None = None

    model_config = {"str_strip_whitespace": True}


class ShipmentUpdate(BaseModel):
    tracking_number: str | None = None
    carrier_name: str | None = None
    current_status: str | None = None
    current_location: str | None = None
    temperature_celsius: Decimal | None = None
    last_gps_lat: Decimal | None = None
    last_gps_lng: Decimal | None = None
    customs_cleared: bool | None = None
    estimated_arrival: date | None = None
    actual_arrival: date | None = None
    vessel_or_flight: str | None = None
    container_number: str | None = None

    model_config = {"str_strip_whitespace": True}


class ShipmentEventCreate(BaseModel):
    event_type: ShipmentEventType
    location: str | None = None
    description: str | None = None
    event_timestamp: datetime | None = None

    model_config = {"str_strip_whitespace": True}


class ShipmentEventRead(BaseModel):
    id: int
    shipment_id: int
    event_type: ShipmentEventType
    location: str | None
    description: str | None
    event_timestamp: datetime

    model_config = {"from_attributes": True}


class ShipmentRead(BaseModel):
    id: int
    order_id: int
    tracking_number: str | None
    carrier_name: str | None
    freight_channel: FreightChannel
    origin_port: str | None
    destination_port: str | None
    vessel_or_flight: str | None
    container_number: str | None
    departure_date: date | None
    estimated_arrival: date | None
    actual_arrival: date | None
    current_status: str | None
    current_location: str | None
    temperature_celsius: Decimal | None
    last_gps_lat: Decimal | None
    last_gps_lng: Decimal | None
    customs_cleared: bool
    created_at: datetime
    events: list[ShipmentEventRead] = []

    model_config = {"from_attributes": True}


class TrackingSummary(BaseModel):
    shipment_id: int
    tracking_number: str | None
    carrier_name: str | None
    freight_channel: FreightChannel
    current_status: str | None
    current_location: str | None
    temperature_celsius: Decimal | None
    departure_date: date | None
    estimated_arrival: date | None
    actual_arrival: date | None
    customs_cleared: bool
    total_events: int
    latest_event: ShipmentEventRead | None
    anomaly: dict[str, Any]


# ---------------------------------------------------------------------------
# Export Documents
# ---------------------------------------------------------------------------

class ExportDocumentCreate(BaseModel):
    order_id: int
    doc_type: ExportDocType
    document_url: str | None = None
    issued_by: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None

    model_config = {"str_strip_whitespace": True}


class ExportDocumentRead(BaseModel):
    id: int
    order_id: int
    doc_type: ExportDocType
    document_url: str | None
    issued_by: str | None
    issue_date: date | None
    expiry_date: date | None
    is_ai_generated: bool
    is_verified: bool

    model_config = {"from_attributes": True}


class AIDocGenerateRequest(BaseModel):
    order_id: int
    doc_type: ExportDocType

    model_config = {"str_strip_whitespace": True}


class AIDocGenerateResponse(BaseModel):
    document_id: int
    doc_type: ExportDocType
    generated_data: dict[str, Any]
    document: ExportDocumentRead


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class ShipmentAlert(BaseModel):
    shipment_id: int
    order_id: int
    tracking_number: str | None
    alert_type: str
    severity: str
    message: str
    event_timestamp: datetime | None


class AlertSettingsBody(BaseModel):
    email_alerts: bool = True
    sms_alerts: bool = False
    alert_on_delay: bool = True
    alert_on_temperature_breach: bool = True
    alert_on_customs_hold: bool = True
    phone_number: str | None = None

    model_config = {"str_strip_whitespace": True}


class AlertSettingsResponse(BaseModel):
    message: str
    settings: AlertSettingsBody
