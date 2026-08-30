import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.clinical import run_clinical_workflow
from app.clinical.crypto import decrypt_json, encrypt_json
from app.clinical.fhir import build_fhir_bundle
from app.clinical.multimodal import analyze_medical_image
from app.clinical.voice import transcribe_audio
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.clinical_case import ClinicalAuditLog, ClinicalCase, ClinicalConsultation, ProviderProfile
from app.models.user import User, UserRole
from app.routers.payments import _paystack_get, _paystack_post
from app.schemas.clinical import ClinicalTriageRequest, ClinicalTriageResponse, ConsultationCheckoutRequest, ProviderProfileCreate, SMSRequest

router = APIRouter()


def _audit(db: Session, action: str, actor_user_id: int | None, case_id: str | None = None, **metadata: Any) -> None:
    db.add(ClinicalAuditLog(case_id=case_id, actor_user_id=actor_user_id, action=action, event_metadata=metadata))


def _verified_provider(db: Session, user_id: int) -> ProviderProfile | None:
    return db.query(ProviderProfile).filter(ProviderProfile.user_id == user_id, ProviderProfile.verified.is_(True)).first()


def _can_read_case(db: Session, case: ClinicalCase, user: User) -> bool:
    if user.role == UserRole.admin or case.patient_id == user.id:
        return True
    return bool(case.assigned_doctor_id == user.id and _verified_provider(db, user.id))


def _verified_provider_matches(db: Session, state_name: str | None, lga: str | None, limit: int = 5) -> list[dict[str, Any]]:
    q = db.query(ProviderProfile).filter(ProviderProfile.verified.is_(True), ProviderProfile.available_online.is_(True))
    if state_name:
        q = q.filter(ProviderProfile.state == state_name)
    if lga:
        q = q.filter(ProviderProfile.lga == lga)
    rows = q.limit(limit).all()
    return [
        {
            "provider_user_id": p.user_id,
            "provider_type": p.provider_type,
            "specialties": p.specialties,
            "state": p.state,
            "lga": p.lga,
            "available_online": p.available_online,
            "consultation_fee_kobo": p.consultation_fee_kobo,
            "source": "Mabrig HealthOS verified provider registry",
            "accreditation_verified": True,
        }
        for p in rows
    ]


@router.post("/triage", response_model=ClinicalTriageResponse, status_code=status.HTTP_201_CREATED)
def triage(body: ClinicalTriageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=workflow.get("block_reason") or "Non-medical request blocked")

    case = ClinicalCase(
        patient_id=current_user.id,
        urgency=workflow.get("urgency", "routine"),
        status="emergency_referral" if workflow.get("emergency") else "triaged",
        state=body.state,
        lga=body.lga,
        encrypted_payload="pending",
        encryption_key_version=settings.PHI_KEY_VERSION,
    )
    db.add(case)
    db.flush()

    fhir_bundle = build_fhir_bundle(case.id, current_user.id, workflow.get("structured_intake") or {}, case.urgency)
    payload = {"workflow": workflow, "fhir_bundle": fhir_bundle}
    case.encrypted_payload = encrypt_json(payload)
    _audit(db, "clinical_case.created", current_user.id, case.id, urgency=case.urgency)
    db.commit()

    verified = _verified_provider_matches(db, body.state, body.lga)
    referrals = verified + list(workflow.get("referrals") or [])
    return ClinicalTriageResponse(
        case_id=case.id,
        urgency=case.urgency,
        emergency=bool(workflow.get("emergency")),
        red_flags=workflow.get("red_flags", []),
        structured_intake=workflow.get("structured_intake") or {},
        differential_for_clinician_review=workflow.get("differential") or [],
        evidence=workflow.get("evidence") or [],
        referrals=referrals,
        patient_notice=workflow.get("patient_notice") or "Licensed clinician review required.",
    )


@router.get("/cases/{case_id}")
def get_case(case_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = db.get(ClinicalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Clinical case not found")
    if not _can_read_case(db, case, current_user):
        raise HTTPException(status_code=403, detail="Clinical record access denied")
    payload = decrypt_json(case.encrypted_payload)
    provider_view = bool(current_user.role == UserRole.admin or (case.assigned_doctor_id == current_user.id and _verified_provider(db, current_user.id)))
    workflow = payload.get("workflow", {})
    result = {
        "id": case.id,
        "urgency": case.urgency,
        "status": case.status,
        "state": case.state,
        "lga": case.lga,
        "assigned_doctor_id": case.assigned_doctor_id,
        "structured_intake": workflow.get("structured_intake", {}),
        "patient_notice": workflow.get("patient_notice"),
        "referrals": workflow.get("referrals", []),
        "created_at": case.created_at,
    }
    if provider_view:
        result.update({"differential": workflow.get("differential", []), "evidence": workflow.get("evidence", []), "soap_note": workflow.get("soap_note", {}), "fhir_bundle": payload.get("fhir_bundle")})
    _audit(db, "clinical_case.read", current_user.id, case.id, provider_view=provider_view)
    db.commit()
    return result


@router.post("/providers/profile", status_code=status.HTTP_201_CREATED)
def create_or_update_provider_profile(body: ProviderProfileCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(ProviderProfile).filter(ProviderProfile.user_id == current_user.id).first()
    if not profile:
        profile = ProviderProfile(user_id=current_user.id, license_number=body.license_number)
        db.add(profile)
    profile.license_number = body.license_number
    profile.licensing_body = body.licensing_body
    profile.specialties = body.specialties
    profile.state = body.state
    profile.lga = body.lga
    profile.available_online = body.available_online
    profile.consultation_fee_kobo = body.consultation_fee_kobo
    profile.paystack_subaccount_code = body.paystack_subaccount_code
    # Any profile edit requires re-verification.
    profile.verified = False
    profile.verified_at = None
    db.commit()
    db.refresh(profile)
    return {"user_id": profile.user_id, "verification_status": "pending", "licensing_body": profile.licensing_body}


@router.post("/providers/{provider_user_id}/verify")
def verify_provider(provider_user_id: int, _: User = Depends(require_role(UserRole.admin)), db: Session = Depends(get_db)):
    profile = db.query(ProviderProfile).filter(ProviderProfile.user_id == provider_user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    profile.verified = True
    profile.verified_at = datetime.now(timezone.utc)
    db.commit()
    return {"provider_user_id": provider_user_id, "verified": True, "note": "Admin attestation recorded. Production operations must independently verify the licence with the relevant regulator."}


@router.get("/providers/nearby")
def nearby_providers(state_name: str | None = None, lga: str | None = None, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _verified_provider_matches(db, state_name, lga, limit=20)


@router.post("/cases/{case_id}/assign/{provider_user_id}")
def assign_provider(case_id: str, provider_user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = db.get(ClinicalCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Clinical case not found")
    if case.patient_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only the patient or an administrator can assign a clinician")
    if not _verified_provider(db, provider_user_id):
        raise HTTPException(status_code=409, detail="Provider is not verified")
    case.assigned_doctor_id = provider_user_id
    case.status = "awaiting_clinician"
    _audit(db, "clinical_case.provider_assigned", current_user.id, case.id, provider_user_id=provider_user_id)
    db.commit()
    return {"case_id": case.id, "assigned_doctor_id": provider_user_id, "status": case.status}


@router.get("/provider/cases")
def provider_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _verified_provider(db, current_user.id):
        raise HTTPException(status_code=403, detail="Verified clinician account required")
    rows = db.query(ClinicalCase).filter(ClinicalCase.assigned_doctor_id == current_user.id).order_by(ClinicalCase.created_at.desc()).limit(100).all()
    return [{"id": c.id, "urgency": c.urgency, "status": c.status, "state": c.state, "lga": c.lga, "created_at": c.created_at} for c in rows]


@router.post("/media/analyze")
async def analyze_media(file: UploadFile = File(...), context: str | None = Form(default=None), _: User = Depends(get_current_user)):
    data = await file.read()
    return analyze_medical_image(data, file.content_type or "application/octet-stream", context)


@router.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...), language_hint: str | None = Form(default=None), _: User = Depends(get_current_user)):
    data = await file.read()
    return transcribe_audio(file.filename or "audio.webm", data, file.content_type or "application/octet-stream", language_hint)


@router.get("/plans")
def plans():
    return {
        "currency": "NGN",
        "b2c": {
            "ai_triage": {"price_kobo": 0, "label": "Free AI triage"},
            "family_pass": {"price_kobo": settings.FAMILY_PASS_MONTHLY_KOBO, "billing": "monthly", "paystack_plan_code": settings.FAMILY_PASS_PAYSTACK_PLAN_CODE or None},
            "doctor_consultation": {"pricing": "provider-set", "platform_commission_percent": settings.CONSULT_PLATFORM_FEE_PERCENT},
        },
        "b2b": {
            "doctor_workspace": {"price_kobo": settings.DOCTOR_WORKSPACE_MONTHLY_KOBO, "billing": "monthly", "paystack_plan_code": settings.DOCTOR_WORKSPACE_PAYSTACK_PLAN_CODE or None},
            "corporate_wellness": {"pricing": "custom quote"},
        },
        "enterprise": {"hmo_api": {"pricing": "contract / usage-based"}, "pharmacy_referrals": {"pricing": "verified fulfillment commission"}},
    }


@router.post("/consultations/checkout", status_code=status.HTTP_201_CREATED)
def consultation_checkout(body: ConsultationCheckoutRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    case = db.get(ClinicalCase, body.case_id)
    if not case or case.patient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient case not found")
    profile = _verified_provider(db, body.provider_user_id)
    if not profile:
        raise HTTPException(status_code=409, detail="Provider is not verified")
    if profile.consultation_fee_kobo <= 0:
        raise HTTPException(status_code=409, detail="Provider has not configured a consultation fee")

    fee = profile.consultation_fee_kobo
    platform_fee = round(fee * settings.CONSULT_PLATFORM_FEE_PERCENT / 100)
    consultation = ClinicalConsultation(case_id=case.id, patient_id=current_user.id, provider_id=body.provider_user_id, amount_kobo=fee, platform_fee_kobo=platform_fee, provider_net_kobo=fee - platform_fee)
    db.add(consultation)
    db.flush()
    payment = _paystack_post(
        "/transaction/initialize",
        {
            "email": current_user.email,
            "amount": fee,
            "currency": "NGN",
            "callback_url": body.callback_url or settings.FRONTEND_URL,
            "metadata": {
                "product": "mabrig_healthos_consultation",
                "consultation_id": consultation.id,
                "case_id": case.id,
                "patient_user_id": current_user.id,
                "provider_user_id": body.provider_user_id,
                "platform_fee_kobo": platform_fee,
                "provider_net_kobo": fee - platform_fee,
            },
        },
    )
    if not payment.get("status"):
        db.rollback()
        raise HTTPException(status_code=502, detail="Payment initialization failed")
    inner = payment["data"]
    consultation.payment_reference = inner["reference"]
    case.assigned_doctor_id = body.provider_user_id
    _audit(db, "consultation.checkout_created", current_user.id, case.id, consultation_id=consultation.id)
    db.commit()
    return {"consultation_id": consultation.id, "authorization_url": inner["authorization_url"], "reference": inner["reference"], "amount_kobo": fee, "platform_fee_kobo": platform_fee}


@router.get("/consultations/verify/{reference}")
def verify_consultation(reference: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consultation = db.query(ClinicalConsultation).filter(ClinicalConsultation.payment_reference == reference).first()
    if not consultation or (consultation.patient_id != current_user.id and consultation.provider_id != current_user.id and current_user.role != UserRole.admin):
        raise HTTPException(status_code=404, detail="Consultation not found")
    result = _paystack_get(f"/transaction/verify/{reference}")
    data = result.get("data") or {}
    paid = data.get("status") == "success" and int(data.get("amount") or 0) == consultation.amount_kobo
    consultation.payment_status = "paid" if paid else str(data.get("status") or "pending")
    if paid:
        consultation.consultation_status = "ready"
        case = db.get(ClinicalCase, consultation.case_id)
        if case:
            case.status = "clinician_assigned"
    db.commit()
    return {"reference": reference, "paid": paid, "status": consultation.payment_status, "consultation_status": consultation.consultation_status}


@router.post("/webhooks/paystack", include_in_schema=False)
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw, hashlib.sha512).hexdigest() if settings.PAYSTACK_SECRET_KEY else ""
    if not expected or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = json.loads(raw.decode("utf-8"))
    if event.get("event") == "charge.success":
        data = event.get("data") or {}
        reference = data.get("reference")
        consultation = db.query(ClinicalConsultation).filter(ClinicalConsultation.payment_reference == reference).first()
        if consultation and int(data.get("amount") or 0) == consultation.amount_kobo:
            consultation.payment_status = "paid"
            consultation.consultation_status = "ready"
            case = db.get(ClinicalCase, consultation.case_id)
            if case:
                case.status = "clinician_assigned"
            db.commit()
    return {"received": True}


@router.post("/channels/sms/send")
def send_sms(body: SMSRequest, _: User = Depends(get_current_user)):
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


@router.post("/channels/ussd")
async def ussd(request: Request):
    form = await request.form()
    text = str(form.get("text") or "")
    if not text:
        return "CON Mabrig HealthOS\n1. Start symptom triage\n2. Emergency guidance"
    if text == "2":
        return "END If you have severe bleeding, chest pain, breathing difficulty, loss of consciousness, or another emergency, seek emergency care immediately."
    return "END For privacy and safety, continue the full clinical intake by secure web/app or request an SMS callback."
