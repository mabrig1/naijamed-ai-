from app.clinical.crypto import decrypt_json, encrypt_json
from app.clinical.guardrails import asks_for_self_medication, evaluate_input


def test_emergency_red_flag_overrides_llm():
    decision = evaluate_input("I have crushing chest pain and I cannot breathe")
    assert decision.emergency is True
    assert decision.blocked is False
    assert "chest pain" in decision.matched_red_flags


def test_non_medical_request_is_blocked():
    decision = evaluate_input("write my essay about public administration")
    assert decision.blocked is True


def test_self_medication_intent_is_detected():
    assert asks_for_self_medication("Which antibiotic should I take?") is True


def test_phi_round_trip(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    payload = {"symptom": "headache", "history": ["none"]}
    assert decrypt_json(encrypt_json(payload)) == payload
