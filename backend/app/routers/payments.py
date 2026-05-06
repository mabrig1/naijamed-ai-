"""
Paystack payment integration for NaijaMed AI marketplace.

Uses httpx (sync) to call the Paystack REST API.
All amounts are in kobo (100 kobo = ₦1).
"""
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from app.core.config import settings
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole

router = APIRouter()

# ---------------------------------------------------------------------------
# Paystack helper
# ---------------------------------------------------------------------------

def _paystack_headers() -> dict[str, str]:
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paystack secret key is not configured. Set PAYSTACK_SECRET_KEY in .env.",
        )
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _paystack_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{settings.PAYSTACK_BASE_URL}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=_paystack_headers())
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack error {exc.response.status_code}: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack request failed: {exc}",
        )


def _paystack_get(path: str) -> dict[str, Any]:
    url = f"{settings.PAYSTACK_BASE_URL}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=_paystack_headers())
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack error {exc.response.status_code}: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack request failed: {exc}",
        )


# ---------------------------------------------------------------------------
# Request / response schemas (small enough to live in-module)
# ---------------------------------------------------------------------------

class PaymentInitiateRequest(BaseModel):
    """Initiate a one-off marketplace transaction."""
    email: EmailStr
    amount_kobo: int
    listing_id: int | None = None
    callback_url: str | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("amount_kobo")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount_kobo must be greater than 0")
        return v


class PaymentInitiateResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str


class PaymentVerifyResponse(BaseModel):
    reference: str
    status: str
    amount_kobo: int
    currency: str
    paid_at: str | None
    customer_email: str | None
    gateway_response: str | None


class SubscriptionInitiateRequest(BaseModel):
    """Initiate a recurring subscription via a Paystack plan code."""
    email: EmailStr
    plan_code: str
    callback_url: str | None = None
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/initiate",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a Paystack payment for a marketplace transaction",
)
def initiate_payment(
    body: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
):
    payload: dict[str, Any] = {
        "email": body.email,
        "amount": body.amount_kobo,
        "currency": "NGN",
        "metadata": {
            **(body.metadata or {}),
            "naijamed_user_id": current_user.id,
            "listing_id": body.listing_id,
        },
    }
    if body.callback_url:
        payload["callback_url"] = body.callback_url

    data = _paystack_post("/transaction/initialize", payload)

    if not data.get("status"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack initialization failed: {data.get('message')}",
        )

    inner = data["data"]
    return PaymentInitiateResponse(
        authorization_url=inner["authorization_url"],
        access_code=inner["access_code"],
        reference=inner["reference"],
    )


@router.get(
    "/verify/{reference}",
    response_model=PaymentVerifyResponse,
    summary="Verify a Paystack payment by transaction reference",
)
def verify_payment(
    reference: str,
    _: User = Depends(get_current_user),
):
    data = _paystack_get(f"/transaction/verify/{reference}")

    if not data.get("status"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack verification failed: {data.get('message')}",
        )

    inner = data["data"]
    customer = inner.get("customer") or {}

    return PaymentVerifyResponse(
        reference=inner.get("reference", reference),
        status=inner.get("status", "unknown"),
        amount_kobo=inner.get("amount", 0),
        currency=inner.get("currency", "NGN"),
        paid_at=inner.get("paid_at"),
        customer_email=customer.get("email"),
        gateway_response=inner.get("gateway_response"),
    )


@router.post(
    "/subscription",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a recurring subscription payment via Paystack plan",
)
def initiate_subscription(
    body: SubscriptionInitiateRequest,
    current_user: User = Depends(
        require_role(UserRole.farmer, UserRole.researcher, UserRole.pharma_company, UserRole.admin)
    ),
):
    payload: dict[str, Any] = {
        "email": body.email,
        "plan": body.plan_code,
        "metadata": {
            **(body.metadata or {}),
            "naijamed_user_id": current_user.id,
            "naijamed_user_role": current_user.role.value,
        },
    }
    if body.callback_url:
        payload["callback_url"] = body.callback_url

    data = _paystack_post("/transaction/initialize", payload)

    if not data.get("status"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Paystack subscription initiation failed: {data.get('message')}",
        )

    inner = data["data"]
    return PaymentInitiateResponse(
        authorization_url=inner["authorization_url"],
        access_code=inner["access_code"],
        reference=inner["reference"],
    )
