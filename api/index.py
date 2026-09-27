from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
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
from app.formulary_pk import noncompartmental_analysis, one_compartment_simulation
from app.formulary_regulatory import build_evidence_source, deterministic_gap_check, generate_grounded_draft, official_sources, validate_source_ids
from app.formulary_journal import appraisal_template, evidence_snapshot, fact_check_claim
from app.formulary_grants import disclosure_watermark, funder_lens, funder_profile_assessment, normalize_percentages, project_template, readiness_assessment, safe_funder_snapshot


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

Role = Literal["patient", "researcher", "doctor", "clinic", "hmo", "admin"]


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


class PKObservation(BaseModel):
    time: float = Field(ge=0)
    concentration: float = Field(ge=0)


class FormularyPKNCARequest(BaseModel):
    title: str = Field(default="NCA Run", min_length=2, max_length=240)
    review_id: str | None = Field(default=None, max_length=120)
    entry_id: str | None = Field(default=None, max_length=120)
    observations: list[PKObservation] = Field(min_length=3, max_length=500)
    terminal_points: int = Field(default=3, ge=3, le=8)
    dose: float | None = Field(default=None, gt=0)
    route: Literal["iv", "oral", "other"] = "other"
    time_unit: str = Field(default="h", min_length=1, max_length=30)
    concentration_unit: str = Field(default="mg/L", min_length=1, max_length=40)
    dose_unit: str = Field(default="mg", min_length=1, max_length=30)


class FormularyPKSimulationRequest(BaseModel):
    title: str = Field(default="One-compartment Simulation", min_length=2, max_length=240)
    review_id: str | None = Field(default=None, max_length=120)
    entry_id: str | None = Field(default=None, max_length=120)
    model: Literal["one_compartment_iv_bolus", "one_compartment_oral"]
    dose: float = Field(gt=0)
    volume: float = Field(gt=0)
    elimination_half_life: float = Field(gt=0)
    duration: float = Field(gt=0)
    points: int = Field(default=101, ge=20, le=500)
    bioavailability: float = Field(default=1.0, gt=0, le=1)
    absorption_rate: float | None = Field(default=None, gt=0)
    time_unit: str = Field(default="h", min_length=1, max_length=30)
    dose_unit: str = Field(default="mg", min_length=1, max_length=30)
    volume_unit: str = Field(default="L", min_length=1, max_length=30)


class FormularyPortfolioProfileRequest(BaseModel):
    track: Literal["pharmd", "residency", "msc", "phd", "other"]
    program_name: str = Field(min_length=2, max_length=240)
    institution: str = Field(min_length=2, max_length=240)
    specialty: str | None = Field(default=None, max_length=160)
    start_date: date | None = None
    target_end_date: date | None = None
    summary: str | None = Field(default=None, max_length=3000)
    competencies: list[str] = Field(default_factory=list, max_length=100)
    public_enabled: bool = False
    public_slug: str | None = Field(default=None, min_length=3, max_length=80)


class FormularyPortfolioItemRequest(BaseModel):
    category: Literal[
        "rotation", "clinical_intervention", "development_plan", "evaluation",
        "research_milestone", "committee", "presentation", "publication",
        "grant", "teaching", "certification", "coursework", "experiment", "other"
    ]
    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=5000)
    occurred_on: date
    status: Literal["planned", "in_progress", "completed"] = "completed"
    competencies: list[str] = Field(default_factory=list, max_length=50)
    hours: float | None = Field(default=None, ge=0, le=10000)
    outcome: str | None = Field(default=None, max_length=2000)
    evidence_url: str | None = Field(default=None, max_length=1000)
    visibility: Literal["private", "public"] = "private"


class FormularyPortfolioItemUpdate(BaseModel):
    status: Literal["planned", "in_progress", "completed"] | None = None
    outcome: str | None = Field(default=None, max_length=2000)
    evidence_url: str | None = Field(default=None, max_length=1000)
    visibility: Literal["private", "public"] | None = None


class FormularyAttestationRequest(BaseModel):
    item_id: str = Field(min_length=3, max_length=120)
    verifier_name: str = Field(min_length=2, max_length=200)
    verifier_email: EmailStr
    message: str | None = Field(default=None, max_length=1500)


class FormularyAttestationSubmit(BaseModel):
    verifier_name: str = Field(min_length=2, max_length=200)
    verifier_email: EmailStr
    verifier_title: str | None = Field(default=None, max_length=200)
    organization: str | None = Field(default=None, max_length=240)
    comment: str | None = Field(default=None, max_length=2000)
    attest: bool


class FormularyCopilotCustomSource(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    url: str | None = Field(default=None, max_length=1200)
    excerpt: str = Field(min_length=20, max_length=12000)
    status: str = Field(default="user_supplied", max_length=80)


class FormularyCopilotWorkspaceRequest(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    purpose: Literal["specific_aims", "research_strategy", "grant_plan", "regulatory_brief", "ctd_plan", "protocol_outline", "compliance_gap"]
    objective: str = Field(min_length=20, max_length=6000)
    jurisdiction: str | None = Field(default=None, max_length=160)
    nofo_url: str | None = Field(default=None, max_length=1200)
    official_source_ids: list[str] = Field(default_factory=list, max_length=30)
    review_ids: list[str] = Field(default_factory=list, max_length=20)
    custom_sources: list[FormularyCopilotCustomSource] = Field(default_factory=list, max_length=8)
    notes: str | None = Field(default=None, max_length=12000)


class FormularyCopilotDraftRequest(BaseModel):
    instruction: str | None = Field(default=None, max_length=4000)


class FormularyJournalRoomRequest(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    review_id: str = Field(min_length=3, max_length=120)
    entry_ids: list[str] = Field(default_factory=list, min_length=1, max_length=12)
    scheduled_at: datetime | None = None
    meeting_url: str | None = Field(default=None, max_length=1200)
    agenda: list[str] = Field(default_factory=list, max_length=20)
    appraisal_template: Literal["general", "rct", "pk"] = "general"


class FormularyJournalRoomUpdate(BaseModel):
    status: Literal["scheduled", "live", "closed"] | None = None
    meeting_url: str | None = Field(default=None, max_length=1200)
    agenda: list[str] | None = Field(default=None, max_length=20)
    locked: bool | None = None


class FormularyJournalJoinRequest(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class FormularyJournalItemRequest(BaseModel):
    kind: Literal["note", "question", "claim", "decision", "action", "appraisal"]
    content: str = Field(min_length=1, max_length=5000)
    entry_id: str | None = Field(default=None, max_length=120)
    appraisal_section: str | None = Field(default=None, max_length=120)
    rating: Literal["strong", "adequate", "weak", "unclear"] | None = None
    assigned_to: str | None = Field(default=None, max_length=200)
    due_on: date | None = None


class FormularyJournalFactCheckRequest(BaseModel):
    claim: str = Field(min_length=5, max_length=3000)
    entry_ids: list[str] = Field(default_factory=list, max_length=12)


class FormularyGrantProjectRequest(BaseModel):
    title: str = Field(min_length=3, max_length=260)
    acronym: str | None = Field(default=None, max_length=40)
    project_type: Literal["flagship_research", "consortium", "implementation", "fellowship", "infrastructure"] = "flagship_research"
    originator_name: str = Field(min_length=2, max_length=200)
    host_institution: str | None = Field(default=None, max_length=240)
    country: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    duration_months: int | None = Field(default=None, ge=1, le=120)
    budget_amount: float | None = Field(default=None, gt=0)
    budget_currency: str = Field(default="NGN", min_length=3, max_length=8)
    funder_name: str | None = Field(default=None, max_length=240)
    call_reference: str | None = Field(default=None, max_length=200)
    call_url: str | None = Field(default=None, max_length=1200)
    deadline: datetime | None = None
    summary: str | None = Field(default=None, max_length=8000)
    problem_statement: str | None = Field(default=None, max_length=12000)
    objectives: list[str] = Field(default_factory=list, max_length=20)
    confidentiality_level: Literal["private", "controlled", "consortium"] = "controlled"


class FormularyGrantProjectUpdate(BaseModel):
    acronym: str | None = Field(default=None, max_length=40)
    host_institution: str | None = Field(default=None, max_length=240)
    country: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=200)
    duration_months: int | None = Field(default=None, ge=1, le=120)
    budget_amount: float | None = Field(default=None, gt=0)
    budget_currency: str | None = Field(default=None, min_length=3, max_length=8)
    funder_name: str | None = Field(default=None, max_length=240)
    call_reference: str | None = Field(default=None, max_length=200)
    call_url: str | None = Field(default=None, max_length=1200)
    deadline: datetime | None = None
    summary: str | None = Field(default=None, max_length=8000)
    problem_statement: str | None = Field(default=None, max_length=12000)
    objectives: list[str] | None = Field(default=None, max_length=20)
    confidentiality_level: Literal["private", "controlled", "consortium"] | None = None
    status: Literal["concept", "institutional_engagement", "consortium_building", "drafting", "internal_review", "submitted", "awarded", "declined"] | None = None


class FormularyGrantPartnerRequest(BaseModel):
    organization: str = Field(min_length=2, max_length=240)
    country: str | None = Field(default=None, max_length=120)
    partner_type: Literal["university", "hospital", "government", "ngo", "industry", "sme", "research_institute", "community", "other"] = "university"
    status: Literal["prospect", "contacted", "interested", "committed", "confirmed", "declined"] = "prospect"
    proposed_role: str | None = Field(default=None, max_length=3000)
    lead_contact: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = None


class FormularyGrantWorkPackageRequest(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    sequence: int = Field(ge=1, le=99)
    lead_partner: str | None = Field(default=None, max_length=240)
    objective: str | None = Field(default=None, max_length=5000)
    outputs: list[str] = Field(default_factory=list, max_length=30)
    budget_amount: float | None = Field(default=None, ge=0)


class FormularyGrantMilestoneRequest(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    milestone_type: Literal["proposal", "partnership", "ethics", "scientific", "financial", "submission", "other"] = "proposal"
    due_on: date | None = None
    status: Literal["planned", "in_progress", "completed", "blocked"] = "planned"
    owner: str | None = Field(default=None, max_length=200)
    evidence: str | None = Field(default=None, max_length=1000)


class FormularyGrantIPAssetRequest(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    category: Literal["background_ip", "proposal", "software", "method", "dataset", "partner_relationship", "other"]
    ownership_statement: str = Field(min_length=10, max_length=5000)
    evidence_reference: str | None = Field(default=None, max_length=1200)
    created_before_collaboration: bool = True
    disclosure_level: Literal["private", "summary_only", "controlled", "full_after_agreement"] = "controlled"


class FormularyGrantDisclosureRequest(BaseModel):
    recipient_name: str = Field(min_length=2, max_length=200)
    recipient_organization: str | None = Field(default=None, max_length=240)
    disclosed_at: datetime
    material: str = Field(min_length=2, max_length=500)
    version: str | None = Field(default=None, max_length=80)
    purpose: str | None = Field(default=None, max_length=1000)
    confidentiality_basis: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class FormularyGrantFunderProfileRequest(BaseModel):
    funder_lens: Literal["cross_funder", "horizon_europe", "nih", "wellcome"] = "cross_funder"
    innovation_case: str | None = Field(default=None, max_length=8000)
    global_relevance: str | None = Field(default=None, max_length=8000)
    rigor_feasibility: str | None = Field(default=None, max_length=12000)
    impact_pathway: str | None = Field(default=None, max_length=12000)
    institutional_capacity: str | None = Field(default=None, max_length=8000)
    ethics_governance: str | None = Field(default=None, max_length=8000)
    data_open_science: str | None = Field(default=None, max_length=8000)
    equity_capacity_building: str | None = Field(default=None, max_length=8000)
    sustainability_scale: str | None = Field(default=None, max_length=8000)
    policy_translation: str | None = Field(default=None, max_length=8000)
    monitoring_evaluation: str | None = Field(default=None, max_length=8000)
    risk_management: str | None = Field(default=None, max_length=8000)
    cofunding_leverage: str | None = Field(default=None, max_length=5000)
    impact_metrics: list[str] = Field(default_factory=list, max_length=30)
    capacity_outputs: list[str] = Field(default_factory=list, max_length=30)
    data_management_commitments: list[str] = Field(default_factory=list, max_length=30)
    sdg_alignment: list[str] = Field(default_factory=list, max_length=17)
    keywords: list[str] = Field(default_factory=list, max_length=30)


class FormularyGrantFunderRoomRequest(BaseModel):
    recipient_label: str | None = Field(default=None, max_length=240)
    expires_in_days: int = Field(default=14, ge=1, le=30)
    include_budget: bool = True
    include_partners: bool = True
    include_milestones: bool = True
    note: str | None = Field(default=None, max_length=1200)


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
    allowed_self_roles = {"patient", "researcher", "doctor", "clinic", "hmo"}
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
    pk_run_count = get_db().formulary_pk_runs.count_documents({"user_id": user_id})
    portfolio_item_count = get_db().formulary_portfolio_items.count_documents({"user_id": user_id})
    copilot_workspace_count = get_db().formulary_copilot_workspaces.count_documents({"user_id": user_id})
    copilot_draft_count = get_db().formulary_copilot_drafts.count_documents({"user_id": user_id})
    journal_room_count = get_db().formulary_journal_rooms.count_documents({"owner_user_id": user_id})
    journal_factcheck_count = get_db().formulary_journal_factchecks.count_documents({"requested_by": user_id})
    grant_project_count = get_db().formulary_grant_projects.count_documents({"user_id": user_id})
    return {
        "plan": "formulary_student" if pro else "free",
        "is_pro": pro,
        "review_count": review_count,
        "paper_count": paper_count,
        "pk_run_count": pk_run_count,
        "portfolio_item_count": portfolio_item_count,
        "copilot_workspace_count": copilot_workspace_count,
        "copilot_draft_count": copilot_draft_count,
        "journal_room_count": journal_room_count,
        "journal_factcheck_count": journal_factcheck_count,
        "grant_project_count": grant_project_count,
        "review_limit": None if pro else settings.FORMULARY_FREE_REVIEW_LIMIT,
        "paper_limit": None if pro else settings.FORMULARY_FREE_PAPER_LIMIT,
        "pk_run_limit": None if pro else settings.FORMULARY_FREE_PK_RUN_LIMIT,
        "portfolio_item_limit": None if pro else settings.FORMULARY_FREE_PORTFOLIO_ITEM_LIMIT,
        "copilot_workspace_limit": None if pro else settings.FORMULARY_FREE_COPILOT_WORKSPACE_LIMIT,
        "copilot_draft_limit": None if pro else settings.FORMULARY_FREE_COPILOT_DRAFT_LIMIT,
        "journal_room_limit": None if pro else settings.FORMULARY_FREE_JOURNAL_ROOM_LIMIT,
        "journal_factcheck_limit": None if pro else settings.FORMULARY_FREE_JOURNAL_FACTCHECK_LIMIT,
        "grant_project_limit": None if pro else settings.FORMULARY_FREE_GRANT_PROJECT_LIMIT,
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
    if resource == "pk_run":
        used = db.formulary_pk_runs.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_PK_RUN_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_PK_RUN_LIMIT} saved PK/PD runs. Upgrade to Formulary Scholar for unlimited simulations.",
            )
    if resource == "portfolio_item":
        used = db.formulary_portfolio_items.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_PORTFOLIO_ITEM_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_PORTFOLIO_ITEM_LIMIT} portfolio items. Upgrade to Formulary Scholar for unlimited tracking.",
            )
    if resource == "copilot_workspace":
        used = db.formulary_copilot_workspaces.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_COPILOT_WORKSPACE_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_COPILOT_WORKSPACE_LIMIT} regulatory/grant workspace. Upgrade to Formulary Scholar for unlimited workspaces.",
            )
    if resource == "copilot_draft":
        used = db.formulary_copilot_drafts.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_COPILOT_DRAFT_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_COPILOT_DRAFT_LIMIT} generated copilot drafts. Upgrade to Formulary Scholar for unlimited drafting.",
            )
    if resource == "journal_room":
        used = db.formulary_journal_rooms.count_documents({"owner_user_id": user_id})
        if used >= settings.FORMULARY_FREE_JOURNAL_ROOM_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_JOURNAL_ROOM_LIMIT} Journal Club rooms. Upgrade to Formulary Scholar for unlimited rooms.",
            )
    if resource == "journal_factcheck":
        used = db.formulary_journal_factchecks.count_documents({"requested_by": user_id})
        if used >= settings.FORMULARY_FREE_JOURNAL_FACTCHECK_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_JOURNAL_FACTCHECK_LIMIT} Journal Club fact checks. Upgrade to Formulary Scholar for unlimited checks.",
            )
    if resource == "grant_project":
        used = db.formulary_grant_projects.count_documents({"user_id": user_id})
        if used >= settings.FORMULARY_FREE_GRANT_PROJECT_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"Free Formulary accounts support {settings.FORMULARY_FREE_GRANT_PROJECT_LIMIT} International Grant Project. Upgrade to Formulary Scholar for unlimited projects.",
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
                "PK/PD Simulator: NCA and one-compartment models",
                "Rotation & Research Portfolio Tracker",
                "Regulatory & Grant Copilot with source traceability",
                "Journal Club Live Room with evidence-grounded fact checks",
                "International Grant Project Studio with IP/disclosure controls",
            ],
            "coming_next": [],
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



def _formulary_validate_pk_links(user: dict[str, Any], review_id: str | None, entry_id: str | None) -> None:
    db = get_db()
    user_id = str(user["_id"])
    if review_id and not db.formulary_reviews.find_one({"_id": review_id, "user_id": user_id}):
        raise HTTPException(status_code=404, detail="Linked Formulary review not found")
    if entry_id:
        query: dict[str, Any] = {"_id": entry_id, "user_id": user_id}
        if review_id:
            query["review_id"] = review_id
        if not db.formulary_entries.find_one(query):
            raise HTTPException(status_code=404, detail="Linked Formulary evidence entry not found")


def _pk_run_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["_id"],
        "kind": row.get("kind"),
        "title": row.get("title"),
        "review_id": row.get("review_id"),
        "entry_id": row.get("entry_id"),
        "input": row.get("input", {}),
        "result": row.get("result", {}),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
    }


@app.get("/api/formulary/pkpd/runs")
def formulary_pk_runs(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    rows = get_db().formulary_pk_runs.find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(50)
    return {"runs": [_pk_run_public(row) for row in rows], "account": _formulary_account(user)}


@app.post("/api/formulary/pkpd/nca", status_code=201)
def formulary_pk_nca(body: FormularyPKNCARequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "pk_run")
    _formulary_validate_pk_links(user, body.review_id, body.entry_id)
    payload = body.model_dump()
    observations = [{"time": row["time"], "concentration": row["concentration"]} for row in payload["observations"]]
    try:
        result = noncompartmental_analysis(
            observations,
            terminal_points=body.terminal_points,
            dose=body.dose,
            route=body.route,
            time_unit=body.time_unit,
            concentration_unit=body.concentration_unit,
            dose_unit=body.dose_unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    run_id = f"FPK-{uuid.uuid4().hex[:14].upper()}"
    row = {
        "_id": run_id,
        "user_id": str(user["_id"]),
        "kind": "nca",
        "title": body.title.strip(),
        "review_id": body.review_id,
        "entry_id": body.entry_id,
        "input": {
            "observations": observations,
            "terminal_points": body.terminal_points,
            "dose": body.dose,
            "route": body.route,
            "time_unit": body.time_unit,
            "concentration_unit": body.concentration_unit,
            "dose_unit": body.dose_unit,
        },
        "result": result,
        "created_at": _now(),
    }
    get_db().formulary_pk_runs.insert_one(row)
    return _pk_run_public(row)


@app.post("/api/formulary/pkpd/simulate", status_code=201)
def formulary_pk_simulate(body: FormularyPKSimulationRequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "pk_run")
    _formulary_validate_pk_links(user, body.review_id, body.entry_id)
    try:
        result = one_compartment_simulation(
            model=body.model,
            dose=body.dose,
            volume=body.volume,
            elimination_half_life=body.elimination_half_life,
            duration=body.duration,
            points=body.points,
            bioavailability=body.bioavailability,
            absorption_rate=body.absorption_rate,
            time_unit=body.time_unit,
            dose_unit=body.dose_unit,
            volume_unit=body.volume_unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    run_id = f"FPK-{uuid.uuid4().hex[:14].upper()}"
    row = {
        "_id": run_id,
        "user_id": str(user["_id"]),
        "kind": "simulation",
        "title": body.title.strip(),
        "review_id": body.review_id,
        "entry_id": body.entry_id,
        "input": body.model_dump(),
        "result": result,
        "created_at": _now(),
    }
    get_db().formulary_pk_runs.insert_one(row)
    return _pk_run_public(row)




def _portfolio_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if len(slug) < 3:
        slug = f"researcher-{uuid.uuid4().hex[:8]}"
    return slug[:80]


def _portfolio_item_public(row: dict[str, Any], *, include_private: bool = False) -> dict[str, Any]:
    result = {
        "id": row["_id"],
        "category": row.get("category"),
        "title": row.get("title"),
        "description": row.get("description"),
        "occurred_on": row.get("occurred_on"),
        "status": row.get("status"),
        "competencies": row.get("competencies", []),
        "hours": row.get("hours"),
        "outcome": row.get("outcome"),
        "visibility": row.get("visibility", "private"),
        "attestation_status": row.get("attestation_status", "unattested"),
        "attested_by": row.get("attested_by"),
        "attested_at": row.get("attested_at").isoformat() if row.get("attested_at") else None,
    }
    if include_private or row.get("visibility") == "public":
        result["evidence_url"] = row.get("evidence_url")
    return result


def _portfolio_summary(items: list[dict[str, Any]], competencies: list[str]) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    competency_hits: dict[str, int] = {name: 0 for name in competencies}
    total_hours = 0.0
    attested = 0
    for item in items:
        category = str(item.get("category") or "other")
        status_name = str(item.get("status") or "planned")
        by_category[category] = by_category.get(category, 0) + 1
        by_status[status_name] = by_status.get(status_name, 0) + 1
        total_hours += float(item.get("hours") or 0)
        if item.get("attestation_status") == "attested":
            attested += 1
        for competency in item.get("competencies") or []:
            competency_hits[competency] = competency_hits.get(competency, 0) + 1
    return {
        "total_items": len(items),
        "completed_items": by_status.get("completed", 0),
        "attested_items": attested,
        "total_hours": round(total_hours, 2),
        "by_category": by_category,
        "by_status": by_status,
        "competency_activity": competency_hits,
    }


def _portfolio_payload(user: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    user_id = str(user["_id"])
    profile = db.formulary_portfolios.find_one({"user_id": user_id})
    items = list(db.formulary_portfolio_items.find({"user_id": user_id}).sort("occurred_on", -1).limit(500))
    return {
        "profile": {
            "track": profile.get("track") if profile else None,
            "program_name": profile.get("program_name") if profile else None,
            "institution": profile.get("institution") if profile else None,
            "specialty": profile.get("specialty") if profile else None,
            "start_date": profile.get("start_date") if profile else None,
            "target_end_date": profile.get("target_end_date") if profile else None,
            "summary": profile.get("summary") if profile else None,
            "competencies": profile.get("competencies", []) if profile else [],
            "public_enabled": bool(profile.get("public_enabled", False)) if profile else False,
            "public_slug": profile.get("public_slug") if profile else None,
        },
        "items": [_portfolio_item_public(row, include_private=True) for row in items],
        "summary": _portfolio_summary(items, profile.get("competencies", []) if profile else []),
        "account": _formulary_account(user),
    }


@app.get("/api/formulary/portfolio")
def formulary_portfolio(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    return _portfolio_payload(user)


@app.put("/api/formulary/portfolio/profile")
def formulary_portfolio_profile(body: FormularyPortfolioProfileRequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    db = get_db()
    user_id = str(user["_id"])
    slug = _portfolio_slug(body.public_slug or body.program_name)
    if body.public_enabled:
        conflict = db.formulary_portfolios.find_one({"public_slug": slug, "user_id": {"$ne": user_id}})
        if conflict:
            slug = f"{slug[:70]}-{uuid.uuid4().hex[:6]}"
    doc = {
        "user_id": user_id,
        "track": body.track,
        "program_name": body.program_name.strip(),
        "institution": body.institution.strip(),
        "specialty": body.specialty,
        "start_date": body.start_date.isoformat() if body.start_date else None,
        "target_end_date": body.target_end_date.isoformat() if body.target_end_date else None,
        "summary": body.summary,
        "competencies": [value.strip() for value in body.competencies if value.strip()],
        "public_enabled": body.public_enabled,
        "public_slug": slug if body.public_enabled else None,
        "updated_at": _now(),
    }
    db.formulary_portfolios.update_one(
        {"user_id": user_id},
        {"$set": doc, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
    )
    return _portfolio_payload(user)


@app.post("/api/formulary/portfolio/items", status_code=201)
def formulary_portfolio_add_item(body: FormularyPortfolioItemRequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "portfolio_item")
    if body.evidence_url and not re.match(r"^https?://", body.evidence_url, flags=re.I):
        raise HTTPException(status_code=422, detail="Evidence URL must begin with http:// or https://")
    row = {
        "_id": f"FPI-{uuid.uuid4().hex[:14].upper()}",
        "user_id": str(user["_id"]),
        "category": body.category,
        "title": body.title.strip(),
        "description": body.description,
        "occurred_on": body.occurred_on.isoformat(),
        "status": body.status,
        "competencies": [value.strip() for value in body.competencies if value.strip()],
        "hours": body.hours,
        "outcome": body.outcome,
        "evidence_url": body.evidence_url,
        "visibility": body.visibility,
        "attestation_status": "unattested",
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_portfolio_items.insert_one(row)
    return _portfolio_item_public(row, include_private=True)


@app.patch("/api/formulary/portfolio/items/{item_id}")
def formulary_portfolio_update_item(
    item_id: str,
    body: FormularyPortfolioItemUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    db = get_db()
    row = db.formulary_portfolio_items.find_one({"_id": item_id, "user_id": str(user["_id"])})
    if not row:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    update = body.model_dump(exclude_none=True)
    if update.get("evidence_url") and not re.match(r"^https?://", str(update["evidence_url"]), flags=re.I):
        raise HTTPException(status_code=422, detail="Evidence URL must begin with http:// or https://")
    update["updated_at"] = _now()
    db.formulary_portfolio_items.update_one({"_id": item_id}, {"$set": update})
    updated = db.formulary_portfolio_items.find_one({"_id": item_id})
    return _portfolio_item_public(updated, include_private=True)


@app.post("/api/formulary/portfolio/attestations", status_code=201)
def formulary_create_attestation(body: FormularyAttestationRequest, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    db = get_db()
    item = db.formulary_portfolio_items.find_one({"_id": body.item_id, "user_id": str(user["_id"])})
    if not item:
        raise HTTPException(status_code=404, detail="Portfolio item not found")
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    row = {
        "_id": f"FAT-{uuid.uuid4().hex[:14].upper()}",
        "token_hash": token_hash,
        "user_id": str(user["_id"]),
        "item_id": body.item_id,
        "verifier_name": body.verifier_name.strip(),
        "verifier_email": str(body.verifier_email).lower(),
        "message": body.message,
        "status": "pending",
        "expires_at": _now() + timedelta(days=14),
        "created_at": _now(),
        "updated_at": _now(),
    }
    db.formulary_attestations.insert_one(row)
    db.formulary_portfolio_items.update_one(
        {"_id": body.item_id},
        {"$set": {"attestation_status": "pending", "updated_at": _now()}},
    )
    return {
        "id": row["_id"],
        "status": "pending",
        "expires_at": row["expires_at"].isoformat(),
        "attestation_path": f"/formulary/attest/{raw_token}",
        "note": "Share this private attestation link only with the intended verifier. Formulary records the verifier's attestation but does not independently validate institutional identity.",
    }


def _attestation_by_token(token: str) -> dict[str, Any]:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = get_db().formulary_attestations.find_one({"token_hash": token_hash})
    if not row:
        raise HTTPException(status_code=404, detail="Attestation request not found")
    if row.get("expires_at") and row["expires_at"] < _now() and row.get("status") == "pending":
        get_db().formulary_attestations.update_one({"_id": row["_id"]}, {"$set": {"status": "expired", "updated_at": _now()}})
        row["status"] = "expired"
    return row


@app.get("/api/formulary/attest/{token}")
def formulary_attestation_detail(token: str):
    row = _attestation_by_token(token)
    item = get_db().formulary_portfolio_items.find_one({"_id": row["item_id"]})
    user = get_db().users.find_one({"_id": ObjectId(row["user_id"])})
    return {
        "status": row.get("status"),
        "expires_at": row.get("expires_at").isoformat() if row.get("expires_at") else None,
        "researcher_name": user.get("full_name") if user else "Formulary researcher",
        "item": {
            "title": item.get("title") if item else None,
            "category": item.get("category") if item else None,
            "description": item.get("description") if item else None,
            "occurred_on": item.get("occurred_on") if item else None,
            "outcome": item.get("outcome") if item else None,
        },
        "intended_verifier_name": row.get("verifier_name"),
        "message": row.get("message"),
        "identity_notice": "This is a self-service supervisor/preceptor attestation. Formulary records the response but does not independently certify the verifier's employment or institution.",
    }


@app.post("/api/formulary/attest/{token}")
def formulary_submit_attestation(token: str, body: FormularyAttestationSubmit):
    db = get_db()
    row = _attestation_by_token(token)
    if row.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Attestation request is {row.get('status')}")
    if str(body.verifier_email).lower() != str(row.get("verifier_email") or "").lower():
        raise HTTPException(status_code=403, detail="Verifier email does not match the intended attestation recipient")
    status_name = "attested" if body.attest else "declined"
    update = {
        "status": status_name,
        "response": {
            "verifier_name": body.verifier_name.strip(),
            "verifier_title": body.verifier_title,
            "organization": body.organization,
            "comment": body.comment,
        },
        "responded_at": _now(),
        "updated_at": _now(),
    }
    db.formulary_attestations.update_one({"_id": row["_id"]}, {"$set": update})
    item_update: dict[str, Any] = {
        "attestation_status": status_name,
        "updated_at": _now(),
    }
    if body.attest:
        item_update.update(
            {
                "attested_by": {
                    "name": body.verifier_name.strip(),
                    "title": body.verifier_title,
                    "organization": body.organization,
                },
                "attested_at": _now(),
            }
        )
    db.formulary_portfolio_items.update_one({"_id": row["item_id"]}, {"$set": item_update})
    return {"status": status_name, "message": "Attestation response recorded."}


@app.get("/api/formulary/portfolio/public/{slug}")
def formulary_public_portfolio(slug: str):
    db = get_db()
    profile = db.formulary_portfolios.find_one({"public_slug": slug, "public_enabled": True})
    if not profile:
        raise HTTPException(status_code=404, detail="Public Formulary portfolio not found")
    user = db.users.find_one({"_id": ObjectId(profile["user_id"])})
    items = list(
        db.formulary_portfolio_items.find(
            {"user_id": profile["user_id"], "visibility": "public"}
        ).sort("occurred_on", -1).limit(300)
    )
    return {
        "researcher": {
            "name": user.get("full_name") if user else "Formulary researcher",
            "track": profile.get("track"),
            "program_name": profile.get("program_name"),
            "institution": profile.get("institution"),
            "specialty": profile.get("specialty"),
            "summary": profile.get("summary"),
            "start_date": profile.get("start_date"),
            "target_end_date": profile.get("target_end_date"),
        },
        "items": [_portfolio_item_public(row) for row in items],
        "summary": _portfolio_summary(items, profile.get("competencies", [])),
        "verification_notice": "Attested items reflect a response through a private Formulary attestation link; Formulary does not independently certify institutional identity.",
    }




def _copilot_evidence_rows(user_id: str, review_ids: list[str]) -> list[dict[str, Any]]:
    db = get_db()
    rows: list[dict[str, Any]] = []
    for review_id in review_ids:
        review = db.formulary_reviews.find_one({"_id": review_id, "user_id": user_id})
        if not review:
            raise HTTPException(status_code=404, detail=f"Formulary review not found: {review_id}")
        entries = db.formulary_entries.find({"review_id": review_id, "user_id": user_id}).sort("created_at", -1).limit(25)
        rows.extend(build_evidence_source(entry) for entry in entries)
        if len(rows) >= 50:
            break
    return rows[:50]


def _copilot_custom_rows(workspace: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(workspace.get("custom_sources") or [], start=1):
        rows.append(
            {
                "id": source.get("id") or f"custom:{workspace['_id']}:{index}",
                "organization": "User-supplied source",
                "title": source.get("title") or f"Custom source {index}",
                "status": source.get("status") or "user_supplied",
                "issued": None,
                "url": source.get("url"),
                "topic": "user_source",
                "summary": source.get("excerpt") or "",
            }
        )
    return rows


def _copilot_workspace_public(row: dict[str, Any], *, include_sources: bool = False) -> dict[str, Any]:
    output = {
        "id": row["_id"],
        "title": row.get("title"),
        "purpose": row.get("purpose"),
        "objective": row.get("objective"),
        "jurisdiction": row.get("jurisdiction"),
        "nofo_url": row.get("nofo_url"),
        "official_source_ids": row.get("official_source_ids", []),
        "review_ids": row.get("review_ids", []),
        "notes": row.get("notes"),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }
    if include_sources:
        output["custom_sources"] = row.get("custom_sources", [])
    return output


@app.get("/api/formulary/copilot/sources")
def formulary_copilot_sources(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    user_id = str(user["_id"])
    reviews = get_db().formulary_reviews.find({"user_id": user_id}).sort("updated_at", -1).limit(100)
    return {
        "official_sources": official_sources(),
        "reviews": [
            {
                "id": row["_id"],
                "title": row.get("title"),
                "research_question": row.get("research_question"),
                "paper_count": get_db().formulary_entries.count_documents({"review_id": row["_id"], "user_id": user_id}),
            }
            for row in reviews
        ],
        "account": _formulary_account(user),
        "source_policy": {
            "official": "Official source metadata is curated and carries final/draft/current-instructions status.",
            "literature": "Formulary review papers are grounded from the user's structured evidence library.",
            "custom": "Custom source excerpts are used only when the user supplies them; Formulary does not assume the URL contents.",
        },
    }


@app.get("/api/formulary/copilot")
def formulary_copilot_home(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    user_id = str(user["_id"])
    db = get_db()
    rows = db.formulary_copilot_workspaces.find({"user_id": user_id}).sort("updated_at", -1).limit(100)
    workspaces = []
    for row in rows:
        payload = _copilot_workspace_public(row)
        payload["draft_count"] = db.formulary_copilot_drafts.count_documents({"user_id": user_id, "workspace_id": row["_id"]})
        workspaces.append(payload)
    return {"workspaces": workspaces, "account": _formulary_account(user)}


@app.post("/api/formulary/copilot/workspaces", status_code=201)
def formulary_create_copilot_workspace(
    body: FormularyCopilotWorkspaceRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "copilot_workspace")
    user_id = str(user["_id"])

    if body.nofo_url and not re.match(r"^https?://", body.nofo_url, flags=re.I):
        raise HTTPException(status_code=422, detail="NOFO / source URL must begin with http:// or https://")
    known = {row["id"] for row in official_sources()}
    unknown = [source_id for source_id in body.official_source_ids if source_id not in known]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown official source IDs: {', '.join(unknown)}")

    _copilot_evidence_rows(user_id, body.review_ids)
    workspace_id = f"FCW-{uuid.uuid4().hex[:14].upper()}"
    custom_sources = []
    for index, source in enumerate(body.custom_sources, start=1):
        if source.url and not re.match(r"^https?://", source.url, flags=re.I):
            raise HTTPException(status_code=422, detail=f"Custom source {index} URL must begin with http:// or https://")
        custom_sources.append(
            {
                "id": f"custom:{workspace_id}:{index}",
                "title": source.title.strip(),
                "url": source.url,
                "excerpt": source.excerpt.strip(),
                "status": source.status.strip() or "user_supplied",
            }
        )

    row = {
        "_id": workspace_id,
        "user_id": user_id,
        "title": body.title.strip(),
        "purpose": body.purpose,
        "objective": body.objective.strip(),
        "jurisdiction": body.jurisdiction,
        "nofo_url": body.nofo_url,
        "official_source_ids": list(dict.fromkeys(body.official_source_ids)),
        "review_ids": list(dict.fromkeys(body.review_ids)),
        "custom_sources": custom_sources,
        "notes": body.notes,
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_copilot_workspaces.insert_one(row)
    return _copilot_workspace_public(row, include_sources=True)


@app.get("/api/formulary/copilot/workspaces/{workspace_id}")
def formulary_copilot_workspace(workspace_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    user_id = str(user["_id"])
    db = get_db()
    row = db.formulary_copilot_workspaces.find_one({"_id": workspace_id, "user_id": user_id})
    if not row:
        raise HTTPException(status_code=404, detail="Regulatory / grant workspace not found")
    drafts = db.formulary_copilot_drafts.find({"workspace_id": workspace_id, "user_id": user_id}).sort("created_at", -1).limit(50)
    return {
        "workspace": _copilot_workspace_public(row, include_sources=True),
        "drafts": [
            {
                "id": draft["_id"],
                "purpose": draft.get("purpose"),
                "content": draft.get("content"),
                "generation_method": draft.get("generation_method"),
                "cited_source_ids": draft.get("cited_source_ids", []),
                "source_snapshot": draft.get("source_snapshot", []),
                "gap_check": draft.get("gap_check", []),
                "created_at": draft.get("created_at").isoformat() if draft.get("created_at") else None,
            }
            for draft in drafts
        ],
        "account": _formulary_account(user),
    }


@app.get("/api/formulary/copilot/workspaces/{workspace_id}/gap-check")
def formulary_copilot_gap_check(workspace_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    user_id = str(user["_id"])
    row = get_db().formulary_copilot_workspaces.find_one({"_id": workspace_id, "user_id": user_id})
    if not row:
        raise HTTPException(status_code=404, detail="Regulatory / grant workspace not found")
    official_rows = validate_source_ids(row.get("official_source_ids") or [])
    evidence_rows = _copilot_evidence_rows(user_id, row.get("review_ids") or []) + _copilot_custom_rows(row)
    gaps = deterministic_gap_check(
        purpose=str(row.get("purpose")),
        official_rows=official_rows,
        evidence_rows=evidence_rows,
        nofo_url=row.get("nofo_url"),
    )
    return {"workspace_id": workspace_id, "gaps": gaps, "source_count": len(official_rows) + len(evidence_rows)}


@app.post("/api/formulary/copilot/workspaces/{workspace_id}/draft", status_code=201)
def formulary_copilot_generate_draft(
    workspace_id: str,
    body: FormularyCopilotDraftRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "copilot_draft")
    user_id = str(user["_id"])
    db = get_db()
    workspace = db.formulary_copilot_workspaces.find_one({"_id": workspace_id, "user_id": user_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Regulatory / grant workspace not found")

    official_rows = validate_source_ids(workspace.get("official_source_ids") or [])
    evidence_rows = _copilot_evidence_rows(user_id, workspace.get("review_ids") or [])
    custom_rows = _copilot_custom_rows(workspace)
    grounding_rows = evidence_rows + custom_rows
    gaps = deterministic_gap_check(
        purpose=str(workspace.get("purpose")),
        official_rows=official_rows,
        evidence_rows=grounding_rows,
        nofo_url=workspace.get("nofo_url"),
    )
    notes_parts = []
    if workspace.get("jurisdiction"):
        notes_parts.append(f"Target jurisdiction / regulator: {workspace['jurisdiction']}")
    if workspace.get("notes"):
        notes_parts.append(str(workspace["notes"]))
    if body.instruction:
        notes_parts.append(f"Draft instruction: {body.instruction}")
    content, generation_method, cited_ids = generate_grounded_draft(
        purpose=str(workspace["purpose"]),
        title=str(workspace["title"]),
        objective=str(workspace["objective"]),
        notes="\n\n".join(notes_parts) or None,
        nofo_url=workspace.get("nofo_url"),
        official_rows=official_rows,
        evidence_rows=grounding_rows,
        gaps=gaps,
    )
    snapshot = official_rows + grounding_rows
    draft_id = f"FCD-{uuid.uuid4().hex[:14].upper()}"
    draft = {
        "_id": draft_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "purpose": workspace["purpose"],
        "content": content,
        "generation_method": generation_method,
        "cited_source_ids": cited_ids,
        "source_snapshot": snapshot,
        "gap_check": gaps,
        "instruction": body.instruction,
        "created_at": _now(),
    }
    db.formulary_copilot_drafts.insert_one(draft)
    db.formulary_copilot_workspaces.update_one({"_id": workspace_id}, {"$set": {"updated_at": _now()}})
    return {
        "id": draft_id,
        "workspace_id": workspace_id,
        "content": content,
        "generation_method": generation_method,
        "cited_source_ids": cited_ids,
        "source_snapshot": snapshot,
        "gap_check": gaps,
        "created_at": draft["created_at"].isoformat(),
    }




def _journal_room_access(room_id: str, user: dict[str, Any]) -> dict[str, Any]:
    user_id = str(user["_id"])
    row = get_db().formulary_journal_rooms.find_one({"_id": room_id})
    if not row:
        raise HTTPException(status_code=404, detail="Journal Club room not found")
    if user.get("role") == "admin":
        return row
    if row.get("owner_user_id") != user_id and user_id not in (row.get("member_user_ids") or []):
        raise HTTPException(status_code=403, detail="You are not a member of this Journal Club room")
    return row


def _journal_room_entries(room: dict[str, Any]) -> list[dict[str, Any]]:
    ids = list(room.get("entry_ids") or [])
    if not ids:
        return []
    rows = list(
        get_db().formulary_entries.find(
            {
                "_id": {"$in": ids},
                "review_id": room.get("review_id"),
                "user_id": room.get("owner_user_id"),
            }
        )
    )
    by_id = {row["_id"]: row for row in rows}
    return [by_id[entry_id] for entry_id in ids if entry_id in by_id]


def _journal_participants(room: dict[str, Any]) -> list[dict[str, Any]]:
    ids = [room.get("owner_user_id")] + list(room.get("member_user_ids") or [])
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for user_id in ids:
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        try:
            user = get_db().users.find_one({"_id": ObjectId(str(user_id))})
        except Exception:
            user = None
        output.append(
            {
                "user_id": str(user_id),
                "name": user.get("full_name") if user else "Formulary participant",
                "role": user.get("role") if user else None,
                "host": str(user_id) == str(room.get("owner_user_id")),
            }
        )
    return output


def _journal_room_public(room: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": room["_id"],
        "title": room.get("title"),
        "review_id": room.get("review_id"),
        "entry_ids": room.get("entry_ids", []),
        "scheduled_at": room.get("scheduled_at").isoformat() if room.get("scheduled_at") else None,
        "meeting_url": room.get("meeting_url"),
        "agenda": room.get("agenda", []),
        "appraisal_template": room.get("appraisal_template", "general"),
        "status": room.get("status", "scheduled"),
        "locked": bool(room.get("locked", False)),
        "owner_user_id": room.get("owner_user_id"),
        "member_count": len(room.get("member_user_ids") or []),
        "created_at": room.get("created_at").isoformat() if room.get("created_at") else None,
        "updated_at": room.get("updated_at").isoformat() if room.get("updated_at") else None,
    }


@app.get("/api/formulary/journal")
def formulary_journal_home(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    user_id = str(user["_id"])
    query = {"$or": [{"owner_user_id": user_id}, {"member_user_ids": user_id}]}
    rows = get_db().formulary_journal_rooms.find(query).sort("updated_at", -1).limit(100)
    return {"rooms": [_journal_room_public(row) for row in rows], "account": _formulary_account(user)}


@app.post("/api/formulary/journal/rooms", status_code=201)
def formulary_create_journal_room(
    body: FormularyJournalRoomRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "journal_room")
    user_id = str(user["_id"])
    db = get_db()
    review = db.formulary_reviews.find_one({"_id": body.review_id, "user_id": user_id})
    if not review:
        raise HTTPException(status_code=404, detail="Living Review not found")
    entry_ids = list(dict.fromkeys(body.entry_ids))
    entries = list(
        db.formulary_entries.find(
            {"_id": {"$in": entry_ids}, "review_id": body.review_id, "user_id": user_id}
        )
    )
    found_ids = {row["_id"] for row in entries}
    missing = [entry_id for entry_id in entry_ids if entry_id not in found_ids]
    if missing:
        raise HTTPException(status_code=422, detail=f"Selected evidence entries are not in this review: {', '.join(missing)}")
    if body.meeting_url and not re.match(r"^https?://", body.meeting_url, flags=re.I):
        raise HTTPException(status_code=422, detail="Meeting URL must begin with http:// or https://")

    raw_token = secrets.token_urlsafe(24)
    room_id = f"FJR-{uuid.uuid4().hex[:14].upper()}"
    now = _now()
    row = {
        "_id": room_id,
        "owner_user_id": user_id,
        "review_id": body.review_id,
        "entry_ids": entry_ids,
        "title": body.title.strip(),
        "scheduled_at": body.scheduled_at,
        "meeting_url": body.meeting_url,
        "agenda": [item.strip() for item in body.agenda if item.strip()],
        "appraisal_template": body.appraisal_template,
        "status": "scheduled",
        "locked": False,
        "member_user_ids": [],
        "join_token_hash": hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        "created_at": now,
        "updated_at": now,
    }
    db.formulary_journal_rooms.insert_one(row)
    return {
        "room": _journal_room_public(row),
        "join_path": f"/formulary/journal/join/{raw_token}",
        "notice": "Share the private join link only with intended participants. Joined members see structured evidence and discussion records, not the room owner's uploaded PDF bytes.",
    }


@app.post("/api/formulary/journal/rooms/{room_id}/invite")
def formulary_rotate_journal_invite(room_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    room = _journal_room_access(room_id, user)
    if room.get("owner_user_id") != str(user["_id"]) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only the room host can create a new invite")
    raw_token = secrets.token_urlsafe(24)
    get_db().formulary_journal_rooms.update_one(
        {"_id": room_id},
        {"$set": {"join_token_hash": hashlib.sha256(raw_token.encode("utf-8")).hexdigest(), "updated_at": _now()}},
    )
    return {"join_path": f"/formulary/journal/join/{raw_token}"}


@app.post("/api/formulary/journal/join")
def formulary_join_journal_room(
    body: FormularyJournalJoinRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    token_hash = hashlib.sha256(body.token.encode("utf-8")).hexdigest()
    db = get_db()
    room = db.formulary_journal_rooms.find_one({"join_token_hash": token_hash})
    if not room:
        raise HTTPException(status_code=404, detail="Journal Club invitation not found")
    if room.get("locked"):
        raise HTTPException(status_code=409, detail="This Journal Club room is locked")
    if room.get("status") == "closed":
        raise HTTPException(status_code=409, detail="This Journal Club room is closed")
    user_id = str(user["_id"])
    if user_id != room.get("owner_user_id"):
        db.formulary_journal_rooms.update_one(
            {"_id": room["_id"]},
            {"$addToSet": {"member_user_ids": user_id}, "$set": {"updated_at": _now()}},
        )
    return {"room_id": room["_id"], "status": room.get("status", "scheduled")}


@app.get("/api/formulary/journal/rooms/{room_id}")
def formulary_journal_room_detail(room_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    room = _journal_room_access(room_id, user)
    db = get_db()
    entries = _journal_room_entries(room)
    items = list(db.formulary_journal_items.find({"room_id": room_id}).sort("created_at", 1).limit(1000))
    factchecks = list(db.formulary_journal_factchecks.find({"room_id": room_id}).sort("created_at", -1).limit(200))
    return {
        "room": _journal_room_public(room),
        "participants": _journal_participants(room),
        "evidence": evidence_snapshot(entries),
        "appraisal_prompts": appraisal_template(room.get("appraisal_template")),
        "items": [
            {
                "id": item["_id"],
                "kind": item.get("kind"),
                "content": item.get("content"),
                "entry_id": item.get("entry_id"),
                "appraisal_section": item.get("appraisal_section"),
                "rating": item.get("rating"),
                "assigned_to": item.get("assigned_to"),
                "due_on": item.get("due_on"),
                "created_by": item.get("created_by"),
                "created_by_name": item.get("created_by_name"),
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
            }
            for item in items
        ],
        "factchecks": [
            {
                "id": row["_id"],
                "claim": row.get("claim"),
                "verdict": row.get("verdict"),
                "confidence": row.get("confidence"),
                "rationale": row.get("rationale"),
                "citations": row.get("citations", []),
                "contradictory_points": row.get("contradictory_points", []),
                "verification_steps": row.get("verification_steps", []),
                "method": row.get("method"),
                "requested_by_name": row.get("requested_by_name"),
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            }
            for row in factchecks
        ],
        "account": _formulary_account(user),
        "privacy_notice": "Room members can see structured evidence, metadata, discussion items and fact-check outputs. Uploaded PDF bytes and private source excerpts are not shared through the room.",
    }


@app.patch("/api/formulary/journal/rooms/{room_id}")
def formulary_update_journal_room(
    room_id: str,
    body: FormularyJournalRoomUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    room = _journal_room_access(room_id, user)
    if room.get("owner_user_id") != str(user["_id"]) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only the room host can update room settings")
    update = body.model_dump(exclude_none=True)
    if update.get("meeting_url") and not re.match(r"^https?://", str(update["meeting_url"]), flags=re.I):
        raise HTTPException(status_code=422, detail="Meeting URL must begin with http:// or https://")
    if "agenda" in update:
        update["agenda"] = [str(item).strip() for item in update["agenda"] if str(item).strip()]
    update["updated_at"] = _now()
    get_db().formulary_journal_rooms.update_one({"_id": room_id}, {"$set": update})
    updated = get_db().formulary_journal_rooms.find_one({"_id": room_id})
    return _journal_room_public(updated)


@app.post("/api/formulary/journal/rooms/{room_id}/items", status_code=201)
def formulary_add_journal_item(
    room_id: str,
    body: FormularyJournalItemRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    room = _journal_room_access(room_id, user)
    if room.get("status") == "closed":
        raise HTTPException(status_code=409, detail="This Journal Club room is closed")
    if body.entry_id and body.entry_id not in (room.get("entry_ids") or []):
        raise HTTPException(status_code=422, detail="The selected paper is not linked to this room")
    if body.kind == "appraisal" and not body.appraisal_section:
        raise HTTPException(status_code=422, detail="Appraisal items require an appraisal_section")
    item_id = f"FJI-{uuid.uuid4().hex[:14].upper()}"
    row = {
        "_id": item_id,
        "room_id": room_id,
        "kind": body.kind,
        "content": body.content.strip(),
        "entry_id": body.entry_id,
        "appraisal_section": body.appraisal_section,
        "rating": body.rating,
        "assigned_to": body.assigned_to,
        "due_on": body.due_on.isoformat() if body.due_on else None,
        "created_by": str(user["_id"]),
        "created_by_name": user.get("full_name"),
        "created_at": _now(),
    }
    get_db().formulary_journal_items.insert_one(row)
    get_db().formulary_journal_rooms.update_one({"_id": room_id}, {"$set": {"updated_at": _now()}})
    return {
        "id": item_id,
        "kind": row["kind"],
        "content": row["content"],
        "entry_id": row["entry_id"],
        "appraisal_section": row["appraisal_section"],
        "rating": row["rating"],
        "assigned_to": row["assigned_to"],
        "due_on": row["due_on"],
        "created_by": row["created_by"],
        "created_by_name": row["created_by_name"],
        "created_at": row["created_at"].isoformat(),
    }


@app.post("/api/formulary/journal/rooms/{room_id}/fact-check", status_code=201)
def formulary_journal_fact_check(
    room_id: str,
    body: FormularyJournalFactCheckRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "journal_factcheck")
    room = _journal_room_access(room_id, user)
    selected_ids = list(dict.fromkeys(body.entry_ids)) if body.entry_ids else list(room.get("entry_ids") or [])
    invalid = [entry_id for entry_id in selected_ids if entry_id not in (room.get("entry_ids") or [])]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Fact-check paper is not linked to this room: {', '.join(invalid)}")
    entries = [row for row in _journal_room_entries(room) if row["_id"] in selected_ids]
    result = fact_check_claim(body.claim.strip(), entries)
    row = {
        "_id": f"FJF-{uuid.uuid4().hex[:14].upper()}",
        "room_id": room_id,
        "claim": body.claim.strip(),
        **result,
        "entry_ids": selected_ids,
        "evidence_snapshot": evidence_snapshot(entries),
        "requested_by": str(user["_id"]),
        "requested_by_name": user.get("full_name"),
        "created_at": _now(),
    }
    get_db().formulary_journal_factchecks.insert_one(row)
    get_db().formulary_journal_rooms.update_one({"_id": room_id}, {"$set": {"updated_at": _now()}})
    return {
        "id": row["_id"],
        "claim": row["claim"],
        "verdict": row["verdict"],
        "confidence": row["confidence"],
        "rationale": row["rationale"],
        "citations": row["citations"],
        "contradictory_points": row["contradictory_points"],
        "verification_steps": row["verification_steps"],
        "method": row["method"],
        "requested_by_name": row["requested_by_name"],
        "created_at": row["created_at"].isoformat(),
    }




# -------------------------- Formulary Grant Project Studio -------------------

def _grant_project_owner(project_id: str, user: dict[str, Any]) -> dict[str, Any]:
    row = get_db().formulary_grant_projects.find_one({"_id": project_id, "user_id": str(user["_id"])})
    if not row:
        raise HTTPException(status_code=404, detail="Grant project not found")
    return row


def _grant_project_public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["_id"],
        "title": row.get("title"),
        "acronym": row.get("acronym"),
        "project_type": row.get("project_type"),
        "originator_name": row.get("originator_name"),
        "host_institution": row.get("host_institution"),
        "country": row.get("country"),
        "location": row.get("location"),
        "duration_months": row.get("duration_months"),
        "budget_amount": row.get("budget_amount"),
        "budget_currency": row.get("budget_currency"),
        "funder_name": row.get("funder_name"),
        "call_reference": row.get("call_reference"),
        "call_url": row.get("call_url"),
        "deadline": row.get("deadline").isoformat() if row.get("deadline") else None,
        "summary": row.get("summary"),
        "problem_statement": row.get("problem_statement"),
        "objectives": row.get("objectives", []),
        "confidentiality_level": row.get("confidentiality_level", "controlled"),
        "status": row.get("status", "concept"),
        "template": project_template(str(row.get("project_type") or "flagship_research")),
        "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updated_at": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def _grant_collection_rows(collection_name: str, project_id: str) -> list[dict[str, Any]]:
    db = get_db()
    collection = getattr(db, collection_name)
    if collection_name == "formulary_grant_workpackages":
        return list(collection.find({"project_id": project_id}).sort("sequence", 1).limit(100))
    if collection_name == "formulary_grant_milestones":
        return list(collection.find({"project_id": project_id}).sort("due_on", 1).limit(200))
    if collection_name == "formulary_grant_disclosures":
        return list(collection.find({"project_id": project_id}).sort("disclosed_at", -1).limit(500))
    return list(collection.find({"project_id": project_id}).sort("created_at", 1).limit(500))


def _grant_related_public(row: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in row.items():
        if key == "_id":
            output["id"] = str(value)
        elif isinstance(value, (datetime, date)):
            output[key] = value.isoformat()
        else:
            output[key] = value
    return output


def _grant_funder_profile_public(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {"funder_lens": "cross_funder"}
    return {
        key: value
        for key, value in row.items()
        if key not in {"_id", "user_id", "created_at", "updated_at"}
    }


def _grant_project_bundle(project: dict[str, Any]) -> dict[str, Any]:
    project_id = project["_id"]
    partners = _grant_collection_rows("formulary_grant_partners", project_id)
    work_packages = _grant_collection_rows("formulary_grant_workpackages", project_id)
    milestones = _grant_collection_rows("formulary_grant_milestones", project_id)
    ip_assets = _grant_collection_rows("formulary_grant_ip_assets", project_id)
    disclosures = _grant_collection_rows("formulary_grant_disclosures", project_id)
    funder_profile_row = get_db().formulary_grant_funder_profiles.find_one({"project_id": project_id})
    funder_profile = _grant_funder_profile_public(funder_profile_row)
    readiness = readiness_assessment(
        project,
        partners=partners,
        work_packages=work_packages,
        milestones=milestones,
        ip_assets=ip_assets,
        disclosures=disclosures,
    )
    return {
        "project": _grant_project_public(project),
        "partners": [_grant_related_public(row) for row in partners],
        "work_packages": [_grant_related_public(row) for row in normalize_percentages(work_packages, project.get("budget_amount"))],
        "milestones": [_grant_related_public(row) for row in milestones],
        "ip_assets": [_grant_related_public(row) for row in ip_assets],
        "disclosures": [_grant_related_public(row) for row in disclosures],
        "readiness": readiness,
        "funder_profile": funder_profile,
        "funder_readiness": funder_profile_assessment(
            project,
            funder_profile,
            partners=partners,
            work_packages=work_packages,
            milestones=milestones,
        ),
        "watermark": disclosure_watermark(project),
    }


@app.get("/api/formulary/grants")
def formulary_grant_projects(user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    user_id = str(user["_id"])
    db = get_db()
    rows = list(db.formulary_grant_projects.find({"user_id": user_id}).sort("updated_at", -1).limit(100))
    projects = []
    for row in rows:
        bundle = _grant_project_bundle(row)
        projects.append({
            **bundle["project"],
            "readiness": bundle["readiness"],
            "partner_count": len(bundle["partners"]),
            "work_package_count": len(bundle["work_packages"]),
            "background_ip_count": len(bundle["ip_assets"]),
            "disclosure_count": len(bundle["disclosures"]),
        })
    return {"projects": projects, "account": _formulary_account(user)}


@app.post("/api/formulary/grants/projects", status_code=201)
def formulary_create_grant_project(
    body: FormularyGrantProjectRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _formulary_enforce_limit(user, "grant_project")
    if body.call_url and not re.match(r"^https?://", body.call_url, flags=re.I):
        raise HTTPException(status_code=422, detail="Call URL must begin with http:// or https://")
    now = _now()
    project_id = f"FGP-{uuid.uuid4().hex[:14].upper()}"
    row = {
        "_id": project_id,
        "user_id": str(user["_id"]),
        **body.model_dump(),
        "objectives": [item.strip() for item in body.objectives if item.strip()],
        "status": "concept",
        "created_at": now,
        "updated_at": now,
    }
    get_db().formulary_grant_projects.insert_one(row)
    return _grant_project_bundle(row)


@app.get("/api/formulary/grants/projects/{project_id}")
def formulary_grant_project_detail(project_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    return _grant_project_bundle(_grant_project_owner(project_id, user))


@app.patch("/api/formulary/grants/projects/{project_id}")
def formulary_update_grant_project(
    project_id: str,
    body: FormularyGrantProjectUpdate,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    update = body.model_dump(exclude_none=True)
    if update.get("call_url") and not re.match(r"^https?://", str(update["call_url"]), flags=re.I):
        raise HTTPException(status_code=422, detail="Call URL must begin with http:// or https://")
    if "objectives" in update:
        update["objectives"] = [str(item).strip() for item in update["objectives"] if str(item).strip()]
    update["updated_at"] = _now()
    get_db().formulary_grant_projects.update_one({"_id": project_id, "user_id": str(user["_id"])}, {"$set": update})
    return _grant_project_bundle(_grant_project_owner(project_id, user))


@app.post("/api/formulary/grants/projects/{project_id}/partners", status_code=201)
def formulary_add_grant_partner(
    project_id: str,
    body: FormularyGrantPartnerRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    row = {
        "_id": f"FGPART-{uuid.uuid4().hex[:12].upper()}",
        "project_id": project_id,
        "user_id": str(user["_id"]),
        **body.model_dump(mode="json"),
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_grant_partners.insert_one(row)
    get_db().formulary_grant_projects.update_one({"_id": project_id}, {"$set": {"updated_at": _now()}})
    return _grant_related_public(row)


@app.post("/api/formulary/grants/projects/{project_id}/work-packages", status_code=201)
def formulary_add_grant_work_package(
    project_id: str,
    body: FormularyGrantWorkPackageRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    row = {
        "_id": f"FGWP-{uuid.uuid4().hex[:12].upper()}",
        "project_id": project_id,
        "user_id": str(user["_id"]),
        **body.model_dump(),
        "outputs": [item.strip() for item in body.outputs if item.strip()],
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_grant_workpackages.insert_one(row)
    get_db().formulary_grant_projects.update_one({"_id": project_id}, {"$set": {"updated_at": _now()}})
    return _grant_related_public(row)


@app.post("/api/formulary/grants/projects/{project_id}/milestones", status_code=201)
def formulary_add_grant_milestone(
    project_id: str,
    body: FormularyGrantMilestoneRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    row = {
        "_id": f"FGM-{uuid.uuid4().hex[:12].upper()}",
        "project_id": project_id,
        "user_id": str(user["_id"]),
        **body.model_dump(),
        "due_on": body.due_on.isoformat() if body.due_on else None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    get_db().formulary_grant_milestones.insert_one(row)
    get_db().formulary_grant_projects.update_one({"_id": project_id}, {"$set": {"updated_at": _now()}})
    return _grant_related_public(row)


@app.post("/api/formulary/grants/projects/{project_id}/ip-assets", status_code=201)
def formulary_add_grant_ip_asset(
    project_id: str,
    body: FormularyGrantIPAssetRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    row = {
        "_id": f"FGIP-{uuid.uuid4().hex[:12].upper()}",
        "project_id": project_id,
        "user_id": str(user["_id"]),
        **body.model_dump(),
        "created_at": _now(),
    }
    get_db().formulary_grant_ip_assets.insert_one(row)
    get_db().formulary_grant_projects.update_one({"_id": project_id}, {"$set": {"updated_at": _now()}})
    return _grant_related_public(row)


@app.post("/api/formulary/grants/projects/{project_id}/disclosures", status_code=201)
def formulary_add_grant_disclosure(
    project_id: str,
    body: FormularyGrantDisclosureRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    project = _grant_project_owner(project_id, user)
    row = {
        "_id": f"FGD-{uuid.uuid4().hex[:12].upper()}",
        "project_id": project_id,
        "user_id": str(user["_id"]),
        **body.model_dump(),
        "watermark": disclosure_watermark(project, body.version),
        "created_at": _now(),
    }
    get_db().formulary_grant_disclosures.insert_one(row)
    get_db().formulary_grant_projects.update_one({"_id": project_id}, {"$set": {"updated_at": _now()}})
    return _grant_related_public(row)


@app.get("/api/formulary/grants/projects/{project_id}/readiness")
def formulary_grant_project_readiness(project_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    return _grant_project_bundle(_grant_project_owner(project_id, user))["readiness"]


@app.get("/api/formulary/grants/projects/{project_id}/disclosure-watermark")
def formulary_grant_disclosure_watermark(
    project_id: str,
    version: str | None = None,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    project = _grant_project_owner(project_id, user)
    return {"watermark": disclosure_watermark(project, version)}



@app.get("/api/formulary/grants/projects/{project_id}/funder-profile")
def formulary_grant_funder_profile(project_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    project = _grant_project_owner(project_id, user)
    bundle = _grant_project_bundle(project)
    return {
        "project_id": project_id,
        "profile": bundle["funder_profile"],
        "readiness": bundle["funder_readiness"],
        "lens": funder_lens(str(bundle["funder_profile"].get("funder_lens") or "cross_funder")),
    }


@app.put("/api/formulary/grants/projects/{project_id}/funder-profile")
def formulary_update_grant_funder_profile(
    project_id: str,
    body: FormularyGrantFunderProfileRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    project = _grant_project_owner(project_id, user)
    payload = body.model_dump()
    for key in (
        "impact_metrics", "capacity_outputs", "data_management_commitments",
        "sdg_alignment", "keywords",
    ):
        payload[key] = [str(item).strip() for item in payload.get(key, []) if str(item).strip()]
    now = _now()
    get_db().formulary_grant_funder_profiles.update_one(
        {"project_id": project_id},
        {
            "$set": {
                "project_id": project_id,
                "user_id": str(user["_id"]),
                **payload,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    get_db().formulary_grant_projects.update_one(
        {"_id": project_id, "user_id": str(user["_id"])},
        {"$set": {"updated_at": now}},
    )
    return _grant_project_bundle(project)


@app.get("/api/formulary/grants/projects/{project_id}/funder-rooms")
def formulary_grant_funder_rooms(project_id: str, user: dict[str, Any] = Depends(current_user)):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    rows = get_db().formulary_grant_funder_rooms.find(
        {"project_id": project_id, "user_id": str(user["_id"])}
    ).sort("created_at", -1).limit(100)
    return {
        "rooms": [
            {
                "id": row["_id"],
                "recipient_label": row.get("recipient_label"),
                "expires_at": row.get("expires_at").isoformat() if row.get("expires_at") else None,
                "revoked": bool(row.get("revoked", False)),
                "access_count": int(row.get("access_count") or 0),
                "last_accessed_at": row.get("last_accessed_at").isoformat() if row.get("last_accessed_at") else None,
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                "readiness_score": (row.get("snapshot") or {}).get("readiness", {}).get("score"),
            }
            for row in rows
        ]
    }


@app.post("/api/formulary/grants/projects/{project_id}/funder-rooms", status_code=201)
def formulary_create_grant_funder_room(
    project_id: str,
    body: FormularyGrantFunderRoomRequest,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    project = _grant_project_owner(project_id, user)
    db = get_db()
    profile = _grant_funder_profile_public(
        db.formulary_grant_funder_profiles.find_one({"project_id": project_id})
    )
    partners = _grant_collection_rows("formulary_grant_partners", project_id)
    work_packages = _grant_collection_rows("formulary_grant_workpackages", project_id)
    milestones = _grant_collection_rows("formulary_grant_milestones", project_id)
    snapshot = safe_funder_snapshot(
        project,
        profile,
        partners=partners,
        work_packages=work_packages,
        milestones=milestones,
        include_budget=body.include_budget,
        include_partners=body.include_partners,
        include_milestones=body.include_milestones,
    )

    days = min(body.expires_in_days, settings.FORMULARY_GRANT_FUNDER_ROOM_MAX_DAYS)
    raw_token = secrets.token_urlsafe(32)
    now = _now()
    room_id = f"FGROOM-{uuid.uuid4().hex[:12].upper()}"
    expires_at = now + timedelta(days=days)
    row = {
        "_id": room_id,
        "project_id": project_id,
        "user_id": str(user["_id"]),
        "recipient_label": body.recipient_label,
        "note": body.note,
        "token_hash": hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        "snapshot": snapshot,
        "expires_at": expires_at,
        "revoked": False,
        "access_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    db.formulary_grant_funder_rooms.insert_one(row)

    db.formulary_grant_disclosures.insert_one(
        {
            "_id": f"FGD-{uuid.uuid4().hex[:12].upper()}",
            "project_id": project_id,
            "user_id": str(user["_id"]),
            "recipient_name": body.recipient_label or "Controlled funder-room recipient",
            "recipient_organization": None,
            "disclosed_at": now,
            "material": "Funder Due-Diligence Room frozen snapshot",
            "version": room_id,
            "purpose": body.note or "International funder / consortium due diligence",
            "confidentiality_basis": "Expiring tokenized read-only access. This access control does not itself create an NDA or other legal confidentiality obligation.",
            "notes": "Background-IP records, disclosure history, private contact emails and unpublished source files are excluded from the snapshot.",
            "watermark": disclosure_watermark(project, room_id),
            "created_at": now,
        }
    )
    db.formulary_grant_projects.update_one({"_id": project_id}, {"$set": {"updated_at": now}})

    return {
        "id": room_id,
        "share_path": f"/funder-room/{raw_token}",
        "expires_at": expires_at.isoformat(),
        "readiness": snapshot["readiness"],
        "notice": "This is a frozen, read-only, expiring snapshot. The raw token is returned only now; create a new room if the link is lost or should be rotated.",
    }


@app.post("/api/formulary/grants/projects/{project_id}/funder-rooms/{room_id}/revoke")
def formulary_revoke_grant_funder_room(
    project_id: str,
    room_id: str,
    user: dict[str, Any] = Depends(current_user),
):
    _formulary_require_user(user)
    _grant_project_owner(project_id, user)
    result = get_db().formulary_grant_funder_rooms.update_one(
        {"_id": room_id, "project_id": project_id, "user_id": str(user["_id"])},
        {"$set": {"revoked": True, "updated_at": _now()}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Funder room not found")
    return {"id": room_id, "revoked": True}


@app.get("/api/formulary/funder-room/{token}")
def formulary_public_funder_room(token: str):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db = get_db()
    row = db.formulary_grant_funder_rooms.find_one({"token_hash": token_hash})
    if not row:
        raise HTTPException(status_code=404, detail="Funder room not found")
    if row.get("revoked"):
        raise HTTPException(status_code=410, detail="This funder room has been revoked")
    expires_at = row.get("expires_at")
    if not expires_at or expires_at < _now():
        raise HTTPException(status_code=410, detail="This funder room has expired")
    db.formulary_grant_funder_rooms.update_one(
        {"_id": row["_id"]},
        {
            "$inc": {"access_count": 1},
            "$set": {"last_accessed_at": _now(), "updated_at": _now()},
        },
    )
    return {
        "room": {
            "id": row["_id"],
            "recipient_label": row.get("recipient_label"),
            "note": row.get("note"),
            "expires_at": expires_at.isoformat(),
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
        },
        "snapshot": row.get("snapshot") or {},
        "access_notice": "This is a frozen project snapshot shared through an expiring read-only link. It is not a funding decision, endorsement, NDA or legal IP determination.",
    }


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
                "Unlimited living literature reviews and evidence entries",
                "DOI/PDF pharmaceutical extraction and citation watch",
                "PK/PD simulator with persistent research runs",
                "Residency & research portfolio with attestations",
                "Source-grounded regulatory & grant copilot",
                "Journal Club Live Rooms with evidence-grounded fact checks",
                "International Grant Project Studio with consortium, IP and disclosure tracking",
                "Funder Due-Diligence Rooms with frozen expiring project snapshots",
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
        entitlements.update({"formulary_pro", "unlimited_literature_reviews", "citation_watch", "structured_pdf_extraction", "pkpd_simulator", "unlimited_portfolio", "public_portfolio", "regulatory_grant_copilot", "journal_club_live_rooms", "international_grant_project_studio", "funder_due_diligence_rooms"})
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
