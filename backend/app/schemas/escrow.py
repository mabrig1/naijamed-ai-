from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.export_enums import EscrowStatus, PaymentMethod


# ---------------------------------------------------------------------------
# Shared read model
# ---------------------------------------------------------------------------

class EscrowTransactionRead(BaseModel):
    id: int
    order_id: int
    amount_usd: Decimal
    status: EscrowStatus
    gateway: str | None = None
    gateway_tx_id: str | None = None
    gateway_transfer_id: str | None = None
    gateway_payment_link: str | None = None
    held_at: datetime
    delivery_confirmed_at: datetime | None = None
    auto_release_at: datetime | None = None
    released_at: datetime | None = None
    release_condition: str | None = None
    dispute_reason: str | None = None
    dispute_raised_at: datetime | None = None
    dispute_resolved_at: datetime | None = None
    ai_recommendation: str | None = None   # raw JSON string from Claude
    resolution_notes: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 1. POST /escrow/hold — buyer initiates escrow payment
# ---------------------------------------------------------------------------

class EscrowHoldRequest(BaseModel):
    order_id: int
    gateway: str = "flutterwave"      # "flutterwave" | "stripe"
    currency: str = "USD"
    redirect_url: str | None = None   # FLW redirect after payment
    buyer_email: str | None = None    # required for FLW / used as Stripe receipt email

    model_config = {"str_strip_whitespace": True}

    @field_validator("gateway")
    @classmethod
    def valid_gateway(cls, v: str) -> str:
        allowed = {"flutterwave", "stripe"}
        v = v.lower().strip()
        if v not in allowed:
            raise ValueError(f"gateway must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, v: str) -> str:
        allowed = {"USD", "EUR", "GBP", "NGN"}
        v = v.upper().strip()
        if v not in allowed:
            raise ValueError(f"currency must be one of: {', '.join(sorted(allowed))}")
        return v


class EscrowHoldResponse(BaseModel):
    escrow_id: int
    order_id: int
    amount_usd: float
    gateway: str
    status: EscrowStatus
    # Flutterwave: hosted payment page URL
    payment_link: str | None = None
    # Stripe: complete on frontend with stripe.js
    stripe_client_secret: str | None = None
    stripe_payment_intent_id: str | None = None
    auto_release_at: datetime
    message: str


# ---------------------------------------------------------------------------
# 2. GET /escrow/status/{order_id}
# ---------------------------------------------------------------------------

class EscrowStatusResponse(BaseModel):
    order_id: int
    escrow_id: int
    amount_usd: Decimal
    status: EscrowStatus
    gateway: str | None
    held_at: datetime
    auto_release_at: datetime | None
    delivery_confirmed_at: datetime | None
    released_at: datetime | None
    dispute_raised_at: datetime | None
    dispute_window_open: bool
    # Computed: days remaining before auto-release (None if already released)
    days_until_auto_release: float | None = None


# ---------------------------------------------------------------------------
# 3. POST /escrow/release/{order_id} — buyer confirms delivery
# ---------------------------------------------------------------------------

class EscrowReleaseRequest(BaseModel):
    """
    Optional seller bank details for Flutterwave payout.
    For Stripe, provide seller_stripe_account_id.
    If omitted, release is logged but transfer is marked as 'manual_required'.
    """
    # Flutterwave NGN payout
    seller_bank_code: str | None = None         # e.g. "044" for Access Bank
    seller_account_number: str | None = None
    seller_account_currency: str = "NGN"

    # Stripe connected account payout
    seller_stripe_account_id: str | None = None  # "acct_XXXX"

    confirmation_note: str | None = None          # buyer's optional note

    model_config = {"str_strip_whitespace": True}


class EscrowReleaseResponse(BaseModel):
    order_id: int
    escrow_id: int
    status: EscrowStatus
    released_at: datetime
    transfer_id: str | None = None
    transfer_status: str | None = None
    message: str


# ---------------------------------------------------------------------------
# 4. POST /escrow/dispute/{order_id}
# ---------------------------------------------------------------------------

class EscrowDisputeRequest(BaseModel):
    reason: str
    details: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("reason")
    @classmethod
    def non_empty_reason(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("reason must be at least 10 characters.")
        return v


class EscrowDisputeResponse(BaseModel):
    order_id: int
    escrow_id: int
    status: EscrowStatus
    dispute_raised_at: datetime
    dispute_deadline: datetime     # delivery_confirmed_at + 48 h
    message: str


# ---------------------------------------------------------------------------
# 5. GET /escrow/disputes (admin)
# ---------------------------------------------------------------------------

class DisputeListItem(BaseModel):
    escrow_id: int
    order_id: int
    amount_usd: Decimal
    dispute_reason: str | None
    dispute_raised_at: datetime | None
    dispute_resolved_at: datetime | None
    ai_recommendation_summary: str | None  # first 200 chars of AI JSON
    resolution_notes: str | None
    gateway: str | None
    status: EscrowStatus

    model_config = {"from_attributes": True}


class DisputesListResponse(BaseModel):
    count: int
    disputes: list[DisputeListItem]


# ---------------------------------------------------------------------------
# 6. POST /escrow/disputes/{id}/resolve (admin)
# ---------------------------------------------------------------------------

class DisputeResolveRequest(BaseModel):
    resolution: str   # "release_to_seller" | "refund_to_buyer" | "split_settlement"
    resolution_notes: str
    compensation_amount_usd: float | None = None   # for split_settlement

    model_config = {"str_strip_whitespace": True}

    @field_validator("resolution")
    @classmethod
    def valid_resolution(cls, v: str) -> str:
        allowed = {"release_to_seller", "refund_to_buyer", "split_settlement"}
        if v not in allowed:
            raise ValueError(f"resolution must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("resolution_notes")
    @classmethod
    def non_empty_notes(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("resolution_notes must be at least 10 characters.")
        return v


class DisputeResolveResponse(BaseModel):
    escrow_id: int
    order_id: int
    resolution: str
    status: EscrowStatus
    resolved_at: datetime
    transfer_id: str | None = None
    ai_recommendation: dict[str, Any] | None = None
    message: str


# ---------------------------------------------------------------------------
# 7. GET /escrow/my-transactions
# ---------------------------------------------------------------------------

class MyTransactionsResponse(BaseModel):
    user_id: int
    count: int
    transactions: list[EscrowTransactionRead]


# ---------------------------------------------------------------------------
# Webhook schemas (inbound events from gateways / carriers)
# ---------------------------------------------------------------------------

class WebhookAckResponse(BaseModel):
    received: bool = True
    message: str = "ok"


class ShipmentWebhookEvent(BaseModel):
    """Carrier-agnostic shipment tracking update."""
    tracking_number: str
    event_type: str          # "departed" | "arrived" | "customs_hold" | "delivered" | etc.
    location: str | None = None
    description: str | None = None
    timestamp: str | None = None   # ISO datetime string from carrier
    carrier: str | None = None
