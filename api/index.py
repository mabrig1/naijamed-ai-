from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

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
    plan_id: Literal["family_pass", "doctor_workspace", "formulary_student"]
    callback_url: str | None = None


class FormularyReviewCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    research_question: str = Field(min_length=3, max_length=2000)
    inclusion_criteria: str | None = Field(default=None, max_length=4000)
    exclusion_criteria: str | None = Field(default=None, max_length=4000)
    consent_to_model_improvement: bool = False


class FormularyDoiRequest(BaseModel):
    doi: str = Field(min_length=5, max_length=300)


class FormularyCorrectionRequest(BaseModel):
    field_path: str = Field(min_length=1, max_length=160)
    value: Any
    note: str | None = Field(default=None, max_length=1000)


class FormularyCitationRefreshRequest(BaseModel):
    entry_id: str | None = Field(default=None, max_length=120)


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



# -------------------------- Formulary ---------------------------------------

FORMULARY_ALLOWED_ROLES = {"researcher", "doctor", "clinic", "admin"}


def _formulary_require_user(user: dict[str, Any]) -> dict[str, Any]:
    if str(user.get("role")) not in FORMULARY_ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Formulary is available to researcher, doctor, clinic and administrator accounts.",
        )
    return user


def _formulary_is_pro(user_id: str) -> bool:
    return bool(
        get_db().clinical_subscriptions.find_one(
            {
                "user_id": user_id,
                "plan_id": "formulary_student",
                "status": {"$in": ["active", "renewing"]},
            }
        )
    )


def _formulary_account(user: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user["_id"])
    pro = user.get("role") == "admin" or _formulary_is_pro(user_id)
    review_count = get_db().formulary_reviews.count_documents({"user_id": user_id})
    paper_count = get_db().formulary_entries.count_documents({"user_id": user_id})
    return {
        "plan": "formulary_student" if pro else "free",
        "is_pro": pro,
        "review_count": review_count,
        "paper_count": paper_count,
        "review_limit": None if pro else settings.FORMULARY_FREE_REVIEW_LIMIT,
        "paper_limit": None if pro else settings.FORMULARY_FREE_PAPER_LIMIT,
        "upgrade_path": "/pricing",
    }


def _formulary_enforce_limit(user: dict[str, Any], resource: str) -> None:
    user_id = str(user["_id"])
    if user.get("role") == "admin" or _formulary_is_pro(user_id):
        return
    db = get_db()
    if resource == "review":
        used = db.formulary_reviews.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_REVIEW_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_REVIEW_LIMIT} living reviews. Upgrade to Formulary Scholar for unlimited reviews.",
            )
    if resource == "paper":
        used = db.formulary_entries.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_PAPER_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_PAPER_LIMIT} papers. Upgrade to Formulary Scholar for unlimited evidence entries.",
            )


def _formulary_review(review_id: str, user: dict[str, Any]) -> dict[str, Any]:
    row = get_db().formulary_reviews.find_one({"_id": review_id, "user_id": str(user["_id"])})
    if not row:
        raise HTTPException(status_code=404, detail="Living literature review not found")
    return row


def _clean_doi(value: str) -> str:
    doi = value.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    if "/" not in doi or len(doi) < 5:
        raise HTTPException(status_code=422, detail="Enter a valid DOI")
    return doi


def _strip_markup(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()


def _crossref_lookup(doi: str) -> dict[str, Any] | None:
    headers = {"User-Agent": "NigerFlora-Formulary/1.0"}
    params: dict[str, Any] = {}
    if settings.CROSSREF_MAILTO:
        params["mailto"] = settings.CROSSREF_MAILTO
    try:
        response = httpx.get(
            f"https://api.crossref.org/works/{quote(doi, safe='')}",
            params=params,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("message") or None
    except (httpx.HTTPError, ValueError):
        return None


def _openalex_params() -> dict[str, str]:
    return {"api_key": settings.OPENALEX_API_KEY} if settings.OPENALEX_API_KEY else {}


def _openalex_lookup(doi: str) -> dict[str, Any] | None:
    params: dict[str, Any] = {
        "filter": f"doi:https://doi.org/{doi}",
        "per_page": 1,
        "select": "id,doi,display_name,publication_date,cited_by_count,authorships,primary_location,abstract_inverted_index,type",
        **_openalex_params(),
    }
    try:
        response = httpx.get("https://api.openalex.org/works", params=params, timeout=20)
        response.raise_for_status()
        rows = (response.json() or {}).get("results") or []
        return rows[0] if rows else None
    except (httpx.HTTPError, ValueError):
        return None


def _openalex_abstract(work: dict[str, Any] | None) -> str:
    inverted = (work or {}).get("abstract_inverted_index") or {}
    positions: list[tuple[int, str]] = []
    for token, indexes in inverted.items():
        for index in indexes or []:
            if isinstance(index, int):
                positions.append((index, token))
    positions.sort(key=lambda item: item[0])
    return " ".join(token for _, token in positions)



def _crossref_authors(work: dict[str, Any] | None) -> list[str]:
    authors: list[str] = []
    for author in (work or {}).get("author") or []:
        name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
        if name:
            authors.append(name)
    return authors


def _publication_date(work: dict[str, Any] | None) -> str | None:
    if not work:
        return None
    for key in ("published-print", "published-online", "published", "issued"):
        parts = (((work.get(key) or {}).get("date-parts") or [[None]])[0])
        values = [str(value) for value in parts if value is not None]
        if values:
            return "-".join(values)
    return None


def _heuristic_pharma_extract(text: str, title: str | None = None) -> dict[str, Any]:
    sample_patterns = re.findall(r"\b(?:n|N)\s*=\s*(\d{1,6})\b", text)
    p_values = re.findall(r"\bp\s*(?:<|>|=|≤|≥)\s*0?\.\d+\b", text, flags=re.I)
    doses = re.findall(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|ug|g)(?:\s*/\s*kg)?\b", text, flags=re.I)
    return {
        "article_title": title,
        "study_design": None,
        "population": None,
        "sample_size": int(sample_patterns[0]) if sample_patterns else None,
        "intervention": None,
        "comparator": None,
        "dosing_regimen": sorted(set(doses))[:20],
        "primary_endpoints": [],
        "p_values": sorted(set(p_values))[:30],
        "confidence_intervals": [],
        "adverse_events": [],
        "pk_parameters": {
            "auc": [],
            "cmax": [],
            "tmax": [],
            "half_life": [],
            "clearance": [],
            "volume_of_distribution": [],
            "bioavailability": [],
        },
        "key_findings": [],
        "limitations": [],
        "evidence_spans": [],
    }


def _parse_model_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Model response was not a JSON object")
    return value


def _formulary_ai_extract(text: str, metadata: dict[str, Any]) -> tuple[dict[str, Any], str]:
    baseline = _heuristic_pharma_extract(text, metadata.get("title"))
    if not settings.effective_gemini_key or len(text.strip()) < 80:
        return baseline, "heuristic"

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.effective_gemini_key)
        model_name = settings.FORMULARY_LLM_MODEL or settings.CLINICAL_LLM_MODEL
        model = genai.GenerativeModel(model_name)
        source = text[:50_000]
        prompt = f"""
You are Formulary, a pharmaceutical evidence-extraction engine for postgraduate research.
Extract ONLY information supported by the supplied source. Never invent missing values.
Do not provide patient-specific medical advice.

Metadata:
{json.dumps(metadata, ensure_ascii=False)}

Source:
{source}

Return ONLY valid JSON with exactly these top-level keys:
article_title, study_design, population, sample_size, intervention, comparator,
dosing_regimen, primary_endpoints, p_values, confidence_intervals, adverse_events,
pk_parameters, key_findings, limitations, evidence_spans.

pk_parameters must contain: auc, cmax, tmax, half_life, clearance,
volume_of_distribution, bioavailability. Use arrays when multiple values exist.
evidence_spans must be an array of objects with field, page, snippet. Keep every
snippet under 240 characters and use it only as provenance for an extracted field.
If a value is not present, use null or [] rather than guessing.
"""
        response = model.generate_content(prompt)
        extracted = _parse_model_json(getattr(response, "text", "") or "")
        return extracted, f"gemini:{model_name}"
    except Exception:
        return baseline, "heuristic_fallback"


def _pdf_text(data: bytes) -> tuple[str, int]:
    if len(data) > settings.FORMULARY_PDF_MAX_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the Formulary upload limit")
    try:
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        chunks: list[str] = []
        for index, page in enumerate(reader.pages[:120], start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                chunks.append(f"[PAGE {index}]\n{page_text}")
        text = "\n\n".join(chunks)
        if len(text.strip()) < 80:
            raise HTTPException(status_code=422, detail="No usable text could be extracted from this PDF")
        return text, len(reader.pages)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {exc}")


def _entry_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["_id"],
        "review_id": row["review_id"],
        "source_type": row.get("source_type"),
        "doi": row.get("doi"),
        "title": row.get("title"),
        "journal": row.get("journal"),
        "authors": row.get("authors", []),
        "published": row.get("published"),
        "openalex_id": row.get("openalex_id"),
        "cited_by_count": row.get("cited_by_count", 0),
        "extraction": row.get("extraction", {}),
        "extraction_method": row.get("extraction_method"),
        "corrections": row.get("corrections", []),
        "citation_watch": row.get("citation_watch", []),
        "citation_watch_last_checked": row.get("citation_watch_last_checked").isoformat() if row.get("citation_watch_last_checked") else None,
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _set_nested(target: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts or len(parts) > 5:
        raise HTTPException(status_code=422, detail="Invalid correction field path")
    current = target
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _openalex_citations(openalex_id: str) -> list[dict[str, Any]]:
    work_id = openalex_id.rsplit("/", 1)[-1]
    params: dict[str, Any] = {
        "filter": f"cites:{work_id}",
        "sort": "publication_date:desc",
        "per_page": 25,
        "select": "id,doi,display_name,publication_date,cited_by_count,authorships,primary_location",
        **_openalex_params(),
    }
    try:
        response = httpx.get("https://api.openalex.org/works", params=params, timeout=25)
        response.raise_for_status()
        rows = (response.json() or {}).get("results") or []
    except (httpx.HTTPError, ValueError):
        return []

    output: list[dict[str, Any]] = []
    for row in rows:
        authors = []
        for authorship in row.get("authorships") or []:
            name = ((authorship.get("author") or {}).get("display_name") or "").strip()
            if name:
                authors.append(name)
        source = (((row.get("primary_location") or {}).get("source") or {}).get("display_name"))
        output.append(
            {
                "openalex_id": row.get("id"),
                "doi": row.get("doi"),
                "title": row.get("display_name"),
                "published": row.get("publication_date"),
                "authors": authors[:12],
                "journal": source,
                "cited_by_count": row.get("cited_by_count", 0),
            }
        )
    return output



@app.get("/api/formulary")
def formulary_home(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    db = get_db()
    rows = db.formulary_reviews.find({"user_id": str(user["_id"])}).sort("updated_at", -1).limit(100)
    reviews = []
    for row in rows:
        reviews.append(
            {
                "id": row["_id"],
                "title": row.get("title"),
                "research_question": row.get("research_question"),
                "status": row.get("status", "active"),
                "paper_count": db.formulary_entries.count_documents({"review_id": row["_id"]}),
                "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
            }
        )
    return {
        "product": "Formulary",
        "tagline": "The operating system for translational pharmaceutical science.",
        "account": _formulary_account(user),
        "reviews": reviews,
        "mvp": {
            "features": [
                "DOI metadata ingestion",
                "PDF pharmaceutical data extraction",
                "Living evidence table",
                "Field-level correction provenance",
                "Citation-watch refresh through OpenAlex",
            ],
            "coming_next": [
                "PK/PD Simulator",
                "Rotation & Residency Tracker",
                "Regulatory & Grant Copilot",
                "Journal Club Live Room",
            ],
        },
    }


@app.post("/api/formulary/reviews", status_code=201)
def formulary_create_review(body: FormularyReviewCreate, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "review")
    review_id = f"FLR-{uuid.uuid4().hex[:12].upper()}"
    row = {
        "_id": review_id,
        "user_id": str(user["_id"]),
        "title": body.title.strip(),
        "research_question": body.research_question.strip(),
        "inclusion_criteria": body.inclusion_criteria,
        "exclusion_criteria": body.exclusion_criteria,
        "consent_to_model_improvement": body.consent_to_model_improvement,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_reviews.insert_one(row)
    return {"id": review_id, "title": row["title"], "status": "active"}


@app.get("/api/formulary/reviews/{review_id}")
def formulary_review_detail(review_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    review = _formulary_review(review_id, user)
    entries = get_db().formulary_entries.find({"review_id": review_id}).sort("created_at", -1).limit(500)
    return {
        "review": {
            "id": review["_id"],
            "title": review.get("title"),
            "research_question": review.get("research_question"),
            "inclusion_criteria": review.get("inclusion_criteria"),
            "exclusion_criteria": review.get("exclusion_criteria"),
            "consent_to_model_improvement": bool(review.get("consent_to_model_improvement", False)),
            "status": review.get("status", "active"),
        },
        "entries": [_entry_public(row) for row in entries],
        "account": _formulary_account(user),
    }


@app.post("/api/formulary/reviews/{review_id}/doi", status_code=201)
def formulary_add_doi(review_id: str, body: FormularyDoiRequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    _formulary_review(review_id, user)
    _formulary_enforce_limit(user, "paper")
    doi = _clean_doi(body.doi)
    db = get_db()
    existing = db.formulary_entries.find_one({"review_id": review_id, "doi": doi})
    if existing:
        return _entry_public(existing)

    crossref = _crossref_lookup(doi) or {}
    openalex = _openalex_lookup(doi) or {}
    title = ((crossref.get("title") or [None])[0] or openalex.get("display_name") or doi)
    journal = ((crossref.get("container-title") or [None])[0] or (((openalex.get("primary_location") or {}).get("source") or {}).get("display_name")))
    abstract = _strip_markup(crossref.get("abstract")) or _openalex_abstract(openalex)
    metadata = {
        "doi": doi,
        "title": title,
        "journal": journal,
        "authors": _crossref_authors(crossref),
        "published": _publication_date(crossref) or openalex.get("publication_date"),
    }
    extraction, extraction_method = _formulary_ai_extract(abstract, metadata)
    entry_id = f"FPE-{uuid.uuid4().hex[:14].upper()}"
    row = {
        "_id": entry_id,
        "review_id": review_id,
        "user_id": str(user["_id"]),
        "source_type": "doi",
        "doi": doi,
        "title": title,
        "journal": journal,
        "authors": metadata["authors"],
        "published": metadata["published"],
        "openalex_id": openalex.get("id"),
        "cited_by_count": int(openalex.get("cited_by_count") or crossref.get("is-referenced-by-count") or 0),
        "source_excerpt": abstract[:4000],
        "extraction": extraction,
        "extraction_method": extraction_method,
        "corrections": [],
        "citation_watch": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.formulary_entries.insert_one(row)
    db.formulary_reviews.update_one({"_id": review_id}, {"$set": {"updated_at": _now()}})
    return _entry_public(row)


@app.post("/api/formulary/reviews/{review_id}/pdf", status_code=201)
async def formulary_add_pdf(
    review_id: str,
    file: UploadFile = File(...),
    doi: str | None = Form(default=None),
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_review(review_id, user)
    _formulary_enforce_limit(user, "paper")
    if file.content_type not in {"application/pdf", "application/x-pdf", "application/octet-stream"} and not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Formulary currently accepts PDF articles")
    data = await file.read()
    text, page_count = _pdf_text(data)
    normalized_doi = _clean_doi(doi) if doi else None
    crossref = _crossref_lookup(normalized_doi) if normalized_doi else None
    openalex = _openalex_lookup(normalized_doi) if normalized_doi else None
    title = (((crossref or {}).get("title") or [None])[0] or (openalex or {}).get("display_name") or (file.filename or "Uploaded article"))
    metadata = {
        "doi": normalized_doi,
        "title": title,
        "journal": (((crossref or {}).get("container-title") or [None])[0]),
        "authors": _crossref_authors(crossref),
        "published": _publication_date(crossref) or (openalex or {}).get("publication_date"),
        "page_count": page_count,
    }
    extraction, extraction_method = _formulary_ai_extract(text, metadata)
    entry_id = f"FPE-{uuid.uuid4().hex[:14].upper()}"
    row = {
        "_id": entry_id,
        "review_id": review_id,
        "user_id": str(user["_id"]),
        "source_type": "pdf",
        "filename": file.filename,
        "doi": normalized_doi,
        "title": extraction.get("article_title") or title,
        "journal": metadata["journal"],
        "authors": metadata["authors"],
        "published": metadata["published"],
        "page_count": page_count,
        "openalex_id": (openalex or {}).get("id"),
        "cited_by_count": int((openalex or {}).get("cited_by_count") or 0),
        "source_excerpt": text[:4000],
        "extraction": extraction,
        "extraction_method": extraction_method,
        "corrections": [],
        "citation_watch": [],
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_entries.insert_one(row)
    get_db().formulary_reviews.update_one({"_id": review_id}, {"$set": {"updated_at": _now()}})
    return _entry_public(row)


@app.patch("/api/formulary/entries/{entry_id}")
def formulary_correct_entry(entry_id: str, body: FormularyCorrectionRequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    db = get_db()
    row = db.formulary_entries.find_one({"_id": entry_id, "user_id": str(user["_id"])})
    if not row:
        raise HTTPException(status_code=404, detail="Formulary evidence entry not found")
    try:
        serialized = json.dumps(body.value, ensure_ascii=False)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Correction value must be JSON serializable")
    if len(serialized) > 10_000:
        raise HTTPException(status_code=422, detail="Correction value is too large")

    extraction = dict(row.get("extraction") or {})
    old_value: Any = extraction
    for part in body.field_path.split("."):
        if isinstance(old_value, dict):
            old_value = old_value.get(part)
        else:
            old_value = None
            break
    _set_nested(extraction, body.field_path, body.value)
    correction = {
        "field_path": body.field_path,
        "old_value": old_value,
        "new_value": body.value,
        "note": body.note,
        "corrected_by": str(user["_id"]),
        "corrected_at": _now(),
    }
    db.formulary_entries.update_one(
        {"_id": entry_id},
        {"$set": {"extraction": extraction, "updated_at": _now()}, "$push": {"corrections": correction}},
    )
    updated = db.formulary_entries.find_one({"_id": entry_id})
    return _entry_public(updated)


@app.post("/api/formulary/reviews/{review_id}/refresh-citations")
def formulary_refresh_citations(
    review_id: str,
    body: FormularyCitationRefreshRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_review(review_id, user)
    db = get_db()
    query: dict[str, Any] = {"review_id": review_id, "user_id": str(user["_id"])}
    if body.entry_id:
        query["_id"] = body.entry_id
    rows = list(db.formulary_entries.find(query).limit(50))
    refreshed = 0
    new_citations = 0
    for row in rows:
        openalex_id = row.get("openalex_id")
        if not openalex_id and row.get("doi"):
            work = _openalex_lookup(row["doi"])
            openalex_id = (work or {}).get("id")
            if openalex_id:
                db.formulary_entries.update_one({"_id": row["_id"]}, {"$set": {"openalex_id": openalex_id}})
        if not openalex_id:
            continue
        latest = _openalex_citations(openalex_id)
        previous_ids = {item.get("openalex_id") for item in row.get("citation_watch", []) if item.get("openalex_id")}
        additions = [item for item in latest if item.get("openalex_id") not in previous_ids]
        db.formulary_entries.update_one(
            {"_id": row["_id"]},
            {
                "$set": {
                    "citation_watch": latest,
                    "citation_watch_last_checked": _now(),
                    "updated_at": _now(),
                }
            },
        )
        refreshed += 1
        new_citations += len(additions)
    db.formulary_reviews.update_one({"_id": review_id}, {"$set": {"updated_at": _now()}})
    return {"review_id": review_id, "entries_refreshed": refreshed, "new_citations": new_citations}


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
        "formulary_student": {
            "id": "formulary_student",
            "label": "Formulary Scholar",
            "audience": "PharmD, M.Sc., Ph.D. & residents",
            "price_kobo": settings.FORMULARY_STUDENT_MONTHLY_KOBO,
            "billing": "monthly",
            "paystack_plan_code": settings.FORMULARY_STUDENT_PAYSTACK_PLAN_CODE or None,
            "allowed_roles": ["researcher", "doctor", "clinic", "admin"],
            "features": [
                "Unlimited living literature reviews",
                "DOI and PDF pharmaceutical data extraction",
                "Field-level correction provenance and evidence tables",
                "OpenAlex citation-watch refresh for included papers",
            ],
        },
    }


def _subscription_entitlements(active_plan_ids: list[str]) -> list[str]:
    entitlements = {"free_ai_triage", "red_flag_escalation", "provider_directory"}
    if "family_pass" in active_plan_ids:
        entitlements.update({"family_history", "priority_handoff", "voice_capture", "care_summary_exports"})
    if "doctor_workspace" in active_plan_ids:
        entitlements.update({"doctor_workspace", "clinical_scribing", "provider_payments", "case_audit_history"})
    if "formulary_student" in active_plan_ids:
        entitlements.update({"formulary_pro", "unlimited_literature_reviews", "citation_watch", "structured_pdf_extraction"})
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
        "subscriptions": [catalog["family_pass"], catalog["doctor_workspace"], catalog["formulary_student"]],
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
    formulary_active = sum(1 for row in active_subscriptions if row.get("plan_id") == "formulary_student")
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
            "formulary_student_active": formulary_active,
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
