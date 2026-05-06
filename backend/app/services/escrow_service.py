"""
Escrow Service — payment gateway integration and AI-powered dispute resolution.

Escrow lifecycle:
  1. Buyer initiates hold  → Flutterwave payment link OR Stripe PaymentIntent created
  2. Payment captured      → EscrowTransaction.status = "held"; gateway_tx_id stored
  3. Seller ships          → uploads tracking number via /logistics/shipments
  4. Buyer confirms        → POST /escrow/release/{order_id} → funds transferred to seller
  5. Auto-release (day 7)  → if buyer hasn't confirmed, held_at+7 days triggers release
  6. Dispute window        → 48 h after delivery_confirmed_at; buyer can POST /escrow/dispute

Payment gateways
  Flutterwave (httpx)  — preferred for NGN / African buyers; hosted payment link
  Stripe (stripe SDK)  — preferred for USD / EUR international buyers; PaymentIntent

Dispute AI (Claude)
  dispute_resolution_ai() — advisory only; human admin makes final decision
"""
import json
import re
import time
from typing import Any

import httpx
from fastapi import HTTPException, status

from ..core.config import settings


# ---------------------------------------------------------------------------
# ── Shared helpers ──────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

def _require_key(key: str, gateway: str) -> str:
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"{gateway} API key is not configured. "
                f"Set the corresponding key in .env."
            ),
        )
    return key


# ===========================================================================
# ── Flutterwave ─────────────────────────────────────────────────────────────
# ===========================================================================

def _flw_headers() -> dict[str, str]:
    key = _require_key(settings.FLUTTERWAVE_SECRET_KEY, "Flutterwave")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _flw_post(path: str, payload: dict) -> dict[str, Any]:
    url = f"{settings.FLUTTERWAVE_BASE_URL}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=_flw_headers())
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave error {exc.response.status_code}: {exc.response.text[:400]}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave request failed: {exc}",
        )


def _flw_get(path: str) -> dict[str, Any]:
    url = f"{settings.FLUTTERWAVE_BASE_URL}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=_flw_headers())
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave error {exc.response.status_code}: {exc.response.text[:400]}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave request failed: {exc}",
        )


def flw_create_payment_link(
    order_id: int,
    amount: float,
    currency: str,
    buyer_email: str,
    buyer_name: str,
    redirect_url: str | None = None,
) -> dict[str, Any]:
    """
    Create a Flutterwave Standard (hosted) payment link for an escrow hold.
    Returns {"payment_link": str, "tx_ref": str}.
    """
    tx_ref = f"NM-ESC-{order_id}-{int(time.time())}"
    payload = {
        "tx_ref": tx_ref,
        "amount": amount,
        "currency": currency.upper(),
        "redirect_url": redirect_url or "https://naijamed.ai/escrow/callback",
        "customer": {
            "email": buyer_email,
            "name": buyer_name,
        },
        "customizations": {
            "title": "NaijaMed Export Escrow",
            "description": f"Secure payment for Order #{order_id}",
            "logo": "https://naijamed.ai/logo.png",
        },
        "meta": {
            "naijamed_order_id": order_id,
            "naijamed_type": "escrow_hold",
        },
    }
    data = _flw_post("/payments", payload)
    if data.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave payment link failed: {data.get('message')}",
        )
    return {"payment_link": data["data"]["link"], "tx_ref": tx_ref}


def flw_verify_transaction(flw_tx_id: str) -> dict[str, Any]:
    """
    Verify a Flutterwave transaction by its numeric ID.
    Returns the full transaction object from FLW.
    """
    data = _flw_get(f"/transactions/{flw_tx_id}/verify")
    if data.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave verification failed: {data.get('message')}",
        )
    return data.get("data", {})


def flw_transfer_to_seller(
    order_id: int,
    amount: float,
    account_bank: str,       # Nigerian bank code e.g. "044" (Access Bank)
    account_number: str,
    narration: str | None = None,
    currency: str = "NGN",
    debit_currency: str = "USD",
) -> dict[str, Any]:
    """
    Initiate a bank transfer to the seller's account via Flutterwave Payouts.
    For NGN transfers, amount is converted from USD at FLW's current rate.
    Returns the transfer object {"id": ..., "reference": ..., "status": ...}.
    """
    reference = f"NM-XFER-{order_id}-{int(time.time())}"
    payload = {
        "account_bank": account_bank,
        "account_number": account_number,
        "amount": amount,
        "narration": narration or f"NaijaMed escrow release — Order #{order_id}",
        "currency": currency.upper(),
        "reference": reference,
        "debit_currency": debit_currency.upper(),
        "meta": [{"sender": "NaijaMed AI", "sender_country": "NG", "mobile_number": ""}],
    }
    data = _flw_post("/transfers", payload)
    if data.get("status") not in ("success", "NEW"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Flutterwave transfer failed: {data.get('message')}",
        )
    return {
        "transfer_id": str(data.get("data", {}).get("id", reference)),
        "reference": reference,
        "status": data.get("data", {}).get("status", "NEW"),
    }


# ===========================================================================
# ── Stripe ──────────────────────────────────────────────────────────────────
# ===========================================================================

def _get_stripe():
    """Import stripe SDK and configure API key. Raises 503 if key not set."""
    _require_key(settings.STRIPE_SECRET_KEY, "Stripe")
    try:
        import stripe as _stripe
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="stripe package is not installed. Run: pip install stripe",
        )
    _stripe.api_key = settings.STRIPE_SECRET_KEY
    return _stripe


def stripe_create_payment_intent(
    order_id: int,
    amount_usd: float,
    currency: str = "usd",
    buyer_email: str | None = None,
) -> dict[str, Any]:
    """
    Create a Stripe PaymentIntent with capture_method='manual' (escrow hold).
    The buyer completes payment on the frontend using the returned client_secret.
    Funds are not captured until stripe_capture_payment_intent() is called.
    Returns {"payment_intent_id": str, "client_secret": str, "amount_usd": float}.
    """
    stripe = _get_stripe()
    amount_cents = int(round(amount_usd * 100))

    kwargs: dict[str, Any] = {
        "amount": amount_cents,
        "currency": currency.lower(),
        "capture_method": "manual",        # hold without capturing
        "description": f"NaijaMed escrow hold — Order #{order_id}",
        "metadata": {
            "naijamed_order_id": str(order_id),
            "naijamed_type": "escrow_hold",
        },
    }
    if buyer_email:
        kwargs["receipt_email"] = buyer_email

    try:
        intent = stripe.PaymentIntent.create(**kwargs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe PaymentIntent creation failed: {exc}",
        )

    return {
        "payment_intent_id": intent.id,
        "client_secret": intent.client_secret,
        "amount_usd": amount_usd,
        "currency": currency.lower(),
        "status": intent.status,
    }


def stripe_capture_payment_intent(payment_intent_id: str) -> dict[str, Any]:
    """
    Capture a previously authorised PaymentIntent (confirm funds are held).
    Called when the webhook signals payment_intent.amount_capturable_updated.
    """
    stripe = _get_stripe()
    try:
        intent = stripe.PaymentIntent.capture(payment_intent_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe capture failed: {exc}",
        )
    return {
        "payment_intent_id": intent.id,
        "status": intent.status,
        "amount_usd": intent.amount_received / 100,
    }


def stripe_transfer_to_seller(
    order_id: int,
    amount_usd: float,
    seller_stripe_account_id: str,
    currency: str = "usd",
) -> dict[str, Any]:
    """
    Transfer captured funds to the seller's Stripe Connected Account.
    seller_stripe_account_id: "acct_XXXX" — stored in the seller's profile.
    """
    stripe = _get_stripe()
    amount_cents = int(round(amount_usd * 100))
    try:
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency=currency.lower(),
            destination=seller_stripe_account_id,
            transfer_group=f"NM-ESC-{order_id}",
            description=f"NaijaMed escrow release — Order #{order_id}",
            metadata={"naijamed_order_id": str(order_id)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe transfer failed: {exc}",
        )
    return {
        "transfer_id": transfer.id,
        "amount_usd": amount_usd,
        "destination": seller_stripe_account_id,
        "status": "created",
    }


def stripe_verify_webhook(
    payload: bytes,
    sig_header: str,
) -> dict[str, Any]:
    """
    Verify a Stripe webhook signature and return the parsed event.
    Raises 400 if signature is invalid.
    """
    stripe = _get_stripe()
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STRIPE_WEBHOOK_SECRET is not configured.",
        )
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe webhook signature invalid: {exc}",
        )
    return dict(event)


# ===========================================================================
# ── Claude — Dispute Resolution AI ──────────────────────────────────────────
# ===========================================================================

_DISPUTE_PROMPT = """
You are a neutral escrow dispute resolution specialist for NaijaMed AI,
a Nigerian herb export marketplace connecting African farmers with global buyers.

Your role is ADVISORY ONLY. A human admin will review your recommendation
before any funds are moved.

Review the following dispute case carefully:

═══ DISPUTE DETAILS ════════════════════════════════════════════════════════
{dispute}

═══ ORDER DETAILS ══════════════════════════════════════════════════════════
{order}

═══ SHIPMENT DETAILS ═══════════════════════════════════════════════════════
{shipment}

═══ SHIPMENT EVENT TIMELINE ════════════════════════════════════════════════
{events}

Analyse the evidence and consider:
1. CONTRACT FULFILMENT — Was the agreed product, quantity, and quality delivered?
2. DELIVERY EVIDENCE — Do shipment events confirm delivery? Is tracking consistent?
3. TIMING — Was delivery made within the agreed timeframe?
4. BUYER LEGITIMACY — Does the dispute reason have merit based on the evidence?
   Is there any sign of buyer fraud (confirming receipt then disputing)?
5. SELLER LEGITIMACY — Is there evidence the seller shipped what was promised?
   Any temperature breaches, customs holds, or unexplained gaps in events?
6. FAIR OUTCOME — What resolution is most equitable given all facts?

Possible recommendations:
  "release_to_seller"  — evidence clearly shows fulfilment; buyer's claim not supported
  "refund_to_buyer"    — evidence shows non-delivery, wrong goods, or serious breach
  "split_settlement"   — partial fault on both sides; specify the split percentage

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "recommendation": "<release_to_seller|refund_to_buyer|split_settlement>",
  "reasoning": "<2-3 paragraph explanation citing specific evidence from the case>",
  "evidence_cited": [
    "<specific finding 1 — e.g. 'ShipmentEvent: delivered at 14:32 on 2025-03-15'>",
    "<specific finding 2>",
    "<specific finding 3>"
  ],
  "confidence": "<high|medium|low>",
  "compensation_amount_usd": <float if partial refund is applicable, else null>,
  "settlement_split": {{"seller_pct": 70, "buyer_pct": 30}} | null,
  "key_factors_favoring_seller": ["<factor 1>", "<factor 2>"],
  "key_factors_favoring_buyer": ["<factor 1>", "<factor 2>"],
  "recommended_action": "<specific next step for the admin — e.g. 'Request photo evidence from buyer before deciding'>",
  "disclaimer": "This is an AI advisory recommendation. Final decision rests with the NaijaMed admin."
}}
"""


def _get_claude_client():
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env.",
        )
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_claude_json(prompt: str, max_tokens: int = 2000) -> Any:
    client = _get_claude_client()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        )
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude returned non-JSON: {exc}. Raw: {raw[:300]}",
        )


def dispute_resolution_ai(
    dispute: dict[str, Any],
    order: dict[str, Any],
    shipment: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Claude reviews all evidence and returns an ADVISORY recommendation.
    Final decision is always made by a human admin.

    Returns dict with keys:
      recommendation, reasoning, evidence_cited, confidence,
      compensation_amount_usd, settlement_split,
      key_factors_favoring_seller, key_factors_favoring_buyer,
      recommended_action, disclaimer
    """
    prompt = _DISPUTE_PROMPT.format(
        dispute=json.dumps(dispute, indent=2, default=str),
        order=json.dumps(order, indent=2, default=str),
        shipment=json.dumps(shipment, indent=2, default=str),
        events=json.dumps(events, indent=2, default=str),
    )
    result = _call_claude_json(prompt, max_tokens=2000)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Claude returned unexpected structure for dispute analysis.",
        )

    # Safety defaults
    result.setdefault("recommendation", "split_settlement")
    result.setdefault("reasoning", "Insufficient evidence for a clear determination.")
    result.setdefault("evidence_cited", [])
    result.setdefault("confidence", "low")
    result.setdefault("compensation_amount_usd", None)
    result.setdefault("settlement_split", None)
    result.setdefault("key_factors_favoring_seller", [])
    result.setdefault("key_factors_favoring_buyer", [])
    result.setdefault("recommended_action", "Request additional evidence from both parties.")
    result.setdefault(
        "disclaimer",
        "This is an AI advisory recommendation. Final decision rests with the NaijaMed admin.",
    )
    return result


# ===========================================================================
# ── Pure-logic helpers ───────────────────────────────────────────────────────
# ===========================================================================

def should_auto_release(escrow: Any) -> bool:
    """
    Returns True if the escrow's auto-release date has passed and funds
    have not yet been released.
    Called on every GET /escrow/status/{order_id} to lazily trigger release.
    """
    from datetime import datetime, timezone
    if escrow.status != "held":
        return False
    if escrow.auto_release_at is None:
        return False
    now = datetime.now(timezone.utc)
    return now >= escrow.auto_release_at


def dispute_window_open(escrow: Any) -> bool:
    """
    Returns True if the 48-hour dispute window after delivery confirmation
    is still open.
    """
    from datetime import datetime, timedelta, timezone
    if escrow.delivery_confirmed_at is None:
        # Can't dispute an unconfirmed delivery
        return False
    deadline = escrow.delivery_confirmed_at + timedelta(hours=48)
    return datetime.now(timezone.utc) <= deadline
