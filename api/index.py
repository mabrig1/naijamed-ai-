from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

# Reuse the agent modules under backend/app without importing the legacy SQL stack.
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import httpx
from bson import ObjectId
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from pymongo.errors import DuplicateKeyError

from app.clinical import run_clinical_workflow
from app.clinical.crypto import decrypt_json, encrypt_json
from app.clinical.fhir import build_fhir_bundle
from app.clinical.multimodal import analyze_medical_image
from app.clinical.voice import transcribe_audio
from app.core.config import settings
from app.core.mongo import get_db


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Agentic Nigerian healthcare decision support, telemedicine coordination and clinical scribing.",
    version="2.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ----------------------------- schemas --------------------------------------

Role = Literal["patient", "doctor", "clinic", "hmo", "admin"]


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: Role = "patient"

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("Password must contain at least one letter and one number")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TriageRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    duration: str | None = Field(default=None, max_length=200)
    severity: int | None = Field(default=None, ge=1, le=10)
    medical_history: list[str] = Field(default_factory=list, max_length=30)
    medications: list[str] = Field(default_factory=list, max_length=30)
    allergies: list[str] = Field(default_factory=list, max_length=30)
    state: str | None = Field(default=None, max_length=100)
    lga: str | None = Field(default=None, max_length=100)


class ProviderProfileRequest(BaseModel):
    license_number: str = Field(min_length=3, max_length=100)
    licensing_body: str = Field(default="MDCN", max_length=100)
    specialties: list[str] = Field(default_factory=list, max_length=20)
    state: str | None = Field(default=None, max_length=100)
    lga: str | None = Field(default=None, max_length=100)
    available_online: bool = True
    consultation_fee_kobo: int = Field(default=0, ge=0, le=100_000_000)
    paystack_subaccount_code: str | None = Field(default=None, max_length=100)


class ConsultationCheckoutRequest(BaseModel):
    case_id: str
    provider_user_id: str
    callback_url: str | None = None


class SubscriptionCheckoutRequest(BaseModel):
    plan_id: Literal["family_pass", "doctor_workspace"]
    callback_url: str | None = None


class SMSRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=30)
    message: str = Field(min_length=1, max_length=1000)


# ----------------------------- auth -----------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_public(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "is_active": bool(user.get("is_active", True)),
        "created_at": user.get("created_at", _now()).isoformat(),
    }


def _token(user: dict[str, Any], token_type: str, expires: timedelta) -> str:
    payload = {
        "sub": str(user["_id"]),
        "type": token_type,
        "ver": int(user.get("token_version", 0)),
        "exp": _now() + expires,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _token_pair(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "access_token": _token(user, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
        "refresh_token": _token(user, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)),
        "token_type": "bearer",
        "user": _user_public(user),
    }


def current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")
    try:
        user_id = ObjectId(str(payload.get("sub")))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")
    user = get_db().users.find_one({"_id": user_id, "is_active": {"$ne": False}})
    if not user or int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    return user


def admin_user(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterRequest):
    db = get_db()
    email = body.email.lower().strip()
    allowed_self_roles = {"patient", "doctor", "clinic", "hmo"}
    role: str = body.role if body.role in allowed_self_roles else "patient"
    admin_emails = {e.strip().lower() for e in settings.ADMIN_EMAILS.split(",") if e.strip()}
    if email in admin_emails:
        role = "admin"
    user = {
        "email": email,
        "full_name": body.full_name.strip(),
        "password_hash": pwd_context.hash(body.password),
        "role": role,
        "is_active": True,
        "token_version": 0,
        "created_at": _now(),
    }
    try:
        result = db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    user["_id"] = result.inserted_id
    return _user_public(user)


@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = get_db().users.find_one({"email": body.email.lower().strip()})
    if not user or not pwd_context.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return _token_pair(user)


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(current_user)):
    return _user_public(user)


@app.post("/api/auth/logout", status_code=204)
def logout(user: dict[str, Any] = Depends(current_user)):
    get_db().users.update_one({"_id": user["_id"]}, {"$inc": {"token_version": 1}})


# -------------------------- clinical workflow -------------------------------


def _audit(action: str, actor_user_id: str | None, case_id: str | None = None, **metadata: Any) -> None:
    get_db().clinical_audit_logs.insert_one(
        {
            "case_id": case_id,
            "actor_user_id": actor_user_id,
            "action": action,
            "metadata": metadata,
            "created_at": _now(),
        }
    )


def _verified_provider(user_id: str) -> dict[str, Any] | None:
    return get_db().provider_profiles.find_one({"user_id": user_id, "verified": True})


def _provider_matches(state_name: str | None, lga: str | None, limit: int = 10) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"verified": True, "available_online": True}
    if state_name:
        query["state"] = state_name
    if lga:
        query["lga"] = lga
    rows = get_db().provider_profiles.find(query).limit(limit)
    return [
        {
            "provider_user_id": row["user_id"],
            "provider_type": row.get("provider_type", "doctor"),
            "specialties": row.get("specialties", []),
            "state": row.get("state"),
            "lga": row.get("lga"),
            "consultation_fee_kobo": int(row.get("consultation_fee_kobo", 0)),
            "source": f"{settings.APP_NAME} verified provider registry",
            "accreditation_verified": True,
        }
        for row in rows
    ]


@app.post("/api/clinical/triage", status_code=201)
def triage(body: TriageRequest, user: dict[str, Any] = Depends(current_user)):
    workflow = run_clinical_workflow(
        {
            "message": body.message,
            "duration": body.duration,
            "severity": body.severity,
            "medical_history": body.medical_history,
            "medications": body.medications,
            "allergies": body.allergies,
            "state": body.state,
            "lga": body.lga,
        }
    )
    if workflow.get("blocked"):
        raise HTTPException(status_code=422, detail=workflow.get("block_reason") or "Request blocked by clinical safety policy")

    case_id = str(uuid.uuid4())
    urgency = str(workflow.get("urgency") or "routine")
    fhir_bundle = build_fhir_bundle(case_id, str(user["_id"]), workflow.get("structured_intake") or {}, urgency)
    encrypted_payload = encrypt_json({"workflow": workflow, "fhir_bundle": fhir_bundle})
    get_db().clinical_cases.insert_one(
        {
            "_id": case_id,
            "patient_id": str(user["_id"]),
            "assigned_doctor_id": None,
            "urgency": urgency,
            "status": "emergency_referral" if workflow.get("emergency") else "triaged",
            "state": body.state,
            "lga": body.lga,
            "encrypted_payload": encrypted_payload,
            "encryption_key_version": settings.PHI_KEY_VERSION,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    _audit("clinical_case.created", str(user["_id"]), case_id, urgency=urgency)

    return {
        "case_id": case_id,
        "urgency": urgency,
        "emergency": bool(workflow.get("emergency")),
        "red_flags": workflow.get("red_flags", []),
        "structured_intake": workflow.get("structured_intake") or {},
        "differential_for_clinician_review": workflow.get("differential") or [],
        "evidence": workflow.get("evidence") or [],
        "referrals": _provider_matches(body.state, body.lga) + list(workflow.get("referrals") or []),
        "patient_notice": workflow.get("patient_notice") or "Licensed clinician review required.",
        "doctor_handoff_ready": True,
        "medication_recommendation": None,
    }


@app.get("/api/clinical/cases/{case_id}")
def get_case(case_id: str, user: dict[str, Any] = Depends(current_user)):
    case = get_db().clinical_cases.find_one({"_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Clinical case not found")
    user_id = str(user["_id"])
    provider_view = user.get("role") == "admin" or (case.get("assigned_doctor_id") == user_id and bool(_verified_provider(user_id)))
    if case.get("patient_id") != user_id and not provider_view:
        raise HTTPException(status_code=403, detail="Clinical record access denied")
    payload = decrypt_json(case["encrypted_payload"])
    workflow = payload.get("workflow", {})
    result: dict[str, Any] = {
        "id": case_id,
        "urgency": case.get("urgency"),
        "status": case.get("status"),
        "state": case.get("state"),
        "lga": case.get("lga"),
        "assigned_doctor_id": case.get("assigned_doctor_id"),
        "structured_intake": workflow.get("structured_intake", {}),
        "patient_notice": workflow.get("patient_notice"),
        "referrals": workflow.get("referrals", []),
        "created_at": case.get("created_at"),
    }
    if provider_view:
        result.update(
            {
                "differential": workflow.get("differential", []),
                "evidence": workflow.get("evidence", []),
                "soap_note": workflow.get("soap_note", {}),
                "fhir_bundle": payload.get("fhir_bundle"),
            }
        )
    _audit("clinical_case.read", user_id, case_id, provider_view=provider_view)
    return result


@app.post("/api/clinical/providers/profile", status_code=201)
def provider_profile(body: ProviderProfileRequest, user: dict[str, Any] = Depends(current_user)):
    if user.get("role") not in {"doctor", "clinic", "admin"}:
        raise HTTPException(status_code=403, detail="Doctor or clinic account required")
    doc = {
        "user_id": str(user["_id"]),
        "provider_type": "doctor" if user.get("role") == "doctor" else "clinic",
        "license_number": body.license_number.strip(),
        "licensing_body": body.licensing_body.strip(),
        "specialties": body.specialties,
        "state": body.state,
        "lga": body.lga,
        "available_online": body.available_online,
        "consultation_fee_kobo": body.consultation_fee_kobo,
        "paystack_subaccount_code": body.paystack_subaccount_code,
        "verified": False,
        "verified_at": None,
        "updated_at": _now(),
    }
    try:
        get_db().provider_profiles.update_one({"user_id": doc["user_id"]}, {"$set": doc, "$setOnInsert": {"created_at": _now()}}, upsert=True)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Licence number is already registered")
    return {"user_id": doc["user_id"], "verification_status": "pending", "licensing_body": doc["licensing_body"]}


@app.post("/api/clinical/providers/{provider_user_id}/verify")
def verify_provider(provider_user_id: str, _: dict[str, Any] = Depends(admin_user)):
    result = get_db().provider_profiles.update_one(
        {"user_id": provider_user_id}, {"$set": {"verified": True, "verified_at": _now()}}
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    return {
        "provider_user_id": provider_user_id,
        "verified": True,
        "note": "Admin attestation recorded. Production operations must independently verify the licence with the relevant regulator.",
    }


@app.get("/api/clinical/providers/nearby")
def nearby_providers(state_name: str | None = None, lga: str | None = None, _: dict[str, Any] = Depends(current_user)):
    return _provider_matches(state_name, lga, 20)


@app.post("/api/clinical/cases/{case_id}/assign/{provider_user_id}")
def assign_provider(case_id: str, provider_user_id: str, user: dict[str, Any] = Depends(current_user)):
    db = get_db()
    case = db.clinical_cases.find_one({"_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Clinical case not found")
    user_id = str(user["_id"])
    if case.get("patient_id") != user_id and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only the patient or an administrator can assign a clinician")
    if not _verified_provider(provider_user_id):
        raise HTTPException(status_code=409, detail="Provider is not verified")
    db.clinical_cases.update_one(
        {"_id": case_id},
        {"$set": {"assigned_doctor_id": provider_user_id, "status": "awaiting_clinician", "updated_at": _now()}},
    )
    _audit("clinical_case.provider_assigned", user_id, case_id, provider_user_id=provider_user_id)
    return {"case_id": case_id, "assigned_doctor_id": provider_user_id, "status": "awaiting_clinician"}


@app.get("/api/clinical/provider/cases")
def provider_cases(user: dict[str, Any] = Depends(current_user)):
    user_id = str(user["_id"])
    if not _verified_provider(user_id):
        raise HTTPException(status_code=403, detail="Verified clinician account required")
    rows = get_db().clinical_cases.find({"assigned_doctor_id": user_id}).sort("created_at", -1).limit(100)
    return [
        {
            "id": row["_id"],
            "urgency": row.get("urgency"),
            "status": row.get("status"),
            "state": row.get("state"),
            "lga": row.get("lga"),
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


@app.post("/api/clinical/media/analyze")
async def analyze_media(file: UploadFile = File(...), context: str | None = Form(default=None), _: dict[str, Any] = Depends(current_user)):
    data = await file.read()
    return analyze_medical_image(data, file.content_type or "application/octet-stream", context)


@app.post("/api/clinical/voice/transcribe")
async def transcribe(file: UploadFile = File(...), language_hint: str | None = Form(default=None), _: dict[str, Any] = Depends(current_user)):
    data = await file.read()
    return transcribe_audio(file.filename or "audio.webm", data, file.content_type or "application/octet-stream", language_hint)


# -------------------------- monetization ------------------------------------


def _paystack_headers() -> dict[str, str]:
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Paystack is not configured")
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}


def _paystack_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(f"{settings.PAYSTACK_BASE_URL}{path}", json=payload, headers=_paystack_headers(), timeout=30)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Payment provider unavailable")


def _paystack_get(path: str) -> dict[str, Any]:
    try:
        response = httpx.get(f"{settings.PAYSTACK_BASE_URL}{path}", headers=_paystack_headers(), timeout=30)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Payment provider unavailable")


def _clinical_plan_catalog() -> dict[str, dict[str, Any]]:
    return {
        "family_pass": {
            "id": "family_pass",
            "label": "Family Health Pass",
            "audience": "Individuals & families",
            "price_kobo": settings.FAMILY_PASS_MONTHLY_KOBO,
            "billing": "monthly",
            "paystack_plan_code": settings.FAMILY_PASS_PAYSTACK_PLAN_CODE or None,
            "allowed_roles": ["patient", "admin"],
            "features": [
                "Family health profile and longitudinal case history",
                "Priority clinician handoff and consultation tracking",
                "Voice symptom capture and secure clinical summaries",
                "Care reminders and exportable visit summaries",
            ],
        },
        "doctor_workspace": {
            "id": "doctor_workspace",
            "label": "Doctor Workspace",
            "audience": "Doctors & clinics",
            "price_kobo": settings.DOCTOR_WORKSPACE_MONTHLY_KOBO,
            "billing": "monthly",
            "paystack_plan_code": settings.DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE or None,
            "allowed_roles": ["doctor", "clinic", "admin"],
            "features": [
                "Structured patient intake and AI-assisted SOAP preparation",
                "Encrypted case workspace and consultation history",
                "Clinical voice/image intake tools with audit trail",
                "Provider profile, fee setup and paid consultation workflow",
            ],
        },
    }


def _subscription_entitlements(active_plan_ids: list[str]) -> list[str]:
    entitlements = {"free_ai_triage", "red_flag_escalation", "provider_directory"}
    if "family_pass" in active_plan_ids:
        entitlements.update({"family_history", "priority_handoff", "voice_capture", "care_summary_exports"})
    if "doctor_workspace" in active_plan_ids:
        entitlements.update({"doctor_workspace", "clinical_scribing", "provider_payments", "case_audit_history"})
    return sorted(entitlements)


def _plan_from_paystack_code(plan_code: str | None) -> str | None:
    if not plan_code:
        return None
    for plan_id, plan in _clinical_plan_catalog().items():
        if plan.get("paystack_plan_code") == plan_code:
            return plan_id
    return None


@app.get("/api/clinical/plans")
def plans():
    catalog = _clinical_plan_catalog()
    return {
        "currency": "NGN",
        "free": {
            "id": "free",
            "label": "Essential Care",
            "price_kobo": 0,
            "billing": "free",
            "features": [
                "AI-assisted symptom intake",
                "Deterministic red-flag escalation",
                "Verified provider discovery",
            ],
        },
        "subscriptions": [catalog["family_pass"], catalog["doctor_workspace"]],
        "consultations": {
            "label": "Doctor consultations",
            "pricing": "provider-set",
            "platform_commission_percent": settings.CONSULT_PLATFORM_FEE_PERCENT,
        },
        "research_services_url": "/bioinformatics-services",
        "enterprise": [
            {"id": "corporate_wellness", "label": "Corporate / campus wellness", "pricing": "custom quote"},
            {"id": "hmo_api", "label": "HMO / clinic API", "pricing": "contract / usage-based"},
        ],
    }


@app.get("/api/clinical/subscriptions/me")
def my_subscriptions(user: dict[str, Any] = Depends(current_user)):
    user_id = str(user["_id"])
    rows = list(get_db().clinical_subscriptions.find({"user_id": user_id}).sort("updated_at", -1).limit(20))
    active_plan_ids = sorted({
        str(row.get("plan_id"))
        for row in rows
        if row.get("status") in {"active", "renewing"} and row.get("plan_id")
    })
    return {
        "active_plan_ids": active_plan_ids,
        "entitlements": _subscription_entitlements(active_plan_ids),
        "subscriptions": [
            {
                "id": str(row.get("_id")),
                "plan_id": row.get("plan_id"),
                "status": row.get("status", "pending"),
                "payment_reference": row.get("payment_reference"),
                "subscription_code": row.get("subscription_code"),
                "next_payment_date": row.get("next_payment_date"),
                "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
            }
            for row in rows
        ],
    }


@app.post("/api/clinical/subscriptions/checkout", status_code=201)
def subscription_checkout(body: SubscriptionCheckoutRequest, user: dict[str, Any] = Depends(current_user)):
    catalog = _clinical_plan_catalog()
    plan = catalog[body.plan_id]
    if user.get("role") not in plan["allowed_roles"]:
        raise HTTPException(status_code=403, detail=f"{plan['label']} is not available for this account role")
    plan_code = plan.get("paystack_plan_code")
    if not plan_code:
        raise HTTPException(
            status_code=503,
            detail=f"{plan['label']} checkout is not configured. Add the Paystack plan code in production environment variables.",
        )

    payment = _paystack_post(
        "/transaction/initialize",
        {
            "email": user["email"],
            "amount": int(plan["price_kobo"]),
            "currency": "NGN",
            "plan": plan_code,
            "callback_url": body.callback_url or f"{settings.FRONTEND_URL}/pricing",
            "metadata": {
                "product": "nigerflora_clinical_subscription",
                "plan_id": body.plan_id,
                "user_id": str(user["_id"]),
            },
        },
    )
    if not payment.get("status"):
        raise HTTPException(status_code=502, detail="Subscription checkout could not be initialized")
    inner = payment.get("data") or {}
    reference = str(inner.get("reference") or "")
    if not reference or not inner.get("authorization_url"):
        raise HTTPException(status_code=502, detail="Payment provider did not return a checkout URL")

    get_db().clinical_subscriptions.update_one(
        {"user_id": str(user["_id"]), "plan_id": body.plan_id},
        {
            "$set": {
                "user_id": str(user["_id"]),
                "email": user["email"],
                "plan_id": body.plan_id,
                "plan_label": plan["label"],
                "price_kobo": int(plan["price_kobo"]),
                "paystack_plan_code": plan_code,
                "payment_reference": reference,
                "status": "pending",
                "updated_at": _now(),
            },
            "$setOnInsert": {"created_at": _now()},
        },
        upsert=True,
    )
    return {
        "plan_id": body.plan_id,
        "authorization_url": inner["authorization_url"],
        "reference": reference,
        "amount_kobo": int(plan["price_kobo"]),
    }


@app.get("/api/clinical/subscriptions/verify/{reference}")
def verify_subscription(reference: str, user: dict[str, Any] = Depends(current_user)):
    db = get_db()
    user_id = str(user["_id"])
    record = db.clinical_subscriptions.find_one({"user_id": user_id, "payment_reference": reference})
    if not record:
        raise HTTPException(status_code=404, detail="Subscription checkout not found")

    data = (_paystack_get(f"/transaction/verify/{reference}").get("data") or {})
    customer = data.get("customer") or {}
    email_matches = str(customer.get("email") or "").lower() == str(user.get("email") or "").lower()
    amount_matches = int(data.get("amount") or 0) == int(record.get("price_kobo") or -1)
    paid = data.get("status") == "success" and email_matches and amount_matches
    if not paid:
        raise HTTPException(status_code=409, detail="Subscription payment could not be matched securely to this account")

    db.clinical_subscriptions.update_one(
        {"_id": record["_id"]},
        {
            "$set": {
                "status": "active",
                "customer_code": customer.get("customer_code"),
                "paid_at": _now(),
                "updated_at": _now(),
            }
        },
    )
    return {
        "reference": reference,
        "paid": True,
        "plan_id": record["plan_id"],
        "status": "active",
        "entitlements": _subscription_entitlements([str(record["plan_id"])]),
    }


@app.get("/api/admin/monetization/summary")
def monetization_summary(_: dict[str, Any] = Depends(admin_user)):
    db = get_db()
    month_start = _now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    active_subscriptions = list(db.clinical_subscriptions.find({"status": {"$in": ["active", "renewing"]}}))
    family_active = sum(1 for row in active_subscriptions if row.get("plan_id") == "family_pass")
    doctor_active = sum(1 for row in active_subscriptions if row.get("plan_id") == "doctor_workspace")
    mrr_kobo = sum(int(row.get("price_kobo") or 0) for row in active_subscriptions)

    paid_consultations = list(
        db.clinical_consultations.find({"payment_status": "paid", "paid_at": {"$gte": month_start}})
    )
    consultation_gmv_kobo = sum(int(row.get("amount_kobo") or 0) for row in paid_consultations)
    platform_fees_kobo = sum(int(row.get("platform_fee_kobo") or 0) for row in paid_consultations)

    paid_research_orders = list(
        db.research_commerce_orders.find({"payment_status": "paid", "paid_at": {"$gte": month_start}})
    )
    research_revenue: dict[str, float] = {}
    for row in paid_research_orders:
        currency = str(row.get("currency") or "NGN").upper()
        research_revenue[currency] = research_revenue.get(currency, 0) + float(row.get("amount_major") or 0)

    pending_research_leads = db.research_sales_leads.count_documents({"status": "new"})

    return {
        "period": month_start.strftime("%Y-%m"),
        "subscriptions": {
            "active_total": len(active_subscriptions),
            "family_pass_active": family_active,
            "doctor_workspace_active": doctor_active,
            "mrr_ngn_kobo": mrr_kobo,
        },
        "consultations": {
            "paid_this_month": len(paid_consultations),
            "gmv_ngn_kobo": consultation_gmv_kobo,
            "platform_fees_ngn_kobo": platform_fees_kobo,
            "commission_percent": settings.CONSULT_PLATFORM_FEE_PERCENT,
        },
        "research_services": {
            "paid_orders_this_month": len(paid_research_orders),
            "revenue_by_currency": research_revenue,
            "new_leads": pending_research_leads,
        },
    }


@app.post("/api/clinical/consultations/checkout", status_code=201)
def consultation_checkout(body: ConsultationCheckoutRequest, user: dict[str, Any] = Depends(current_user)):
    db = get_db()
    user_id = str(user["_id"])
    case = db.clinical_cases.find_one({"_id": body.case_id, "patient_id": user_id})
    if not case:
        raise HTTPException(status_code=404, detail="Patient case not found")
    provider = _verified_provider(body.provider_user_id)
    if not provider:
        raise HTTPException(status_code=409, detail="Provider is not verified")
    amount = int(provider.get("consultation_fee_kobo", 0))
    if amount <= 0:
        raise HTTPException(status_code=409, detail="Provider has not configured a consultation fee")
    platform_fee = round(amount * settings.CONSULT_PLATFORM_FEE_PERCENT / 100)
    consultation_id = str(uuid.uuid4())
    subaccount_code = str(provider.get("paystack_subaccount_code") or "").strip()
    payment_payload: dict[str, Any] = {
        "email": user["email"],
        "amount": amount,
        "currency": "NGN",
        "callback_url": body.callback_url or settings.FRONTEND_URL,
        "metadata": {
            "product": "mabrig_healthos_consultation",
            "consultation_id": consultation_id,
            "case_id": body.case_id,
            "patient_user_id": user_id,
            "provider_user_id": body.provider_user_id,
            "platform_fee_kobo": platform_fee,
            "provider_net_kobo": amount - platform_fee,
            "settlement_mode": "paystack_subaccount" if subaccount_code else "manual",
        },
    }
    if subaccount_code:
        # Paystack split settlement: route the provider share to the verified
        # provider's subaccount while retaining the configured platform charge.
        payment_payload["subaccount"] = subaccount_code
        payment_payload["transaction_charge"] = platform_fee

    payment = _paystack_post("/transaction/initialize", payment_payload)
    if not payment.get("status"):
        raise HTTPException(status_code=502, detail="Payment initialization failed")
    inner = payment["data"]
    db.clinical_consultations.insert_one(
        {
            "_id": consultation_id,
            "case_id": body.case_id,
            "patient_id": user_id,
            "provider_id": body.provider_user_id,
            "amount_kobo": amount,
            "platform_fee_kobo": platform_fee,
            "provider_net_kobo": amount - platform_fee,
            "settlement_mode": "paystack_subaccount" if subaccount_code else "manual",
            "provider_subaccount_code": subaccount_code or None,
            "payment_reference": inner["reference"],
            "payment_status": "pending",
            "consultation_status": "awaiting_payment",
            "created_at": _now(),
        }
    )
    db.clinical_cases.update_one({"_id": body.case_id}, {"$set": {"assigned_doctor_id": body.provider_user_id, "updated_at": _now()}})
    return {
        "consultation_id": consultation_id,
        "authorization_url": inner["authorization_url"],
        "reference": inner["reference"],
        "amount_kobo": amount,
        "platform_fee_kobo": platform_fee,
    }


@app.get("/api/clinical/consultations/verify/{reference}")
def verify_consultation(reference: str, user: dict[str, Any] = Depends(current_user)):
    db = get_db()
    user_id = str(user["_id"])
    consultation = db.clinical_consultations.find_one({"payment_reference": reference})
    if not consultation or (user_id not in {consultation.get("patient_id"), consultation.get("provider_id")} and user.get("role") != "admin"):
        raise HTTPException(status_code=404, detail="Consultation not found")
    data = (_paystack_get(f"/transaction/verify/{reference}").get("data") or {})
    paid = data.get("status") == "success" and int(data.get("amount") or 0) == int(consultation["amount_kobo"])
    payment_status = "paid" if paid else str(data.get("status") or "pending")
    update = {"payment_status": payment_status}
    if paid:
        update["consultation_status"] = "ready"
        update["paid_at"] = _now()
        db.clinical_cases.update_one({"_id": consultation["case_id"]}, {"$set": {"status": "clinician_assigned", "updated_at": _now()}})
    db.clinical_consultations.update_one({"_id": consultation["_id"]}, {"$set": update})
    return {"reference": reference, "paid": paid, "status": payment_status, "consultation_status": update.get("consultation_status", consultation.get("consultation_status"))}


@app.post("/api/clinical/webhooks/paystack", include_in_schema=False)
async def paystack_webhook(request: Request):
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw, hashlib.sha512).hexdigest() if settings.PAYSTACK_SECRET_KEY else ""
    if not expected or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = json.loads(raw.decode("utf-8"))
    event_name = str(event.get("event") or "")
    data = event.get("data") or {}
    db = get_db()

    if event_name == "charge.success":
        reference = data.get("reference")
        consultation = db.clinical_consultations.find_one({"payment_reference": reference})
        if consultation and int(data.get("amount") or 0) == int(consultation["amount_kobo"]):
            db.clinical_consultations.update_one(
                {"_id": consultation["_id"]},
                {"$set": {"payment_status": "paid", "consultation_status": "ready", "paid_at": _now()}},
            )
            db.clinical_cases.update_one(
                {"_id": consultation["case_id"]},
                {"$set": {"status": "clinician_assigned", "updated_at": _now()}},
            )

        metadata = data.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        if metadata.get("product") == "nigerflora_clinical_subscription":
            user_id = str(metadata.get("user_id") or "")
            plan_id = str(metadata.get("plan_id") or "")
            if user_id and plan_id:
                db.clinical_subscriptions.update_one(
                    {"user_id": user_id, "plan_id": plan_id},
                    {
                        "$set": {
                            "status": "active",
                            "payment_reference": str(reference or ""),
                            "customer_code": (data.get("customer") or {}).get("customer_code"),
                            "paid_at": _now(),
                            "updated_at": _now(),
                        }
                    },
                    upsert=False,
                )

    if event_name == "subscription.create":
        customer = data.get("customer") or {}
        plan = data.get("plan") or {}
        plan_code = str(plan.get("plan_code") or data.get("plan_code") or "")
        plan_id = _plan_from_paystack_code(plan_code)
        email = str(customer.get("email") or "").lower()
        user = db.users.find_one({"email": email}) if email else None
        if plan_id and user:
            db.clinical_subscriptions.update_one(
                {"user_id": str(user["_id"]), "plan_id": plan_id},
                {
                    "$set": {
                        "status": "active",
                        "subscription_code": data.get("subscription_code"),
                        "email_token": data.get("email_token"),
                        "customer_code": customer.get("customer_code"),
                        "next_payment_date": data.get("next_payment_date"),
                        "updated_at": _now(),
                    },
                    "$setOnInsert": {"created_at": _now(), "email": email},
                },
                upsert=True,
            )

    if event_name in {"subscription.disable", "subscription.not_renew"}:
        subscription_code = data.get("subscription_code")
        if subscription_code:
            db.clinical_subscriptions.update_one(
                {"subscription_code": subscription_code},
                {"$set": {"status": "cancelled", "updated_at": _now()}},
            )

    if event_name == "invoice.payment_failed":
        subscription = data.get("subscription") or {}
        subscription_code = subscription.get("subscription_code")
        if subscription_code:
            db.clinical_subscriptions.update_one(
                {"subscription_code": subscription_code},
                {"$set": {"status": "past_due", "updated_at": _now()}},
            )

    if event_name == "invoice.update":
        subscription = data.get("subscription") or {}
        subscription_code = subscription.get("subscription_code")
        paid = bool(data.get("paid"))
        if subscription_code and paid:
            db.clinical_subscriptions.update_one(
                {"subscription_code": subscription_code},
                {
                    "$set": {
                        "status": "active",
                        "next_payment_date": subscription.get("next_payment_date"),
                        "updated_at": _now(),
                    }
                },
            )

    return {"received": True}


# -------------------------- low bandwidth -----------------------------------


@app.post("/api/clinical/channels/sms/send")
def send_sms(body: SMSRequest, _: dict[str, Any] = Depends(current_user)):
    if not settings.AFRICASTALKING_API_KEY or not settings.AFRICASTALKING_USERNAME:
        raise HTTPException(status_code=503, detail="Africa's Talking SMS is not configured")
    form = {"username": settings.AFRICASTALKING_USERNAME, "to": body.phone_number, "message": body.message}
    if settings.AFRICASTALKING_SENDER_ID:
        form["from"] = settings.AFRICASTALKING_SENDER_ID
    headers = {"apiKey": settings.AFRICASTALKING_API_KEY, "Accept": "application/json"}
    response = httpx.post("https://api.africastalking.com/version1/messaging", data=form, headers=headers, timeout=20)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="SMS provider request failed")
    return response.json()


@app.post("/api/clinical/channels/ussd")
async def ussd(request: Request):
    form = await request.form()
    text = str(form.get("text") or "")
    if not text:
        return "CON Mabrig HealthOS\n1. Start symptom triage\n2. Emergency guidance"
    if text == "2":
        return "END If you have severe bleeding, chest pain, breathing difficulty, loss of consciousness, or another emergency, seek emergency care immediately."
    return "END For privacy and safety, continue the full clinical intake by secure web/app or request an SMS callback."


@app.get("/api/health")
def health():
    database_ok = False
    try:
        get_db().command("ping")
        database_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if database_ok else "degraded",
        "service": settings.APP_NAME,
        "runtime": "vercel-python",
        "database": "mongodb-atlas",
        "database_ok": database_ok,
        "clinical_engine": "langgraph-agentic-v2",
    }
