from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from pymongo.errors import DuplicateKeyError

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.mongo import get_db

app = FastAPI(title="Mabrig HealthOS Research & Discovery Studio", version="1.0.0")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SERVICE_CATALOG: list[dict[str, Any]] = [
    {
        "id": "network-pharmacology",
        "category": "Bioinformatics Consulting",
        "name": "Network Pharmacology Analysis",
        "description": "Compound-target curation, PPI/network construction, enrichment-ready tables and Cytoscape-ready outputs.",
        "price_kobo": 12_000_000,
        "price_label": "From ₦120,000",
        "deliverables": ["curated compound-target table", "network files", "analysis report", "publication-ready figures"],
    },
    {
        "id": "admet-screening",
        "category": "Bioinformatics Consulting",
        "name": "ADMET & Drug-Likeness Screening",
        "description": "Structured SwissADME-style screening workflow with transparent inclusion/exclusion criteria and exportable tables.",
        "price_kobo": 7_500_000,
        "price_label": "From ₦75,000",
        "deliverables": ["ADMET matrix", "drug-likeness summary", "compound prioritization", "methods-ready notes"],
    },
    {
        "id": "molecular-docking",
        "category": "Bioinformatics Consulting",
        "name": "Molecular Docking Study",
        "description": "Research design, docking workflow support, reproducibility checklist, interaction tables and high-resolution structural figures.",
        "price_kobo": 15_000_000,
        "price_label": "From ₦150,000",
        "deliverables": ["docking protocol", "ranked interaction table", "reproducibility record", "3D figure pack"],
    },
    {
        "id": "insilico-thesis-package",
        "category": "Bioinformatics Consulting",
        "name": "In Silico Thesis Package",
        "description": "Combined network pharmacology, ADMET, docking, visualization and interpretation support for postgraduate research.",
        "price_kobo": 28_000_000,
        "price_label": "From ₦280,000",
        "deliverables": ["network pharmacology", "ADMET", "docking", "figure pack", "defense-ready methods audit"],
    },
    {
        "id": "publication-figures",
        "category": "Research Production",
        "name": "Publication-Ready Scientific Figures",
        "description": "High-resolution network, pathway and molecular-interaction figures prepared from researcher-supplied or project-generated data.",
        "price_kobo": 6_000_000,
        "price_label": "From ₦60,000",
        "deliverables": ["300-600 DPI figures", "editable source files", "journal-size variants", "figure legends"],
    },
    {
        "id": "grant-herbal-research",
        "category": "Grant & Proposal Consulting",
        "name": "Herbal Research Grant Architecture",
        "description": "Translate an ethnobotanical research idea into a structured, funder-ready computational and experimental proposal architecture.",
        "price_kobo": 20_000_000,
        "price_label": "From ₦200,000",
        "deliverables": ["problem framing", "aims and hypotheses", "computational pipeline", "work packages", "budget logic", "risk and ethics checklist"],
    },
    {
        "id": "q1-insilico-course",
        "category": "Training & Digital Products",
        "name": "Publishing with In Silico Tools Cohort",
        "description": "Practical training on reproducible use of AutoDock Vina/PyRx, SwissADME, Cytoscape and publication workflow design.",
        "price_kobo": 5_000_000,
        "price_label": "₦50,000",
        "deliverables": ["workbook", "video lessons", "templates", "live cohort sessions", "reproducibility checklist"],
    },
]

SYNERGY_FRAMEWORK = {
    "name": "Polyherbal Synergy Index (PSI-β)",
    "status": "experimental research framework",
    "purpose": "Compare multi-component computational interaction patterns without presenting in-silico scores as proof of clinical efficacy.",
    "stages": [
        "standardize plant and compound identities",
        "screen pharmacokinetic and toxicity flags",
        "map compounds to targets and disease pathways",
        "run reproducible docking or binding analyses",
        "construct polyherbal interaction networks",
        "quantify complementarity, target coverage and interaction redundancy",
        "pre-register wet-lab validation criteria before efficacy claims",
    ],
    "guardrail": "PSI-β is hypothesis-generating. It does not establish therapeutic synergy, safety, patentability, NAFDAC approval or clinical efficacy.",
}


class StudioAction(BaseModel):
    action: str
    service_id: str | None = None
    project_title: str | None = Field(default=None, max_length=240)
    institution: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=5000)
    callback_url: str | None = None
    plants: list[str] = Field(default_factory=list, max_length=10)
    indication: str | None = Field(default=None, max_length=240)
    targets: list[str] = Field(default_factory=list, max_length=50)
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=128)


def now() -> datetime:
    return datetime.now(timezone.utc)


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


def get_service(service_id: str | None) -> dict[str, Any]:
    for service in SERVICE_CATALOG:
        if service["id"] == service_id:
            return service
    raise HTTPException(status_code=404, detail="Research service not found")


def initialize_paystack(email: str, amount_kobo: int, reference: str, callback_url: str | None, metadata: dict[str, Any]) -> dict[str, Any]:
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Paystack is not configured yet. Add PAYSTACK_SECRET_KEY in Vercel Environment Variables.")
    payload: dict[str, Any] = {
        "email": email,
        "amount": amount_kobo,
        "currency": "NGN",
        "reference": reference,
        "metadata": metadata,
    }
    if callback_url:
        payload["callback_url"] = callback_url
    try:
        response = httpx.post(
            f"{settings.PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"},
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Payment gateway request failed: {exc}")
    if not data.get("status"):
        raise HTTPException(status_code=502, detail=data.get("message") or "Payment initialization failed")
    return data["data"]


def register_researcher(body: StudioAction) -> dict[str, Any]:
    if not body.email or not body.full_name or not body.password:
        raise HTTPException(status_code=422, detail="email, full_name and password are required")
    if len(body.password) < 8 or not any(c.isalpha() for c in body.password) or not any(c.isdigit() for c in body.password):
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters and contain a letter and a number")
    email = str(body.email).lower().strip()
    user = {
        "email": email,
        "full_name": body.full_name.strip(),
        "password_hash": pwd_context.hash(body.password),
        "role": "researcher",
        "is_active": True,
        "token_version": 0,
        "created_at": now(),
    }
    try:
        result = get_db().users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Email already registered")
    return {"id": str(result.inserted_id), "email": email, "full_name": user["full_name"], "role": "researcher", "is_active": True, "created_at": user["created_at"].isoformat()}


@app.get("/api/research_studio")
def catalog():
    return {
        "studio": "Mabrig HealthOS Research & Discovery Studio",
        "services": SERVICE_CATALOG,
        "synergy_framework": SYNERGY_FRAMEWORK,
        "integrity_notice": "Services support legitimate research, analysis and training. Researchers remain responsible for methods, interpretation, authorship, ethics approvals and verification of all results.",
    }


@app.post("/api/research_studio")
def studio_action(body: StudioAction, request: Request):
    if body.action == "register_researcher":
        return register_researcher(body)

    user = user_from_request(request)
    user_id = str(user["_id"])
    db = get_db()

    if body.action == "create_order":
        service = get_service(body.service_id)
        order_id = f"RS-{now().strftime('%Y%m%d%H%M%S')}-{str(user['_id'])[-6:]}"
        order = {
            "_id": order_id,
            "user_id": user_id,
            "service_id": service["id"],
            "service_name": service["name"],
            "project_title": body.project_title,
            "institution": body.institution,
            "notes": body.notes,
            "amount_kobo": service["price_kobo"],
            "currency": "NGN",
            "status": "awaiting_payment",
            "payment_status": "pending",
            "created_at": now(),
            "updated_at": now(),
        }
        db.research_service_orders.insert_one(order)
        paystack = initialize_paystack(
            user["email"],
            service["price_kobo"],
            order_id,
            body.callback_url,
            {"order_id": order_id, "service_id": service["id"], "user_id": user_id, "product": "research_studio"},
        )
        db.research_service_orders.update_one({"_id": order_id}, {"$set": {"paystack_access_code": paystack.get("access_code"), "updated_at": now()}})
        return {
            "order_id": order_id,
            "service": service["name"],
            "amount_kobo": service["price_kobo"],
            "authorization_url": paystack.get("authorization_url"),
            "access_code": paystack.get("access_code"),
            "reference": paystack.get("reference", order_id),
        }

    if body.action == "create_synergy_project":
        plants = [p.strip() for p in body.plants if p.strip()]
        if len(plants) < 2:
            raise HTTPException(status_code=422, detail="At least two plants are required for a polyherbal project")
        project_id = f"PSI-{now().strftime('%Y%m%d%H%M%S')}-{str(user['_id'])[-6:]}"
        project = {
            "_id": project_id,
            "user_id": user_id,
            "title": body.project_title or "Polyherbal Synergy Project",
            "plants": plants,
            "indication": body.indication,
            "targets": body.targets,
            "notes": body.notes,
            "framework": "PSI-beta",
            "status": "design",
            "validation_required": True,
            "created_at": now(),
            "updated_at": now(),
        }
        db.polyherbal_synergy_projects.insert_one(project)
        return {
            "project_id": project_id,
            "status": "design",
            "next_steps": SYNERGY_FRAMEWORK["stages"],
            "guardrail": SYNERGY_FRAMEWORK["guardrail"],
        }

    if body.action == "my_orders":
        orders = db.research_service_orders.find({"user_id": user_id}).sort("created_at", -1).limit(50)
        return {
            "orders": [
                {
                    "order_id": row["_id"],
                    "service_name": row.get("service_name"),
                    "project_title": row.get("project_title"),
                    "amount_kobo": row.get("amount_kobo"),
                    "status": row.get("status"),
                    "payment_status": row.get("payment_status"),
                    "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
                }
                for row in orders
            ]
        }

    raise HTTPException(status_code=400, detail="Unsupported research studio action")
