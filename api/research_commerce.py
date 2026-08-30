from __future__ import annotations

import hashlib
import hmac
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field, HttpUrl

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.mongo import get_db

app = FastAPI(title="NigerFlora Bioinformatics Commerce", version="2.0.0")

INTEGRITY_NOTICE = (
    "NigerFlora provides computational analysis, reproducibility records, visualization and research support. "
    "Outputs are hypothesis-generating research evidence and do not replace experimental validation, clinical evidence, "
    "supervisor review, ethics approval, regulatory review or the researcher's authorship responsibility."
)

ORDER_STATUSES = ["awaiting_payment", "intake", "queued", "running", "review", "delivered", "revision", "closed"]

SERVICE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "scope-consultation",
        "category": "Research Planning",
        "name": "Bioinformatics Scope Consultation",
        "short": "A paid project-design session before committing to a larger analysis.",
        "featured": True,
        "deliverables": [
            "20-minute project scope session",
            "method and data-readiness checklist",
            "recommended computational workflow",
            "written quote for the next stage",
        ],
        "tiers": [
            {"id": "standard", "name": "Scope Call", "local_ngn": 25000, "global_usd": 39, "turnaround": "1-2 business days", "scope": "One research question or thesis project"},
        ],
        "sales_note": "The consultation fee may be credited toward an eligible full analysis ordered within 7 days at admin discretion.",
    },
    {
        "id": "admet-screening",
        "category": "Bioinformatics Consulting",
        "name": "ADMET & Drug-Likeness Screening",
        "short": "Compound screening with transparent criteria, ranked tables and methods-ready reporting.",
        "featured": True,
        "deliverables": [
            "compound identity and SMILES audit",
            "ADMET/drug-likeness matrix",
            "compound prioritization table",
            "methods-ready workflow notes",
            "publication-ready plots/tables",
        ],
        "tiers": [
            {"id": "starter", "name": "Starter", "local_ngn": 75000, "global_usd": 110, "turnaround": "3-4 business days", "scope": "Up to 25 compounds"},
            {"id": "advanced", "name": "Advanced", "local_ngn": 140000, "global_usd": 210, "turnaround": "5-7 business days", "scope": "Up to 75 compounds + deeper prioritization"},
        ],
    },
    {
        "id": "molecular-docking",
        "category": "Bioinformatics Consulting",
        "name": "Molecular Docking Simulation Service",
        "short": "Reproducible docking workflow, ranked poses, interaction summaries and thesis-ready structural figures.",
        "featured": True,
        "deliverables": [
            "target/ligand preparation record",
            "AutoDock Vina-compatible parameter manifest",
            "ranked docking score and interaction table",
            "binding-site/residue interaction summary",
            "high-resolution 3D molecular figure pack",
            "reproducibility appendix",
        ],
        "tiers": [
            {"id": "starter", "name": "Starter Docking", "local_ngn": 150000, "global_usd": 220, "turnaround": "5-7 business days", "scope": "1 target + up to 10 ligands"},
            {"id": "expanded", "name": "Expanded Docking", "local_ngn": 280000, "global_usd": 420, "turnaround": "7-10 business days", "scope": "Up to 2 targets + 30 ligands"},
        ],
    },
    {
        "id": "network-pharmacology",
        "category": "Bioinformatics Consulting",
        "name": "Network Pharmacology & Cytoscape Analysis",
        "short": "Compound-target, PPI and pathway/network analysis with editable Cytoscape-ready outputs.",
        "featured": True,
        "deliverables": [
            "compound-target curation table",
            "target/disease mapping record",
            "PPI/network construction files",
            "Cytoscape-ready network files",
            "network metrics and prioritization",
            "high-resolution network figures",
        ],
        "tiers": [
            {"id": "starter", "name": "Network Starter", "local_ngn": 120000, "global_usd": 180, "turnaround": "5-7 business days", "scope": "One indication, up to 50 curated compounds"},
            {"id": "publication", "name": "Publication Package", "local_ngn": 220000, "global_usd": 330, "turnaround": "7-10 business days", "scope": "Up to 100 compounds + PPI/enrichment-ready network + figure pack"},
        ],
    },
    {
        "id": "publication-figures",
        "category": "Research Production",
        "name": "Publication-Ready Scientific Figure Pack",
        "short": "High-resolution molecular, pathway and network figures for theses, articles and presentations.",
        "featured": False,
        "deliverables": [
            "300-600 DPI PNG/TIFF figures",
            "journal-size variants",
            "editable source/session files where applicable",
            "figure legends and reproducibility labels",
        ],
        "tiers": [
            {"id": "four", "name": "4-Figure Pack", "local_ngn": 60000, "global_usd": 90, "turnaround": "2-4 business days", "scope": "Up to 4 final figures"},
            {"id": "ten", "name": "10-Figure Pack", "local_ngn": 120000, "global_usd": 180, "turnaround": "4-6 business days", "scope": "Up to 10 final figures"},
        ],
    },
    {
        "id": "thesis-computational-package",
        "category": "Postgraduate Packages",
        "name": "M.Sc./Ph.D. Computational Research Package",
        "short": "Integrated network pharmacology, ADMET, docking, visualization and reproducibility support.",
        "featured": True,
        "deliverables": [
            "computational research design review",
            "network pharmacology workflow",
            "ADMET screening",
            "molecular docking workflow",
            "publication-ready figure pack",
            "methods/reproducibility appendix",
            "results interpretation session",
        ],
        "tiers": [
            {"id": "standard", "name": "Standard Thesis Package", "local_ngn": 300000, "global_usd": 450, "turnaround": "10-14 business days", "scope": "One coherent thesis study with agreed dataset limits"},
            {"id": "extended", "name": "Extended Thesis Package", "local_ngn": 500000, "global_usd": 750, "turnaround": "15-20 business days", "scope": "Larger multi-target or multi-plant study + revision round"},
        ],
    },
    {
        "id": "department-analysis-bundle",
        "category": "Institutional Services",
        "name": "Academic Department Analysis Bundle",
        "short": "A 30-day analysis bundle for departments, labs and supervisors handling multiple postgraduate projects.",
        "featured": True,
        "deliverables": [
            "up to 3 scoped computational projects",
            "shared methods/reproducibility templates",
            "departmental progress dashboard",
            "two group review sessions",
            "priority scheduling during the service window",
        ],
        "tiers": [
            {"id": "department", "name": "30-Day Department Bundle", "local_ngn": 650000, "global_usd": 950, "turnaround": "30-day service window", "scope": "Up to 3 scoped projects; oversized datasets quoted separately"},
        ],
    },
]

ADD_ONS = [
    {"id": "rush", "name": "Priority turnaround", "description": "Queue priority where technically feasible; target turnaround is shortened but not guaranteed until scope review.", "percent": 35},
    {"id": "extra-revision", "name": "Additional revision round", "description": "One additional revision round after the included review cycle.", "local_ngn": 30000, "global_usd": 45},
    {"id": "data-cleaning", "name": "Dataset cleaning & identifier harmonization", "description": "Resolve common identifier, duplicate and formatting issues before analysis.", "local_ngn": 40000, "global_usd": 60},
]


class CommerceAction(BaseModel):
    action: str
    service_id: str | None = Field(default=None, max_length=80)
    tier_id: str | None = Field(default=None, max_length=80)
    market: str | None = Field(default="local", max_length=20)
    gateway: str | None = Field(default=None, max_length=20)
    addon_ids: list[str] = Field(default_factory=list, max_length=10)
    project_title: str | None = Field(default=None, max_length=240)
    institution: str | None = Field(default=None, max_length=240)
    department: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=7000)
    dataset_link: HttpUrl | None = None
    callback_url: str | None = Field(default=None, max_length=500)
    reference: str | None = Field(default=None, max_length=180)
    transaction_id: str | None = Field(default=None, max_length=120)
    order_id: str | None = Field(default=None, max_length=180)
    status: str | None = Field(default=None, max_length=40)
    admin_note: str | None = Field(default=None, max_length=5000)
    due_date: str | None = Field(default=None, max_length=40)
    percent_complete: int | None = Field(default=None, ge=0, le=100)
    deliverables: list[str] = Field(default_factory=list, max_length=50)
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    whatsapp: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=4000)
    website: str | None = Field(default=None, max_length=300)


def now() -> datetime:
    return datetime.now(timezone.utc)


def clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    for key, value in list(result.items()):
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def user_from_request(request: Request) -> dict[str, Any]:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")
    try:
        user_id = ObjectId(str(payload.get("sub")))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")
    user = get_db().users.find_one({"_id": user_id, "is_active": {"$ne": False}})
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    return user


def require_admin(user: dict[str, Any]) -> None:
    if str(user.get("role", "")) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def service_and_tier(service_id: str | None, tier_id: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    service = next((row for row in SERVICE_CATALOG if row["id"] == service_id), None)
    if not service:
        raise HTTPException(status_code=404, detail="Bioinformatics service not found")
    tier = next((row for row in service["tiers"] if row["id"] == tier_id), None)
    if not tier:
        raise HTTPException(status_code=404, detail="Service tier not found")
    return service, tier


def calculate_quote(body: CommerceAction) -> dict[str, Any]:
    service, tier = service_and_tier(body.service_id, body.tier_id)
    market = "global" if body.market == "global" else "local"
    currency = "USD" if market == "global" else "NGN"
    base_major = int(tier["global_usd"] if market == "global" else tier["local_ngn"])
    addon_rows: list[dict[str, Any]] = []
    total_major = base_major
    for addon_id in list(dict.fromkeys(body.addon_ids)):
        addon = next((row for row in ADD_ONS if row["id"] == addon_id), None)
        if not addon:
            continue
        if "percent" in addon:
            amount = round(base_major * int(addon["percent"]) / 100)
        else:
            amount = int(addon["global_usd"] if market == "global" else addon["local_ngn"])
        total_major += amount
        addon_rows.append({"id": addon["id"], "name": addon["name"], "amount_major": amount})
    return {
        "service_id": service["id"],
        "service_name": service["name"],
        "tier_id": tier["id"],
        "tier_name": tier["name"],
        "market": market,
        "currency": currency,
        "base_amount_major": base_major,
        "addons": addon_rows,
        "amount_major": total_major,
        "amount_minor": total_major * 100,
        "turnaround": tier["turnaround"],
        "scope": tier["scope"],
        "deliverables": service["deliverables"],
        "integrity_notice": INTEGRITY_NOTICE,
    }


def paystack_headers() -> dict[str, str]:
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Paystack is not configured. Add PAYSTACK_SECRET_KEY in Vercel Environment Variables.")
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}


def initialize_paystack(user: dict[str, Any], order: dict[str, Any], callback_url: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "email": user["email"],
        "amount": order["amount_minor"],
        "currency": order["currency"],
        "reference": order["_id"],
        "metadata": {"order_id": order["_id"], "service_id": order["service_id"], "product": "nigerflora_bioinformatics"},
    }
    if callback_url:
        payload["callback_url"] = callback_url
    try:
        response = httpx.post(f"{settings.PAYSTACK_BASE_URL}/transaction/initialize", json=payload, headers=paystack_headers(), timeout=25)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Paystack request failed: {exc}")
    if not data.get("status"):
        raise HTTPException(status_code=502, detail=data.get("message") or "Paystack initialization failed")
    return data["data"]


def verify_paystack(reference: str) -> dict[str, Any]:
    try:
        response = httpx.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=paystack_headers(), timeout=25)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Paystack verification failed: {exc}")
    if not data.get("status"):
        raise HTTPException(status_code=502, detail=data.get("message") or "Paystack verification failed")
    return data["data"]


def flutterwave_headers() -> dict[str, str]:
    if not settings.FLUTTERWAVE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Flutterwave is not configured. Add FLUTTERWAVE_SECRET_KEY in Vercel Environment Variables.")
    return {"Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}", "Content-Type": "application/json"}


def initialize_flutterwave(user: dict[str, Any], order: dict[str, Any], callback_url: str | None) -> dict[str, Any]:
    if not callback_url:
        raise HTTPException(status_code=422, detail="A callback URL is required for Flutterwave checkout")
    payload = {
        "tx_ref": order["_id"],
        "amount": str(order["amount_major"]),
        "currency": order["currency"],
        "redirect_url": callback_url,
        "customer": {"email": user["email"], "name": user.get("full_name") or user["email"]},
        "customizations": {"title": "NigerFlora BioSciences", "description": order["service_name"]},
        "meta": {"order_id": order["_id"], "service_id": order["service_id"]},
    }
    try:
        response = httpx.post(f"{settings.FLUTTERWAVE_BASE_URL}/v3/payments", json=payload, headers=flutterwave_headers(), timeout=25)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Flutterwave request failed: {exc}")
    link = (data.get("data") or {}).get("link")
    if data.get("status") != "success" or not link:
        raise HTTPException(status_code=502, detail=data.get("message") or "Flutterwave initialization failed")
    return {"authorization_url": link, "reference": order["_id"]}


def verify_flutterwave(transaction_id: str) -> dict[str, Any]:
    try:
        response = httpx.get(f"{settings.FLUTTERWAVE_BASE_URL}/v3/transactions/{transaction_id}/verify", headers=flutterwave_headers(), timeout=25)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Flutterwave verification failed: {exc}")
    if data.get("status") != "success":
        raise HTTPException(status_code=502, detail=data.get("message") or "Flutterwave verification failed")
    return data.get("data") or {}


def mark_paid(order: dict[str, Any], gateway_payload: dict[str, Any], gateway: str) -> dict[str, Any]:
    db = get_db()
    receipt = f"NF-{now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"
    db.research_commerce_orders.update_one(
        {"_id": order["_id"]},
        {"$set": {
            "payment_status": "paid",
            "status": "intake",
            "percent_complete": 10,
            "receipt_number": receipt,
            "paid_at": now(),
            "gateway": gateway,
            "gateway_payment_id": str(gateway_payload.get("id") or gateway_payload.get("reference") or ""),
            "updated_at": now(),
        }},
    )
    return {"order_id": order["_id"], "payment_status": "paid", "status": "intake", "receipt_number": receipt, "message": "Payment verified. Your project is active and ready for research intake."}


@app.get("/api/research_commerce")
def commerce_catalog():
    return {
        "studio": "NigerFlora BioSciences — Bioinformatics Consulting & Data Analysis",
        "services": SERVICE_CATALOG,
        "addons": ADD_ONS,
        "markets": [
            {"id": "local", "name": "Nigeria / Local", "currency": "NGN", "recommended_gateway": "paystack"},
            {"id": "global", "name": "International", "currency": "USD", "recommended_gateway": "flutterwave"},
        ],
        "gateways": ["paystack", "flutterwave"],
        "order_statuses": ORDER_STATUSES,
        "integrity_notice": INTEGRITY_NOTICE,
    }


@app.post("/api/research_commerce")
def commerce_action(body: CommerceAction, request: Request):
    db = get_db()

    if body.action == "quote":
        return calculate_quote(body)

    if body.action == "capture_lead":
        if body.website:
            return {"message": "Thank you. Your request has been received."}
        if not body.email or not body.full_name:
            raise HTTPException(status_code=422, detail="Name and email are required")
        lead_id = f"LEAD-{now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"
        lead = {
            "_id": lead_id,
            "full_name": body.full_name.strip(),
            "email": str(body.email).lower().strip(),
            "whatsapp": (body.whatsapp or "").strip(),
            "service_id": body.service_id,
            "market": "global" if body.market == "global" else "local",
            "message": body.message,
            "status": "new",
            "source": "bioinformatics_storefront",
            "created_at": now(),
            "updated_at": now(),
        }
        db.research_sales_leads.insert_one(lead)
        return {"lead_id": lead_id, "message": "Your project request has been recorded. You can also create an account and pay for a defined package immediately."}

    user = user_from_request(request)
    user_id = str(user["_id"])

    if body.action == "create_order":
        quote = calculate_quote(body)
        gateway = (body.gateway or ("flutterwave" if quote["market"] == "global" else "paystack")).lower()
        if gateway not in {"paystack", "flutterwave"}:
            raise HTTPException(status_code=422, detail="Choose Paystack or Flutterwave")
        order_id = f"BIO-{now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"
        order = {
            "_id": order_id,
            "commerce_version": 2,
            "user_id": user_id,
            "email": user["email"],
            "service_id": quote["service_id"],
            "service_name": quote["service_name"],
            "tier_id": quote["tier_id"],
            "tier_name": quote["tier_name"],
            "project_title": (body.project_title or quote["service_name"]).strip(),
            "institution": (body.institution or "").strip(),
            "department": (body.department or "").strip(),
            "notes": body.notes,
            "dataset_link": str(body.dataset_link) if body.dataset_link else None,
            "market": quote["market"],
            "currency": quote["currency"],
            "amount_major": quote["amount_major"],
            "amount_minor": quote["amount_minor"],
            "addons": quote["addons"],
            "scope": quote["scope"],
            "turnaround": quote["turnaround"],
            "expected_deliverables": quote["deliverables"],
            "deliverables": [],
            "gateway": gateway,
            "status": "awaiting_payment",
            "payment_status": "pending",
            "percent_complete": 0,
            "created_at": now(),
            "updated_at": now(),
        }
        db.research_commerce_orders.insert_one(order)
        try:
            payment = initialize_paystack(user, order, body.callback_url) if gateway == "paystack" else initialize_flutterwave(user, order, body.callback_url)
        except Exception:
            db.research_commerce_orders.update_one({"_id": order_id}, {"$set": {"status": "payment_setup_failed", "updated_at": now()}})
            raise
        db.research_commerce_orders.update_one({"_id": order_id}, {"$set": {"payment_reference": payment.get("reference", order_id), "updated_at": now()}})
        return {
            "order_id": order_id,
            "gateway": gateway,
            "currency": quote["currency"],
            "amount_major": quote["amount_major"],
            "authorization_url": payment.get("authorization_url"),
            "reference": payment.get("reference", order_id),
        }

    if body.action == "verify_order":
        reference = (body.reference or "").strip()
        if not reference:
            raise HTTPException(status_code=422, detail="Payment reference is required")
        order = db.research_commerce_orders.find_one({"_id": reference, "user_id": user_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if order.get("payment_status") == "paid":
            return {"order_id": reference, "payment_status": "paid", "status": order.get("status"), "receipt_number": order.get("receipt_number"), "message": "Payment was already verified."}
        gateway = order.get("gateway", "paystack")
        if gateway == "paystack":
            payment = verify_paystack(reference)
            customer = payment.get("customer") or {}
            if not (
                payment.get("status") == "success"
                and int(payment.get("amount", -1)) == int(order.get("amount_minor", -2))
                and str(payment.get("currency", "")).upper() == str(order.get("currency", "")).upper()
                and str(customer.get("email", "")).lower() == str(user.get("email", "")).lower()
            ):
                raise HTTPException(status_code=409, detail="Paystack payment could not be matched securely to this order")
            return mark_paid(order, payment, "paystack")
        if not body.transaction_id:
            raise HTTPException(status_code=422, detail="Flutterwave transaction_id is required")
        payment = verify_flutterwave(body.transaction_id)
        paid_amount = float(payment.get("amount", -1))
        if not (
            payment.get("status") == "successful"
            and str(payment.get("tx_ref", "")) == reference
            and str(payment.get("currency", "")).upper() == str(order.get("currency", "")).upper()
            and abs(paid_amount - float(order.get("amount_major", -2))) < 0.01
        ):
            raise HTTPException(status_code=409, detail="Flutterwave payment could not be matched securely to this order")
        return mark_paid(order, payment, "flutterwave")

    if body.action == "my_orders":
        rows = db.research_commerce_orders.find({"user_id": user_id}).sort("created_at", -1).limit(100)
        return {"orders": [clean_doc(row) for row in rows]}

    if body.action == "admin_orders":
        require_admin(user)
        rows = db.research_commerce_orders.find({}).sort("created_at", -1).limit(300)
        leads = db.research_sales_leads.find({}).sort("created_at", -1).limit(300)
        return {"orders": [clean_doc(row) for row in rows], "leads": [clean_doc(row) for row in leads]}

    if body.action == "admin_update_order":
        require_admin(user)
        if not body.order_id:
            raise HTTPException(status_code=422, detail="order_id is required")
        order = db.research_commerce_orders.find_one({"_id": body.order_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        updates: dict[str, Any] = {"updated_at": now()}
        if body.status:
            if body.status not in ORDER_STATUSES:
                raise HTTPException(status_code=422, detail="Unsupported order status")
            updates["status"] = body.status
        if body.admin_note is not None:
            updates["admin_note"] = body.admin_note
        if body.due_date is not None:
            updates["due_date"] = body.due_date
        if body.percent_complete is not None:
            updates["percent_complete"] = body.percent_complete
        if body.deliverables:
            cleaned = [item.strip() for item in body.deliverables if item.strip()]
            updates["deliverables"] = cleaned
            if cleaned and not body.status:
                updates["status"] = "review"
        db.research_commerce_orders.update_one({"_id": body.order_id}, {"$set": updates})
        updated = db.research_commerce_orders.find_one({"_id": body.order_id})
        return {"order": clean_doc(updated), "message": "Order updated."}

    raise HTTPException(status_code=400, detail="Unsupported commerce action")


@app.post("/api/research_commerce/paystack_webhook")
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
    if int(data.get("amount", -1)) != int(order.get("amount_minor", -2)) or str(data.get("currency", "")).upper() != str(order.get("currency", "")).upper():
        raise HTTPException(status_code=409, detail="Webhook payment mismatch")
    mark_paid(order, data, "paystack")
    return {"ok": True}
