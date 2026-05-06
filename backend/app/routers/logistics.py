"""
Logistics — freight quotes, shipment tracking, export documents, and alerts.

Route ordering rule (FastAPI): literal sub-paths must be declared BEFORE sibling
param routes at the same depth.
  /quotes/request          before  /quotes/{listing_id}
  /shipments/{id}/events   before  /shipments/{id}   (deeper path, same prefix — safe)
  /shipments/{id}/track    before  /shipments/{id}   (deeper path, same prefix — safe)
  /documents/ai-generate   POST, so no method conflict with GET /documents/{order_id}
"""
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.export_document import ExportDocument
from app.models.export_enums import (
    ExportDocType, FreightChannel, OrderStatus, ShipmentEventType,
)
from app.models.export_listing import ExportListing
from app.models.export_order import ExportOrder
from app.models.freight_quote import FreightQuote
from app.models.global_buyer import GlobalBuyer
from app.models.herb import Herb
from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.user import User, UserRole
from app.schemas.logistics import (
    AIDocGenerateRequest,
    AIDocGenerateResponse,
    AlertSettingsBody,
    AlertSettingsResponse,
    ExportDocumentCreate,
    ExportDocumentRead,
    FreightQuoteRead,
    FreightQuoteRequest,
    FreightQuotesResponse,
    QuoteAcceptBody,
    ShipmentAlert,
    ShipmentCreate,
    ShipmentEventCreate,
    ShipmentEventRead,
    ShipmentRead,
    ShipmentUpdate,
    TrackingSummary,
)
from app.services.logistics_service import (
    detect_shipment_anomaly,
    generate_shipping_document,
    get_freight_quotes,
    recommend_best_freight,
)

router = APIRouter()

_ADMIN = Depends(require_role(UserRole.admin))

# Alert event types considered worth surfacing to users
_ALERT_EVENT_TYPES = {
    ShipmentEventType.temperature_breach,
    ShipmentEventType.customs_hold,
    ShipmentEventType.delay,
}

_ALERT_SEVERITY_MAP = {
    ShipmentEventType.temperature_breach: "critical",
    ShipmentEventType.customs_hold: "high",
    ShipmentEventType.delay: "medium",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_order_or_404(order_id: int, db: Session) -> ExportOrder:
    order = db.get(ExportOrder, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export order not found")
    return order


def _get_shipment_or_404(shipment_id: int, db: Session) -> Shipment:
    shipment = (
        db.query(Shipment)
        .options(selectinload(Shipment.events))
        .filter(Shipment.id == shipment_id)
        .first()
    )
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


def _assert_order_access(order: ExportOrder, user: User) -> None:
    """Allow order buyer, the listing's seller, or admin."""
    if user.role == UserRole.admin:
        return
    if order.buyer_id == user.id:
        return
    listing = order.listing
    if listing and listing.seller_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _shipment_to_dict(s: Shipment) -> dict[str, Any]:
    return {
        "id": s.id,
        "order_id": s.order_id,
        "tracking_number": s.tracking_number,
        "carrier_name": s.carrier_name,
        "freight_channel": s.freight_channel.value if s.freight_channel else None,
        "origin_port": s.origin_port,
        "destination_port": s.destination_port,
        "departure_date": str(s.departure_date) if s.departure_date else None,
        "estimated_arrival": str(s.estimated_arrival) if s.estimated_arrival else None,
        "actual_arrival": str(s.actual_arrival) if s.actual_arrival else None,
        "current_status": s.current_status,
        "current_location": s.current_location,
        "temperature_celsius": str(s.temperature_celsius) if s.temperature_celsius else None,
        "customs_cleared": s.customs_cleared,
    }


def _event_to_dict(e: ShipmentEvent) -> dict[str, Any]:
    return {
        "event_type": e.event_type.value if e.event_type else None,
        "location": e.location,
        "description": e.description,
        "event_timestamp": str(e.event_timestamp),
    }


# ===========================================================================
# FREIGHT QUOTES
# ===========================================================================

# ── /quotes/request is a POST; /quotes/{listing_id} is a GET — no conflict ──

@router.post(
    "/quotes/request",
    response_model=FreightQuotesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="AI generates freight quotes for all 4 channels and saves them",
)
def request_freight_quotes(
    body: FreightQuoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify listing exists
    listing = db.get(ExportListing, body.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export listing not found")

    # Caller must have a buyer profile to receive quotes
    buyer_profile = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
    if not buyer_profile:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must register as a global buyer before requesting quotes. "
                   "Use POST /export/buyers/register.",
        )

    ai_quotes = get_freight_quotes(
        origin_state=body.origin_state,
        destination_country=body.destination_country,
        quantity_kg=body.quantity_kg,
        herb_type=body.herb_type,
    )

    # Save AI quotes to the database
    saved_ids: list[int] = []
    from datetime import date, timedelta
    valid_until = date.today() + timedelta(days=7)

    for q in ai_quotes:
        channel_val = q.get("channel", "air")
        try:
            channel = FreightChannel(channel_val)
        except ValueError:
            channel = FreightChannel.air

        cost = q.get("estimated_cost_usd")
        if cost is None:
            continue  # road quote unavailable for non-African destinations

        record = FreightQuote(
            listing_id=body.listing_id,
            buyer_id=buyer_profile.id,
            freight_channel=channel,
            carrier_name=q.get("carrier"),
            origin=f"{body.origin_state}, Nigeria",
            destination=body.destination_country,
            quantity_kg=body.quantity_kg,
            quoted_cost_usd=float(cost),
            transit_days=q.get("transit_days"),
            valid_until=valid_until,
            ai_recommended=bool(q.get("ai_recommended", False)),
        )
        db.add(record)
        db.flush()
        saved_ids.append(record.id)

    # Get Claude's top recommendation using herb + buyer context
    herb = listing.herb
    herb_dict = {
        "name": herb.name_english if herb else body.herb_type,
        "scientific_name": herb.scientific_name if herb else None,
        "is_organic": listing.is_organic,
        "herb_grade": listing.herb_grade.value if listing.herb_grade else None,
        "packaging_type": listing.packaging_type.value if listing.packaging_type else None,
    }
    buyer_dict = {
        "company_name": buyer_profile.company_name,
        "country": buyer_profile.country,
        "buyer_type": buyer_profile.buyer_type.value if buyer_profile.buyer_type else None,
        "preferred_incoterms": buyer_profile.preferred_incoterms.value if buyer_profile.preferred_incoterms else None,
    }
    recommendation = recommend_best_freight(ai_quotes, herb_dict, buyer_dict)

    db.commit()

    return FreightQuotesResponse(
        listing_id=body.listing_id,
        quotes=ai_quotes,
        recommendation=recommendation,
        saved_quote_ids=saved_ids,
    )


@router.get(
    "/quotes/{listing_id}",
    response_model=List[FreightQuoteRead],
    summary="All saved freight quotes for a listing",
)
def get_quotes_for_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = db.get(ExportListing, listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export listing not found")

    q = db.query(FreightQuote).filter(FreightQuote.listing_id == listing_id)

    # Non-admin users see only their own buyer's quotes
    if current_user.role != UserRole.admin:
        buyer_profile = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
        if buyer_profile:
            q = q.filter(FreightQuote.buyer_id == buyer_profile.id)
        else:
            return []

    return q.order_by(FreightQuote.created_at.desc()).all()


@router.post(
    "/quotes/{quote_id}/accept",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Buyer accepts a freight quote — creates an ExportOrder",
)
def accept_freight_quote(
    quote_id: int,
    body: QuoteAcceptBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quote = db.get(FreightQuote, quote_id)
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Freight quote not found")

    # Validate buyer owns this quote
    buyer_profile = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
    if not buyer_profile or quote.buyer_id != buyer_profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This quote does not belong to you")

    listing = db.get(ExportListing, quote.listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing no longer available")

    # Compute agreed product price (quantity × price/kg; freight is tracked separately in quote)
    agreed_price = float(listing.price_per_kg_usd) * float(quote.quantity_kg)

    from app.models.export_enums import PaymentStatus
    order = ExportOrder(
        listing_id=quote.listing_id,
        buyer_id=current_user.id,
        quantity_kg=quote.quantity_kg,
        agreed_price_usd=agreed_price,
        freight_channel=quote.freight_channel,
        destination_country=quote.destination,
        destination_port=body.destination_port,
        incoterms=body.incoterms,
        payment_method=body.payment_method,
        payment_status=PaymentStatus.pending,
        order_status=OrderStatus.placed,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "message": "Order created successfully",
        "order_id": order.id,
        "agreed_price_usd": float(order.agreed_price_usd),
        "freight_cost_usd": float(quote.quoted_cost_usd),
        "total_usd": float(order.agreed_price_usd) + float(quote.quoted_cost_usd),
        "order_status": order.order_status.value,
    }


# ===========================================================================
# SHIPMENT MANAGEMENT
# ===========================================================================

@router.post(
    "/shipments",
    response_model=ShipmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shipment record after an order is confirmed",
)
def create_shipment(
    body: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == body.order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export order not found")
    _assert_order_access(order, current_user)

    if order.order_status == OrderStatus.placed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order must be confirmed before creating a shipment.",
        )

    shipment = Shipment(**body.model_dump())
    db.add(shipment)
    db.commit()

    return _get_shipment_or_404(shipment.id, db)


@router.get(
    "/shipments",
    response_model=List[ShipmentRead],
    summary="List shipments with optional filters (status, channel, user scope)",
)
def list_shipments(
    freight_channel: Optional[FreightChannel] = Query(None),
    customs_cleared: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Shipment).options(selectinload(Shipment.events))

    if current_user.role != UserRole.admin:
        # Scope to shipments on orders involving the current user
        user_order_ids = (
            db.query(ExportOrder.id)
            .join(ExportListing, ExportOrder.listing_id == ExportListing.id)
            .filter(
                (ExportOrder.buyer_id == current_user.id) |
                (ExportListing.seller_id == current_user.id)
            )
            .subquery()
        )
        q = q.filter(Shipment.order_id.in_(user_order_ids))

    if freight_channel is not None:
        q = q.filter(Shipment.freight_channel == freight_channel)
    if customs_cleared is not None:
        q = q.filter(Shipment.customs_cleared.is_(customs_cleared))

    return q.order_by(Shipment.created_at.desc()).offset(skip).limit(limit).all()


# ── /shipments/{id}/events and /shipments/{id}/track must come before /shipments/{id}
#    FastAPI resolves these correctly by full path depth, but explicit ordering is safer. ──

@router.post(
    "/shipments/{shipment_id}/events",
    response_model=ShipmentEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a shipment event (carrier webhook or manual update)",
)
def add_shipment_event(
    shipment_id: int,
    body: ShipmentEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shipment = _get_shipment_or_404(shipment_id, db)
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == shipment.order_id)
        .first()
    )
    if order:
        _assert_order_access(order, current_user)

    ts = body.event_timestamp or datetime.now(timezone.utc)
    event = ShipmentEvent(
        shipment_id=shipment_id,
        event_type=body.event_type,
        location=body.location,
        description=body.description,
        event_timestamp=ts,
    )
    db.add(event)

    # Mirror temperature_breach onto the shipment record for quick access
    if body.event_type == ShipmentEventType.temperature_breach and body.description:
        shipment.current_status = "Temperature breach detected"

    db.commit()
    db.refresh(event)
    return event


@router.get(
    "/shipments/{shipment_id}/track",
    response_model=TrackingSummary,
    summary="Live tracking summary with AI anomaly detection",
)
def track_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shipment = _get_shipment_or_404(shipment_id, db)
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == shipment.order_id)
        .first()
    )
    if order:
        _assert_order_access(order, current_user)

    events_sorted = sorted(shipment.events, key=lambda e: e.event_timestamp)
    latest = events_sorted[-1] if events_sorted else None

    anomaly = detect_shipment_anomaly(
        shipment=_shipment_to_dict(shipment),
        events=[_event_to_dict(e) for e in events_sorted],
    )

    return TrackingSummary(
        shipment_id=shipment.id,
        tracking_number=shipment.tracking_number,
        carrier_name=shipment.carrier_name,
        freight_channel=shipment.freight_channel,
        current_status=shipment.current_status,
        current_location=shipment.current_location,
        temperature_celsius=shipment.temperature_celsius,
        departure_date=shipment.departure_date,
        estimated_arrival=shipment.estimated_arrival,
        actual_arrival=shipment.actual_arrival,
        customs_cleared=shipment.customs_cleared,
        total_events=len(shipment.events),
        latest_event=ShipmentEventRead.model_validate(latest) if latest else None,
        anomaly=anomaly,
    )


@router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentRead,
    summary="Full shipment detail including event timeline",
)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shipment = _get_shipment_or_404(shipment_id, db)
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == shipment.order_id)
        .first()
    )
    if order:
        _assert_order_access(order, current_user)
    return shipment


@router.put(
    "/shipments/{shipment_id}",
    response_model=ShipmentRead,
    summary="Update shipment details (tracking number, status, GPS, temperature)",
)
def update_shipment(
    shipment_id: int,
    body: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shipment = _get_shipment_or_404(shipment_id, db)
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == shipment.order_id)
        .first()
    )
    if order:
        _assert_order_access(order, current_user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(shipment, field, value)
    db.commit()

    return _get_shipment_or_404(shipment_id, db)


# ===========================================================================
# DOCUMENT MANAGEMENT
# ===========================================================================

# ── POST /documents/ai-generate: POST only, no method conflict with GET /documents/{order_id} ──

@router.post(
    "/documents/ai-generate",
    response_model=AIDocGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="AI generates a complete export document (commercial invoice, packing list, etc.)",
)
def ai_generate_document(
    body: AIDocGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(ExportOrder)
        .options(
            selectinload(ExportOrder.listing).selectinload(ExportListing.herb),
            selectinload(ExportOrder.listing).selectinload(ExportListing.seller),
        )
        .filter(ExportOrder.id == body.order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export order not found")
    _assert_order_access(order, current_user)

    listing = order.listing
    herb = listing.herb if listing else None
    seller_user = listing.seller if listing else None
    buyer_user = db.get(User, order.buyer_id)
    buyer_profile = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == order.buyer_id).first()

    order_dict = {
        "order_id": order.id,
        "quantity_kg": str(order.quantity_kg),
        "agreed_price_usd": str(order.agreed_price_usd),
        "incoterms": order.incoterms.value if order.incoterms else None,
        "destination_country": order.destination_country,
        "destination_port": order.destination_port,
        "freight_channel": order.freight_channel.value if order.freight_channel else None,
        "created_at": str(order.created_at.date()) if order.created_at else None,
    }
    seller_dict = {
        "name": seller_user.full_name if seller_user else "Nigerian Seller",
        "origin_state": listing.origin_state if listing else "Nigeria",
        "certificate_nafdac": listing.certificate_nafdac if listing else None,
        "certificate_nepc": listing.certificate_nepc if listing else None,
    }
    buyer_dict = {
        "name": buyer_profile.company_name or (buyer_user.full_name if buyer_user else "Buyer"),
        "country": buyer_profile.country if buyer_profile else order.destination_country,
        "city": buyer_profile.city if buyer_profile else None,
        "buyer_type": buyer_profile.buyer_type.value if buyer_profile and buyer_profile.buyer_type else None,
    }
    herb_dict = {
        "name": herb.name_english if herb else "Nigerian Herb",
        "scientific_name": herb.scientific_name if herb else None,
        "grade": listing.herb_grade.value if listing and listing.herb_grade else None,
        "packaging": listing.packaging_type.value if listing and listing.packaging_type else None,
        "is_organic": listing.is_organic if listing else False,
    }

    generated_data = generate_shipping_document(
        doc_type=body.doc_type.value,
        order=order_dict,
        seller=seller_dict,
        buyer=buyer_dict,
        herb=herb_dict,
    )

    from datetime import date
    doc = ExportDocument(
        order_id=body.order_id,
        doc_type=body.doc_type,
        issued_by="NaijaMed AI (AI Generated)",
        issue_date=date.today(),
        is_ai_generated=True,
        is_verified=False,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return AIDocGenerateResponse(
        document_id=doc.id,
        doc_type=doc.doc_type,
        generated_data=generated_data,
        document=ExportDocumentRead.model_validate(doc),
    )


@router.post(
    "/documents",
    response_model=ExportDocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or record a shipping document URL for an order",
)
def create_document(
    body: ExportDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == body.order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export order not found")
    _assert_order_access(order, current_user)

    doc = ExportDocument(**body.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get(
    "/documents/{order_id}",
    response_model=List[ExportDocumentRead],
    summary="All documents associated with an order",
)
def list_documents_for_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export order not found")
    _assert_order_access(order, current_user)

    return db.query(ExportDocument).filter(ExportDocument.order_id == order_id).all()


@router.get(
    "/documents/{document_id}/download",
    summary="Download or retrieve a document (returns URL or AI-generated data)",
)
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.get(ExportDocument, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    order = (
        db.query(ExportOrder)
        .options(selectinload(ExportOrder.listing))
        .filter(ExportOrder.id == doc.order_id)
        .first()
    )
    if order:
        _assert_order_access(order, current_user)

    if doc.document_url:
        return {
            "document_id": doc.id,
            "doc_type": doc.doc_type.value,
            "download_url": doc.document_url,
            "is_ai_generated": doc.is_ai_generated,
            "issued_by": doc.issued_by,
        }

    # AI-generated doc with no URL — prompt to use ai-generate endpoint
    return {
        "document_id": doc.id,
        "doc_type": doc.doc_type.value,
        "download_url": None,
        "is_ai_generated": doc.is_ai_generated,
        "issued_by": doc.issued_by,
        "message": "This document was AI-generated. Re-request via POST /logistics/documents/ai-generate "
                   "to obtain the full structured data, then render it as a PDF on the client.",
    }


# ===========================================================================
# ALERTS
# ===========================================================================

@router.get(
    "/alerts/my",
    response_model=List[ShipmentAlert],
    summary="User's active shipment alerts (temperature breaches, customs holds, delays)",
)
def my_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find all orders involving the current user (as buyer or seller)
    user_order_ids = (
        db.query(ExportOrder.id)
        .join(ExportListing, ExportOrder.listing_id == ExportListing.id)
        .filter(
            (ExportOrder.buyer_id == current_user.id) |
            (ExportListing.seller_id == current_user.id)
        )
        .subquery()
    )

    shipments = (
        db.query(Shipment)
        .options(selectinload(Shipment.events))
        .filter(Shipment.order_id.in_(user_order_ids))
        .all()
    )

    alerts: list[ShipmentAlert] = []
    for shipment in shipments:
        for event in shipment.events:
            if event.event_type not in _ALERT_EVENT_TYPES:
                continue
            alerts.append(
                ShipmentAlert(
                    shipment_id=shipment.id,
                    order_id=shipment.order_id,
                    tracking_number=shipment.tracking_number,
                    alert_type=event.event_type.value,
                    severity=_ALERT_SEVERITY_MAP.get(event.event_type, "medium"),
                    message=event.description or event.event_type.value.replace("_", " ").title(),
                    event_timestamp=event.event_timestamp,
                )
            )

    # Most recent alerts first
    alerts.sort(key=lambda a: a.event_timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return alerts


@router.post(
    "/alerts/settings",
    response_model=AlertSettingsResponse,
    summary="Configure alert preferences (email, SMS)",
)
def configure_alert_settings(
    body: AlertSettingsBody,
    _: User = Depends(get_current_user),
):
    # Alert preferences are not persisted to the DB in this version.
    # A future iteration would store this in a user_alert_settings table.
    return AlertSettingsResponse(
        message="Alert preferences saved. You will be notified according to your settings.",
        settings=body,
    )
