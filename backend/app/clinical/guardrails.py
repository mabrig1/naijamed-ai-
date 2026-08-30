import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailDecision:
    blocked: bool
    emergency: bool
    reason: str | None = None
    matched_red_flags: tuple[str, ...] = ()


RED_FLAG_PATTERNS: dict[str, str] = {
    "chest pain": r"\b(chest pain|crushing chest|pressure in (my |the )?chest)\b",
    "severe bleeding": r"\b(severe|heavy|uncontrolled|won'?t stop)\s+(bleeding|blood loss)\b",
    "breathing difficulty": r"\b(can'?t breathe|cannot breathe|difficulty breathing|shortness of breath|gasping)\b",
    "loss of consciousness": r"\b(unconscious|passed out|not waking|unresponsive)\b",
    "seizure": r"\b(seizure|convulsion|fits? and (not|won'?t) stop)\b",
    "stroke signs": r"\b(face droop|slurred speech|sudden weakness|one side.*weak)\b",
    "severe allergic reaction": r"\b(anaphylaxis|throat swelling|tongue swelling.*breath)\b",
    "pregnancy emergency": r"\b(pregnan\w*.*severe bleeding|pregnan\w*.*severe abdominal pain)\b",
}

NON_MEDICAL_PATTERNS = [
    r"\b(write|do) (my )?(essay|assignment|code|program)\b",
    r"\b(bitcoin|crypto|football score|weather forecast|political campaign)\b",
    r"\b(generate (a )?(logo|image|song|poem))\b",
]

SELF_MEDICATION_PATTERNS = [
    r"\bwhat dose\b",
    r"\bhow many (tablets|capsules|mg|ml)\b",
    r"\bprescribe (me|for me)\b",
    r"\bwhich antibiotic should i take\b",
]


def evaluate_input(text: str) -> GuardrailDecision:
    normalized = " ".join(text.lower().split())
    red_flags = tuple(name for name, pattern in RED_FLAG_PATTERNS.items() if re.search(pattern, normalized, flags=re.I))
    if red_flags:
        return GuardrailDecision(False, True, "Emergency red-flag language detected", red_flags)
    if any(re.search(pattern, normalized, flags=re.I) for pattern in NON_MEDICAL_PATTERNS):
        return GuardrailDecision(True, False, "This clinical endpoint only handles health-related requests")
    return GuardrailDecision(False, False)


def asks_for_self_medication(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(re.search(pattern, normalized, flags=re.I) for pattern in SELF_MEDICATION_PATTERNS)


def patient_safety_notice(emergency: bool) -> str:
    if emergency:
        return (
            "Your symptoms may represent an emergency. Seek in-person emergency care immediately or contact your local emergency service. "
            "Do not wait for an AI response or self-medicate."
        )
    return (
        "This is clinical decision support, not a diagnosis or prescription. A licensed clinician should confirm any assessment and treatment plan."
    )
