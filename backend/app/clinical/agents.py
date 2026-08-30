import json
from typing import Any, TypedDict

from app.core.config import settings

from .guardrails import asks_for_self_medication, evaluate_input, patient_safety_notice
from .rag import retrieve_protocols
from .referrals import search_nearby_facilities


class ClinicalState(TypedDict, total=False):
    message: str
    duration: str | None
    severity: int | None
    medical_history: list[str]
    medications: list[str]
    allergies: list[str]
    state: str | None
    lga: str | None
    blocked: bool
    block_reason: str | None
    emergency: bool
    red_flags: list[str]
    urgency: str
    structured_intake: dict[str, Any]
    evidence: list[dict[str, Any]]
    differential: list[dict[str, Any]]
    referrals: list[dict[str, Any]]
    soap_note: dict[str, Any]
    patient_notice: str
    self_medication_request: bool


def _gemini_json(system: str, prompt: str) -> dict[str, Any] | list[Any] | None:
    if not settings.effective_gemini_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.effective_gemini_key)
        model = genai.GenerativeModel(model_name=settings.CLINICAL_LLM_MODEL, system_instruction=system)
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return None


def safety_node(state: ClinicalState) -> ClinicalState:
    decision = evaluate_input(state["message"])
    return {
        "blocked": decision.blocked,
        "block_reason": decision.reason,
        "emergency": decision.emergency,
        "red_flags": list(decision.matched_red_flags),
        "urgency": "emergency" if decision.emergency else "routine",
        "patient_notice": patient_safety_notice(decision.emergency),
        "self_medication_request": asks_for_self_medication(state["message"]),
    }


def triage_node(state: ClinicalState) -> ClinicalState:
    fallback = {
        "symptoms": [{"name": state["message"], "duration": state.get("duration"), "severity": state.get("severity")}],
        "medical_history": state.get("medical_history", []),
        "current_medications": state.get("medications", []),
        "allergies": state.get("allergies", []),
        "severity_score": state.get("severity"),
        "next_questions": [],
    }
    system = (
        "You are the Triage Agent for Mabrig HealthOS. Extract facts only from the patient message. "
        "Do not diagnose, prescribe, invent vitals, or downgrade red flags. Return strict JSON with keys: "
        "symptoms (array of objects name,duration,severity), medical_history, current_medications, allergies, "
        "severity_score (1-10 or null), urgency (emergency|urgent|routine), next_questions (max 4)."
    )
    prompt = json.dumps(
        {
            "message": state["message"],
            "duration": state.get("duration"),
            "severity": state.get("severity"),
            "medical_history": state.get("medical_history", []),
            "medications": state.get("medications", []),
            "allergies": state.get("allergies", []),
        },
        ensure_ascii=False,
    )
    parsed = _gemini_json(system, prompt)
    intake = parsed if isinstance(parsed, dict) else fallback
    urgency = str(intake.get("urgency") or "routine").lower()
    if urgency not in {"emergency", "urgent", "routine"}:
        urgency = "routine"
    if state.get("emergency"):
        urgency = "emergency"
    intake.pop("urgency", None)
    return {"structured_intake": intake, "urgency": urgency}


def knowledge_node(state: ClinicalState) -> ClinicalState:
    symptoms = state.get("structured_intake", {}).get("symptoms") or []
    query = "; ".join((s.get("name") if isinstance(s, dict) else str(s)) for s in symptoms) or state["message"]
    evidence = retrieve_protocols(query)
    if not evidence:
        return {"evidence": [], "differential": []}

    system = (
        "You are the Clinical Knowledge Agent. Use ONLY the supplied retrieved evidence. "
        "Return a JSON array of up to 5 differential considerations for clinician review. "
        "Each item must contain condition, rationale, evidence_source. Do not provide medication, dosing, or a definitive diagnosis."
    )
    prompt = json.dumps({"symptoms": symptoms, "evidence": evidence}, ensure_ascii=False)
    parsed = _gemini_json(system, prompt)
    differential = parsed if isinstance(parsed, list) else []
    return {"evidence": evidence, "differential": differential[:5]}


def referral_node(state: ClinicalState) -> ClinicalState:
    facilities = search_nearby_facilities(
        state.get("state"),
        state.get("lga"),
        emergency=bool(state.get("emergency") or state.get("urgency") == "emergency"),
    )
    return {"referrals": facilities}


def scribe_node(state: ClinicalState) -> ClinicalState:
    intake = state.get("structured_intake") or {
        "symptoms": [{"name": state["message"], "duration": state.get("duration"), "severity": state.get("severity")}],
        "medical_history": state.get("medical_history", []),
        "current_medications": state.get("medications", []),
        "allergies": state.get("allergies", []),
    }
    fallback = {
        "subjective": intake,
        "objective": "Not provided during remote intake. No vitals or examination findings were inferred.",
        "assessment": {
            "urgency": state.get("urgency", "routine"),
            "red_flags": state.get("red_flags", []),
            "differential_for_clinician_review": state.get("differential", []),
        },
        "plan": [
            "Licensed clinician review required before diagnosis or treatment.",
            "No autonomous prescription or medication dose generated.",
        ],
    }
    system = (
        "You are a Clinical Scribe. Create a concise SOAP note from supplied facts only. "
        "Never invent vitals, examination findings, diagnoses, medication doses, or treatment orders. "
        "Use 'Not provided' when data is absent. Return strict JSON keys subjective, objective, assessment, plan."
    )
    parsed = _gemini_json(system, json.dumps({"intake": intake, "urgency": state.get("urgency"), "red_flags": state.get("red_flags", []), "differential": state.get("differential", [])}, ensure_ascii=False))
    return {"soap_note": parsed if isinstance(parsed, dict) else fallback}
