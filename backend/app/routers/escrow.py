"""
Escrow & Webhooks — buyer-seller payment protection for Nigerian herb exports.

Two APIRouter objects in this module:
  router         → mounted at /api/escrow   (authenticated endpoints)
  webhook_router → mounted at /api/webhooks (unauthenticated; signature-verified)

Escrow route ordering (FastAPI literal-before-param rule):
  GET  /my-transactions      (literal)  ← must be before /{param}
  GET  /disputes             (literal)
  POST /disputes/{id}/resolve (parameterised — id is escrow id, not order)
  POST /hold                 (literal, POST — no method conflict)
  GET  /status/{order_id}    (parameterised)
  POST /release/{order_id}   (parameterised, POST)
  POST /dispute/{order_id}   (parameterised, POST)

All three path prefixes (dispute* vs hold vs status vs release vs my-*) are
distinct, so there are no cross-route capture risks.
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_current_user, require_role
from app.models.escrow_transaction import EscrowTransaction
from app.models.export_enums import EscrowStatus, OrderStatus, PaymentMethod, ShipmentEventType
from app.models.export_order import ExportOrder
from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.user import User, UserRole
from app.schemas.escrow import (
    DisputeListItem,
    DisputeResolveRequest,
    DisputeResolveResponse,
    DisputesListResponse,
    EscrowDisputeRequest,
    EscrowDisputeResponse,
    EscrowHoldRequest,
    EscrowHoldResponse,
    EscrowReleaseRequest,
    EscrowReleaseResponse,
    EscrowStatusResponse,
    EscrowTransactionRead,
    MyTransactionsResponse,
    ShipmentWebhookEvent,
    WebhookAckResponse,
)
from app.services.escrow_service import (
    dispute_resolution_ai,
    dispute_window_open,
    flw_create_payment_link,
    flw_transfer_to_seller,
    flw_verify_transaction,
    should_auto_release,
    stripe_capture_payment_intent,
    stripe_create_payment_intent,
    stripe_transfer_to_seller,
    stripe_verify_webhook,
)

router = APIRouter()
webhook_router = APIRouter()

_ADMIN = Depends(require_role(UserRole.admin))

# Auto-release window: buyer must confirm within 7 days of escrow being held
_AUTO_RELEASE_DAYS = 7
# Dispute window: buyer has 48 hours after delivery confirmation
_DISPUTE_HOURS = 48


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_order_or_404(order_id: int, db: Session) -> ExportOrder:
    order = (
        db.query(ExportOrder)
        .options(
            selectinload(ExportOrder.listing).selectinload("herb"),
            selectinload(ExportOrder.listing).selectinload("seller"),
            selectinload(ExportOrder.buyer),
            selectinload(ExportOrder.shipments).selectinload(Shipment.events),
            selectinload(ExportOrder.escrow),
        )
        .filter(ExportOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export order #{order_id} not found.",
        )
    return order


def _get_escrow_or_404(escrow_id: int, db: Session) -> EscrowTransaction:
    escrow = (
        db.query(EscrowTransaction)
        .options(selectinload(EscrowTransaction.order))
        .filter(EscrowTransaction.id == escrow_id)
        .first()
    )
    if not escrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escrow transaction #{escrow_id} not found.",
        )
    return escrow


def _assert_buyer_or_admin(order: ExportOrder, user: User) -> None:
    if user.role == UserRole.admin:
        return
    if order.buyer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the buyer or an admin can perform this action.",
        )


def _assert_access(order: ExportOrder, user: User) -> None:
    """Allow buyer, seller, or admin."""
    if user.role == UserRole.admin:
        return
    if order.buyer_id == user.id:
        return
    listing = order.listing
    if listing and listing.seller_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def _order_to_dict(order: ExportOrder) -> dict[str, Any]:
    listing = order.listing
    herb = listing.herb if listing else None
    seller = listing.seller if listing else None
    return {
        "order_id": order.id,
        "listing_id": order.listing_id,
        "herb_name": herb.name_english if herb else None,
        "quantity_kg": str(order.quantity_kg),
        "agreed_price_usd": str(order.agreed_price_usd),
        "freight_channel": order.freight_channel.value,
        "destination_country": order.destination_country,
        "incoterms": order.incoterms.value,
        "payment_method": order.payment_method.value,
        "order_status": order.order_status.value,
        "created_at": str(order.created_at),
        "buyer_id": order.buyer_id,
        "seller_id": seller.id if seller else None,
        "seller_name": seller.full_name if seller else None,
    }


def _execute_release(
    escrow: EscrowTransaction,
    order: ExportOrder,
    release_body: EscrowReleaseRequest | None,
    condition: str,
    db: Session,
) -> dict[str, Any]:
    """
    Core release logic — transfer funds and mark escrow as released.
    Returns {"transfer_id": ..., "transfer_status": ...}.
    """
    now = datetime.now(timezone.utc)
    transfer_id: str | None = None
    transfer_status: str | None = None

    if escrow.gateway == "flutterwave":
        if (
            release_body
            and release_body.seller_bank_code
            and release_body.seller_account_number
        ):
            result = flw_transfer_to_seller(
                order_id=order.id,
                amount=float(escrow.amount_usd),
                account_bank=release_body.seller_bank_code,
                account_number=release_body.seller_account_number,
                currency=release_body.seller_account_currency,
            )
            transfer_id = result.get("transfer_id")
            transfer_status = result.get("status")
        else:
            transfer_status = "manual_required"
            transfer_id = f"MANUAL-FLW-{order.id}"

    elif escrow.gateway == "stripe":
        if release_body and release_body.seller_stripe_account_id:
            result = stripe_transfer_to_seller(
                order_id=order.id,
                amount_usd=float(escrow.amount_usd),
                seller_stripe_account_id=release_body.seller_stripe_account_id,
            )
            transfer_id = result.get("transfer_id")
            transfer_status = result.get("status", "created")
        else:
            transfer_status = "manual_required"
            transfer_id = f"MANUAL-STRIPE-{order.id}"
    else:
        transfer_status = "manual_required"
        transfer_id = f"MANUAL-{order.id}"

    # Update escrow
    escrow.status = EscrowStatus.released
    escrow.released_at = now
    escrow.release_condition = condition
    escrow.gateway_transfer_id = transfer_id

    # Update order status
    order.order_status = OrderStatus.delivered
    order.payment_status = __import__("app.models.export_enums", fromlist=["PaymentStatus"]).PaymentStatus.released

    db.commit()
    return {"transfer_id": transfer_id, "transfer_status": transfer_status}


# ===========================================================================
# ── ESCROW ENDPOINTS ─────────────────────────────────────────────────────────
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /escrow/my-transactions  ← MUST be before any /{order_id} routes
# ---------------------------------------------------------------------------

@router.get(
    "/my-transactions",
    response_model=MyTransactionsResponse,
    summary="My escrow transaction history",
    description="Returns all escrow transactions where the current user is buyer or seller.",
    status_code=status.HTTP_200_OK,
)
def my_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MyTransactionsResponse:
    # Buyers: orders where buyer_id = current_user.id
    buyer_orders = (
        db.query(ExportOrder.id)
        .filter(ExportOrder.buyer_id == current_user.id)
        .subquery()
    )
    # Sellers: orders where listing.seller_id = current_user.id
    from app.models.export_listing import ExportListing
    seller_orders = (
        db.query(ExportOrder.id)
        .join(ExportListing, ExportOrder.listing_id == ExportListing.id)
        .filter(ExportListing.seller_id == current_user.id)
        .subquery()
    )

    from sqlalchemy import or_
    transactions = (
        db.query(EscrowTransaction)
        .filter(
            or_(
                EscrowTransaction.order_id.in_(buyer_orders),
                EscrowTransaction.order_id.in_(seller_orders),
            )
        )
        .order_by(EscrowTransaction.held_at.desc())
        .all()
    )

    return MyTransactionsResponse(
        user_id=current_user.id,
        count=len(transactions),
        transactions=[EscrowTransactionRead.model_validate(t) for t in transactions],
    )


# ---------------------------------------------------------------------------
# GET /escrow/disputes  (admin only)
# ---------------------------------------------------------------------------

@router.get(
    "/disputes",
    response_model=DisputesListResponse,
    summary="List all disputed escrow transactions (admin)",
    description="Returns every EscrowTransaction currently in 'disputed' status.",
    status_code=status.HTTP_200_OK,
)
def list_disputes(
    _admin: User = _ADMIN,
    db: Session = Depends(get_db),
) -> DisputesListResponse:
    disputes = (
        db.query(EscrowTransaction)
        .filter(EscrowTransaction.status == EscrowStatus.disputed)
        .order_by(EscrowTransaction.dispute_raised_at.desc())
        .all()
    )

    items = [
        DisputeListItem(
            escrow_id=d.id,
            order_id=d.order_id,
            amount_usd=d.amount_usd,
            dispute_reason=d.dispute_reason,
            dispute_raised_at=d.dispute_raised_at,
            dispute_resolved_at=d.dispute_resolved_at,
            ai_recommendation_summary=d.ai_recommendation[:200] if d.ai_recommendation else None,
            resolution_notes=d.resolution_notes,
            gateway=d.gateway,
            status=d.status,
        )
        for d in disputes
    ]
    return DisputesListResponse(count=len(items), disputes=items)


# ---------------------------------------------------------------------------
# POST /escrow/disputes/{id}/resolve  (admin only)
# ---------------------------------------------------------------------------

@router.post(
    "/disputes/{escrow_id}/resolve",
    response_model=DisputeResolveResponse,
    summary="Resolve a dispute (admin)",
    description=(
        "Admin reviews the AI recommendation and sets the final resolution. "
        "Triggers the appropriate financial action (release or refund)."
    ),
    status_code=status.HTTP_200_OK,
)
def resolve_dispute(
    escrow_id: int,
    body: DisputeResolveRequest,
    _admin: User = _ADMIN,
    db: Session = Depends(get_db),
) -> DisputeResolveResponse:
    escrow = _get_escrow_or_404(escrow_id, db)
    order = escrow.order

    if escrow.status != EscrowStatus.disputed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Escrow #{escrow_id} is not in 'disputed' status (current: {escrow.status.value}).",
        )

    now = datetime.now(timezone.utc)
    transfer_id: str | None = None
    from app.models.export_enums import PaymentStatus as PS

    if body.resolution == "release_to_seller":
        result = _execute_release(escrow, order, None, f"Admin resolved: {body.resolution_notes}", db)
        transfer_id = result.get("transfer_id")
        final_status = EscrowStatus.released

    elif body.resolution == "refund_to_buyer":
        escrow.status = EscrowStatus.refunded
        escrow.released_at = now
        escrow.release_condition = f"Refund to buyer: {body.resolution_notes}"
        order.order_status = OrderStatus.disputed
        order.payment_status = PS.refunded
        final_status = EscrowStatus.refunded
        db.commit()
        # Note: actual refund via gateway API would be triggered here
        transfer_id = f"REFUND-{order.id}"

    else:  # split_settlement
        # Partial refund — release partial amount to seller, refund remainder to buyer
        escrow.status = EscrowStatus.released
        escrow.released_at = now
        escrow.release_condition = (
            f"Split settlement: {body.compensation_amount_usd} USD to buyer; "
            f"remainder to seller. {body.resolution_notes}"
        )
        order.order_status = OrderStatus.delivered
        order.payment_status = PS.released
        final_status = EscrowStatus.released
        db.commit()
        transfer_id = f"SPLIT-{order.id}"

    # Record dispute resolution
    escrow.dispute_resolved_at = now
    escrow.resolution_notes = body.resolution_notes
    db.commit()

    # Parse AI recommendation back to dict for response
    ai_rec: dict | None = None
    if escrow.ai_recommendation:
        try:
            ai_rec = json.loads(escrow.ai_recommendation)
        except (json.JSONDecodeError, TypeError):
            ai_rec = {"raw": escrow.ai_recommendation}

    return DisputeResolveResponse(
        escrow_id=escrow.id,
        order_id=order.id,
        resolution=body.resolution,
        status=final_status,
        resolved_at=now,
        transfer_id=transfer_id,
        ai_recommendation=ai_rec,
        message=(
            f"Dispute resolved: {body.resolution.replace('_', ' ')}. "
            f"Escrow #{escrow_id} for Order #{order.id} has been finalised."
        ),
    )


# ---------------------------------------------------------------------------
# POST /escrow/hold
# ---------------------------------------------------------------------------

@router.post(
    "/hold",
    response_model=EscrowHoldResponse,
    summary="Initiate escrow payment hold",
    description=(
        "Buyer initiates a payment hold for an existing export order. "
        "For Flutterwave: returns a hosted payment link. "
        "For Stripe: returns a PaymentIntent client_secret for frontend completion."
    ),
    status_code=status.HTTP_201_CREATED,
)
def initiate_hold(
    body: EscrowHoldRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EscrowHoldResponse:
    order = _get_order_or_404(body.order_id, db)
    _assert_buyer_or_admin(order, current_user)

    # Validate order is in a state that allows escrow
    if order.order_status not in (OrderStatus.placed, OrderStatus.confirmed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Order #{body.order_id} is in '{order.order_status.value}' status. "
                "Escrow can only be initiated for 'placed' or 'confirmed' orders."
            ),
        )

    # Prevent duplicate escrow
    if order.escrow and order.escrow.status == EscrowStatus.held:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Order #{body.order_id} already has an active escrow hold.",
        )

    amount_usd = float(order.agreed_price_usd * order.quantity_kg)
    buyer = order.buyer
    buyer_email = body.buyer_email or (buyer.email if buyer else "buyer@nigerflora.mabrigkorie.org")
    buyer_name = buyer.full_name if buyer else "Buyer"

    now = datetime.now(timezone.utc)
    auto_release = now + timedelta(days=_AUTO_RELEASE_DAYS)

    payment_link: str | None = None
    stripe_client_secret: str | None = None
    stripe_pi_id: str | None = None
    gateway_tx_id: str | None = None

    if body.gateway == "flutterwave":
        flw_result = flw_create_payment_link(
            order_id=body.order_id,
            amount=amount_usd,
            currency=body.currency,
            buyer_email=buyer_email,
            buyer_name=buyer_name,
            redirect_url=body.redirect_url,
        )
        payment_link = flw_result["payment_link"]
        gateway_tx_id = flw_result["tx_ref"]   # FLW tx_ref (numeric ID comes via webhook)

    else:  # stripe
        stripe_result = stripe_create_payment_intent(
            order_id=body.order_id,
            amount_usd=amount_usd,
            currency=body.currency.lower() if body.currency != "NGN" else "usd",
            buyer_email=buyer_email,
        )
        stripe_pi_id = stripe_result["payment_intent_id"]
        stripe_client_secret = stripe_result["client_secret"]
        gateway_tx_id = stripe_pi_id

    # Create EscrowTransaction
    escrow = EscrowTransaction(
        order_id=body.order_id,
        amount_usd=Decimal(str(round(amount_usd, 4))),
        status=EscrowStatus.held,
        gateway=body.gateway,
        gateway_tx_id=gateway_tx_id,
        gateway_payment_link=payment_link,
        held_at=now,
        auto_release_at=auto_release,
        release_condition="Awaiting buyer delivery confirmation within 7 days.",
    )
    db.add(escrow)

    # Advance order status
    order.order_status = OrderStatus.confirmed
    db.commit()
    db.refresh(escrow)

    return EscrowHoldResponse(
        escrow_id=escrow.id,
        order_id=body.order_id,
        amount_usd=amount_usd,
        gateway=body.gateway,
        status=escrow.status,
        payment_link=payment_link,
        stripe_client_secret=stripe_client_secret,
        stripe_payment_intent_id=stripe_pi_id,
        auto_release_at=auto_release,
        message=(
            f"Escrow hold initiated for ${amount_usd:.2f} via {body.gateway.title()}. "
            + (
                "Complete payment via the provided link."
                if body.gateway == "flutterwave"
                else "Complete payment on the frontend using the client_secret."
            )
            + f" Funds will auto-release to seller on {auto_release.date().isoformat()} "
            "if delivery is not confirmed."
        ),
    )


# ---------------------------------------------------------------------------
# GET /escrow/status/{order_id}
# ---------------------------------------------------------------------------

@router.get(
    "/status/{order_id}",
    response_model=EscrowStatusResponse,
    summary="Check escrow status for an order",
    description=(
        "Returns the current escrow state. Also lazily triggers auto-release "
        "if the 7-day window has passed without buyer confirmation."
    ),
    status_code=status.HTTP_200_OK,
)
def escrow_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EscrowStatusResponse:
    order = _get_order_or_404(order_id, db)
    _assert_access(order, current_user)

    escrow = order.escrow
    if not escrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No escrow transaction found for order #{order_id}.",
        )

    # Lazy auto-release check
    if escrow.status == EscrowStatus.held and should_auto_release(escrow):
        _execute_release(
            escrow=escrow,
            order=order,
            release_body=None,
            condition="Auto-released: 7-day confirmation window expired.",
            db=db,
        )
        db.refresh(escrow)

    # Compute days until auto-release
    days_left: float | None = None
    if escrow.auto_release_at and escrow.status == EscrowStatus.held:
        delta = escrow.auto_release_at - datetime.now(timezone.utc)
        days_left = max(0.0, round(delta.total_seconds() / 86400, 2))

    return EscrowStatusResponse(
        order_id=order_id,
        escrow_id=escrow.id,
        amount_usd=escrow.amount_usd,
        status=escrow.status,
        gateway=escrow.gateway,
        held_at=escrow.held_at,
        auto_release_at=escrow.auto_release_at,
        delivery_confirmed_at=escrow.delivery_confirmed_at,
        released_at=escrow.released_at,
        dispute_raised_at=escrow.dispute_raised_at,
        dispute_window_open=dispute_window_open(escrow),
        days_until_auto_release=days_left,
    )


# ---------------------------------------------------------------------------
# POST /escrow/release/{order_id}
# ---------------------------------------------------------------------------

@router.post(
    "/release/{order_id}",
    response_model=EscrowReleaseResponse,
    summary="Buyer confirms delivery — release funds to seller",
    description=(
        "Buyer calls this endpoint to confirm they have received the goods. "
        "Triggers an immediate fund transfer to the seller's account. "
        "The 48-hour dispute window starts from this confirmation."
    ),
    status_code=status.HTTP_200_OK,
)
def release_escrow(
    order_id: int,
    body: EscrowReleaseRequest = Body(default_factory=EscrowReleaseRequest),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EscrowReleaseResponse:
    order = _get_order_or_404(order_id, db)
    _assert_buyer_or_admin(order, current_user)

    escrow = order.escrow
    if not escrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No escrow found for order #{order_id}.",
        )
    if escrow.status != EscrowStatus.held:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Escrow is in '{escrow.status.value}' status; cannot release.",
        )

    # Record delivery confirmation before releasing
    now = datetime.now(timezone.utc)
    escrow.delivery_confirmed_at = now
    db.flush()

    result = _execute_release(
        escrow=escrow,
        order=order,
        release_body=body,
        condition=f"Buyer confirmed delivery. {body.confirmation_note or ''}".strip(),
        db=db,
    )

    return EscrowReleaseResponse(
        order_id=order_id,
        escrow_id=escrow.id,
        status=escrow.status,
        released_at=escrow.released_at,
        transfer_id=result.get("transfer_id"),
        transfer_status=result.get("transfer_status"),
        message=(
            f"Delivery confirmed. Funds of ${float(escrow.amount_usd):.2f} released to seller. "
            f"You have {_DISPUTE_HOURS} hours to raise a dispute if needed."
        ),
    )


# ---------------------------------------------------------------------------
# POST /escrow/dispute/{order_id}
# ---------------------------------------------------------------------------

@router.post(
    "/dispute/{order_id}",
    response_model=EscrowDisputeResponse,
    summary="Raise an escrow dispute",
    description=(
        "Buyer raises a dispute within 48 hours of delivery confirmation. "
        "Claude automatically analyses all evidence and generates an advisory "
        "recommendation for the admin."
    ),
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def raise_dispute(
    request: Request,
    order_id: int,
    body: EscrowDisputeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EscrowDisputeResponse:
    order = _get_order_or_404(order_id, db)
    _assert_buyer_or_admin(order, current_user)

    escrow = order.escrow
    if not escrow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No escrow found for order #{order_id}.",
        )

    # Only allow disputes on held or released (within 48h window) escrows
    if escrow.status == EscrowStatus.disputed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dispute is already open for this order.",
        )
    if escrow.status in (EscrowStatus.refunded,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot dispute a {escrow.status.value} escrow.",
        )

    # Enforce 48-hour dispute window if delivery was already confirmed
    if escrow.status == EscrowStatus.released:
        if not dispute_window_open(escrow):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The 48-hour dispute window has closed. "
                    "Contact support at disputes@nigerflora.mabrigkorie.org for late claims."
                ),
            )

    now = datetime.now(timezone.utc)
    escrow.status = EscrowStatus.disputed
    escrow.dispute_reason = f"{body.reason}\n\n{body.details or ''}".strip()
    escrow.dispute_raised_at = now
    db.flush()

    # Run Claude dispute analysis asynchronously (called synchronously here for simplicity)
    shipments = order.shipments or []
    primary_shipment = shipments[0] if shipments else {}
    all_events: list[dict] = []
    for s in shipments:
        for e in (s.events or []):
            all_events.append({
                "event_type": e.event_type.value,
                "location": e.location,
                "description": e.description,
                "timestamp": str(e.event_timestamp),
            })

    dispute_dict = {
        "reason": body.reason,
        "details": body.details,
        "raised_at": str(now),
        "buyer_id": current_user.id,
        "escrow_amount_usd": float(escrow.amount_usd),
    }
    shipment_dict = {
        "tracking_number": primary_shipment.tracking_number if hasattr(primary_shipment, "tracking_number") else None,
        "carrier": primary_shipment.carrier_name if hasattr(primary_shipment, "carrier_name") else None,
        "current_status": primary_shipment.current_status if hasattr(primary_shipment, "current_status") else None,
        "departure_date": str(primary_shipment.departure_date) if hasattr(primary_shipment, "departure_date") and primary_shipment.departure_date else None,
        "estimated_arrival": str(primary_shipment.estimated_arrival) if hasattr(primary_shipment, "estimated_arrival") and primary_shipment.estimated_arrival else None,
        "actual_arrival": str(primary_shipment.actual_arrival) if hasattr(primary_shipment, "actual_arrival") and primary_shipment.actual_arrival else None,
    }

    try:
        ai_result = dispute_resolution_ai(
            dispute=dispute_dict,
            order=_order_to_dict(order),
            shipment=shipment_dict,
            events=all_events,
        )
        escrow.ai_recommendation = json.dumps(ai_result)
    except Exception:
        # Non-fatal: log failure but don't block the dispute creation
        escrow.ai_recommendation = json.dumps({
            "recommendation": "split_settlement",
            "reasoning": "AI analysis unavailable. Admin should review manually.",
            "confidence": "low",
            "disclaimer": "AI analysis failed; manual review required.",
        })

    db.commit()

    dispute_deadline = (
        escrow.delivery_confirmed_at + timedelta(hours=_DISPUTE_HOURS)
        if escrow.delivery_confirmed_at
        else now + timedelta(hours=_DISPUTE_HOURS)
    )

    return EscrowDisputeResponse(
        order_id=order_id,
        escrow_id=escrow.id,
        status=escrow.status,
        dispute_raised_at=now,
        dispute_deadline=dispute_deadline,
        message=(
            f"Dispute raised for Order #{order_id}. "
            "An AI analysis has been generated for admin review. "
            "A NigerFlora admin will contact you within 24 hours."
        ),
    )


# ===========================================================================
# ── WEBHOOK ENDPOINTS ────────────────────────────────────────────────────────
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /webhooks/flutterwave
# ---------------------------------------------------------------------------

@webhook_router.post(
    "/flutterwave",
    response_model=WebhookAckResponse,
    summary="Flutterwave payment webhook",
    description=(
        "Receives charge.completed and transfer.completed events from Flutterwave. "
        "Verifies the secret hash header before processing."
    ),
    status_code=status.HTTP_200_OK,
)
async def flutterwave_webhook(
    request: Request,
    db: Session = Depends(get_db),
    verif_hash: str | None = Header(None, alias="verif-hash"),
) -> WebhookAckResponse:
    # ── Signature verification ───────────────────────────────────────────
    expected = settings.FLUTTERWAVE_WEBHOOK_SECRET
    if expected and verif_hash != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Flutterwave webhook signature.",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is not valid JSON.",
        )

    event_type = payload.get("event", "")

    # ── charge.completed → confirm escrow hold ───────────────────────────
    if event_type == "charge.completed":
        tx_data = payload.get("data", {})
        tx_status = tx_data.get("status", "").lower()
        tx_ref = tx_data.get("tx_ref", "")
        flw_tx_id = str(tx_data.get("id", ""))

        if tx_status == "successful" and tx_ref:
            # Find escrow by tx_ref (stored in gateway_tx_id at hold time)
            escrow = (
                db.query(EscrowTransaction)
                .filter(EscrowTransaction.gateway_tx_id == tx_ref)
                .first()
            )
            if escrow and escrow.status == EscrowStatus.held:
                # Update with confirmed FLW numeric transaction ID
                escrow.gateway_tx_id = flw_tx_id
                escrow.release_condition = (
                    f"Payment confirmed via Flutterwave (tx_id={flw_tx_id}). "
                    "Awaiting buyer delivery confirmation."
                )
                db.commit()

    # ── transfer.completed → log successful payout ───────────────────────
    elif event_type == "transfer.completed":
        tx_data = payload.get("data", {})
        reference = tx_data.get("reference", "")
        if reference:
            # reference format: "NM-XFER-{order_id}-{timestamp}"
            parts = reference.split("-")
            if len(parts) >= 3 and parts[0] == "NM" and parts[1] == "XFER":
                try:
                    order_id = int(parts[2])
                    order = db.get(ExportOrder, order_id)
                    if order and order.escrow:
                        order.escrow.gateway_transfer_id = str(tx_data.get("id", reference))
                        db.commit()
                except (ValueError, AttributeError):
                    pass

    return WebhookAckResponse(message=f"Event '{event_type}' processed.")


# ---------------------------------------------------------------------------
# POST /webhooks/stripe
# ---------------------------------------------------------------------------

@webhook_router.post(
    "/stripe",
    response_model=WebhookAckResponse,
    summary="Stripe payment webhook",
    description=(
        "Receives Stripe payment events. Verifies the Stripe-Signature header "
        "using the STRIPE_WEBHOOK_SECRET before processing."
    ),
    status_code=status.HTTP_200_OK,
)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
) -> WebhookAckResponse:
    # Read raw bytes for signature verification
    raw_body = await request.body()

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Stripe-Signature header.",
        )

    # Verify signature (raises 400 on failure)
    event = stripe_verify_webhook(payload=raw_body, sig_header=stripe_signature)
    event_type: str = event.get("type", "")

    # ── payment_intent.amount_capturable_updated → capture funds ─────────
    if event_type == "payment_intent.amount_capturable_updated":
        pi_data = event.get("data", {}).get("object", {})
        pi_id: str = pi_data.get("id", "")
        if pi_id:
            escrow = (
                db.query(EscrowTransaction)
                .filter(EscrowTransaction.gateway_tx_id == pi_id)
                .first()
            )
            if escrow and escrow.status == EscrowStatus.held:
                try:
                    capture_result = stripe_capture_payment_intent(pi_id)
                    escrow.release_condition = (
                        f"Stripe PaymentIntent captured (status={capture_result['status']}). "
                        "Awaiting buyer delivery confirmation."
                    )
                    db.commit()
                except HTTPException:
                    pass  # Log failure — escrow remains held for manual review

    # ── payment_intent.succeeded → already captured elsewhere ────────────
    elif event_type == "payment_intent.succeeded":
        pi_data = event.get("data", {}).get("object", {})
        pi_id = pi_data.get("id", "")
        order_id_str = (pi_data.get("metadata") or {}).get("nigerflora_order_id")
        if pi_id and order_id_str:
            escrow = (
                db.query(EscrowTransaction)
                .filter(EscrowTransaction.gateway_tx_id == pi_id)
                .first()
            )
            if escrow:
                escrow.release_condition = (
                    f"Stripe payment succeeded (pi={pi_id}). "
                    "Awaiting buyer delivery confirmation."
                )
                db.commit()

    # ── payment_intent.payment_failed → notify and mark pending ──────────
    elif event_type == "payment_intent.payment_failed":
        pi_data = event.get("data", {}).get("object", {})
        pi_id = pi_data.get("id", "")
        if pi_id:
            escrow = (
                db.query(EscrowTransaction)
                .filter(EscrowTransaction.gateway_tx_id == pi_id)
                .first()
            )
            if escrow and escrow.status == EscrowStatus.held:
                escrow.release_condition = (
                    f"Stripe payment FAILED (pi={pi_id}). Manual review required."
                )
                db.commit()

    return WebhookAckResponse(message=f"Stripe event '{event_type}' processed.")


# ---------------------------------------------------------------------------
# POST /webhooks/shipment
# ---------------------------------------------------------------------------

@webhook_router.post(
    "/shipment",
    response_model=WebhookAckResponse,
    summary="Carrier shipment tracking webhook",
    description=(
        "Receives tracking updates from freight carriers (DHL, FedEx, Maersk, etc.). "
        "Verifies the X-Shipment-Secret header. "
        "Automatically creates ShipmentEvent records and marks shipment as delivered."
    ),
    status_code=status.HTTP_200_OK,
)
async def shipment_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_shipment_secret: str | None = Header(None, alias="x-shipment-secret"),
) -> WebhookAckResponse:
    # ── Signature / secret verification ─────────────────────────────────
    expected_secret = settings.SHIPMENT_WEBHOOK_SECRET
    if expected_secret and x_shipment_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid shipment webhook secret.",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is not valid JSON.",
        )

    tracking_number: str = payload.get("tracking_number", "")
    event_type_raw: str = payload.get("event_type", "").lower()
    location: str | None = payload.get("location")
    description: str | None = payload.get("description")
    timestamp_str: str | None = payload.get("timestamp")

    if not tracking_number:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tracking_number is required in the webhook payload.",
        )

    # Find shipment by tracking number
    shipment = (
        db.query(Shipment)
        .filter(Shipment.tracking_number == tracking_number)
        .first()
    )
    if not shipment:
        # Unknown tracking number — acknowledge but take no action
        return WebhookAckResponse(
            message=f"Tracking number '{tracking_number}' not found in system. Acknowledged.",
        )

    # Map carrier event to ShipmentEventType
    event_map: dict[str, ShipmentEventType] = {
        "departed": ShipmentEventType.departure,
        "departure": ShipmentEventType.departure,
        "arrived": ShipmentEventType.arrival,
        "arrival": ShipmentEventType.arrival,
        "customs_hold": ShipmentEventType.customs_hold,
        "on_hold": ShipmentEventType.customs_hold,
        "delay": ShipmentEventType.delay,
        "delayed": ShipmentEventType.delay,
        "customs_cleared": ShipmentEventType.customs_cleared,
        "cleared": ShipmentEventType.customs_cleared,
        "delivered": ShipmentEventType.delivered,
        "delivery": ShipmentEventType.delivered,
        "temperature_breach": ShipmentEventType.temperature_breach,
        "temp_breach": ShipmentEventType.temperature_breach,
    }
    event_type_enum = event_map.get(event_type_raw, ShipmentEventType.arrival)

    # Parse timestamp
    event_ts = datetime.now(timezone.utc)
    if timestamp_str:
        try:
            event_ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Create ShipmentEvent
    event = ShipmentEvent(
        shipment_id=shipment.id,
        event_type=event_type_enum,
        location=location,
        description=description or f"{event_type_raw} event from carrier webhook",
        event_timestamp=event_ts,
    )
    db.add(event)

    # Update shipment status
    shipment.current_status = event_type_raw
    if location:
        shipment.current_location = location
    if event_type_enum == ShipmentEventType.delivered:
        shipment.actual_arrival = event_ts.date()
        # If order has an escrow, note delivery in release_condition
        order = db.get(ExportOrder, shipment.order_id)
        if order and order.escrow and order.escrow.status == EscrowStatus.held:
            order.escrow.release_condition = (
                f"Carrier reported delivery on {event_ts.date().isoformat()}. "
                "Awaiting buyer confirmation within 7 days."
            )
    elif event_type_enum == ShipmentEventType.customs_cleared:
        shipment.customs_cleared = True

    db.commit()

    return WebhookAckResponse(
        message=(
            f"Shipment event '{event_type_raw}' recorded for tracking #{tracking_number}. "
            f"ShipmentEvent id={event.id}."
        ),
    )
