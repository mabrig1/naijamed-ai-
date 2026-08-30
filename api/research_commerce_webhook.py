from __future__ import annotations

import hashlib
import hmac
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.mongo import get_db

app = FastAPI(title="NigerFlora Research Commerce Webhooks", version="1.0.0")


def now() -> datetime:
    return datetime.now(timezone.utc)


def mark_paid(order: dict[str, Any], gateway_payload: dict[str, Any]) -> None:
    receipt = order.get("receipt_number") or f"NF-{now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
    get_db().research_commerce_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {
            "payment_status": "paid",
            "status": "intake",
            "percent_complete": 10,
            "receipt_number": receipt,
            "paid_at": now(),
            "gateway": "paystack",
            "gateway_payment_id": str(gateway_payload.get("id") or gateway_payload.get("reference") or ""),
            "updated_at": now(),
        }},
    )


@app.post("/api/research_commerce_webhook")
async def paystack_webhook(request: Request):
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Paystack is not configured")
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw, hashlib.sha512).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = await request.json()
    if payload.get("event") != "charge.success":
        return {"ok": True}
    data = payload.get("data") or {}
    reference = str(data.get("reference", ""))
    order = get_db().research_commerce_orders.find_one({"_id": reference, "gateway": "paystack"})
    if not order or order.get("payment_status") == "paid":
        return {"ok": True}
    if int(data.get("amount", -1)) != int(order.get("amount_minor", -2)):
        raise HTTPException(status_code=409, detail="Webhook amount mismatch")
    if str(data.get("currency", "")).upper() != str(order.get("currency", "")).upper():
        raise HTTPException(status_code=409, detail="Webhook currency mismatch")
    mark_paid(order, data)
    return {"ok": True}
