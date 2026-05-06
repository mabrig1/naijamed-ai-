"""
Clinical Research Intelligence — Claude-powered trial analysis for NaijaMed AI.

Synchronous functions; FastAPI runs them in its thread pool.
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SUMMARIZE_TRIAL_PROMPT = """
You are a senior clinical research scientist reviewing a study on Nigerian herbal medicine.

Clinical trial data:
- Title: {study_title}
- Herb: {herb_name} ({scientific_name})
- Phase: {study_phase}
- Status: {status}
- Methodology: {methodology}
- Patient count: {patient_count}
- Duration: {start_date} to {end_date}
- Outcome summary: {outcome_summary}
- Effectiveness score: {effectiveness_score}/100
- Key findings: {findings}
- Statistical data: {statistical_data}
- Publication DOI: {publication_doi}
- Peer verified: {is_verified}

Produce a rigorous yet accessible scientific summary of this clinical trial.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "plain_language_summary": "<2-3 paragraph summary a non-scientist can understand>",
  "statistical_significance": "<assessment of the statistical strength of findings, noting p-values or CIs if provided>",
  "confidence_level": "<low | medium | high — based on study design, sample size, and peer verification>",
  "literature_comparison": "<how these findings compare with existing published research on this herb>",
  "recommended_next_steps": [
    "<specific next research action 1>",
    "<specific next research action 2>",
    "<specific next research action 3>"
  ]
}}

Rules:
- confidence_level must be exactly one of: low, medium, high.
- recommended_next_steps: list at least 3 specific, actionable research milestones.
- Be scientifically honest — if the study is weak, say so clearly.
- Return only the JSON — no surrounding text.
"""

_EVIDENCE_SCORE_PROMPT = """
You are a systematic review expert assessing the body of evidence for a Nigerian medicinal herb.

Herb: {herb_name} ({scientific_name})
Total trials reviewed: {trial_count}
Verified/peer-reviewed trials: {verified_count}

Trial summaries:
{trials_summary}

Aggregate all available evidence and produce an overall evidence assessment.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "evidence_score": <integer 0-100>,
  "verdict": "<Promising | Needs more study | Not recommended>",
  "key_findings": [
    "<key finding 1 supported by the evidence>",
    "<key finding 2>",
    "<key finding 3>"
  ],
  "safety_signals": [
    "<safety concern or signal 1 from the evidence>",
    "<safety concern 2 — or 'No significant safety signals identified' if none>"
  ]
}}

Rules:
- evidence_score: 0 = no evidence / harmful, 100 = robust multi-phase clinical evidence.
- verdict must be exactly one of: "Promising", "Needs more study", "Not recommended".
- key_findings: list at least 3 findings derived from the trials.
- safety_signals: list at least 1 entry (use the no-signals message if none exist).
- Weight verified trials more heavily than unverified submissions.
- Return only the JSON — no surrounding text.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client():
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env.",
        )
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_claude(prompt: str) -> dict[str, Any]:
    try:
        message = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        )

    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned non-JSON response: {exc}. Raw: {raw_text[:300]}",
        )


def _fmt(value: Any, fallback: str = "not provided") -> str:
    if value is None:
        return fallback
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def summarize_trial(trial_data: dict[str, Any]) -> dict[str, Any]:
    """
    Ask Claude to produce a structured research summary for a single clinical trial.

    trial_data must contain: study_title, herb_name, scientific_name, study_phase,
    status, methodology, patient_count, start_date, end_date, outcome_summary,
    effectiveness_score, findings, statistical_data, publication_doi, is_verified.

    Returns keys: plain_language_summary, statistical_significance, confidence_level,
    literature_comparison, recommended_next_steps.
    """
    prompt = _SUMMARIZE_TRIAL_PROMPT.format(
        study_title=_fmt(trial_data.get("study_title")),
        herb_name=_fmt(trial_data.get("herb_name")),
        scientific_name=_fmt(trial_data.get("scientific_name")),
        study_phase=_fmt(trial_data.get("study_phase")),
        status=_fmt(trial_data.get("status")),
        methodology=_fmt(trial_data.get("methodology")),
        patient_count=_fmt(trial_data.get("patient_count")),
        start_date=_fmt(trial_data.get("start_date")),
        end_date=_fmt(trial_data.get("end_date")),
        outcome_summary=_fmt(trial_data.get("outcome_summary")),
        effectiveness_score=_fmt(trial_data.get("effectiveness_score")),
        findings=_fmt(trial_data.get("findings")),
        statistical_data=_fmt(trial_data.get("statistical_data")),
        publication_doi=_fmt(trial_data.get("publication_doi")),
        is_verified=str(trial_data.get("is_verified", False)),
    )
    result = _call_claude(prompt)

    # Normalise confidence_level to allowed values
    cl = result.get("confidence_level", "low").lower()
    if cl not in ("low", "medium", "high"):
        cl = "low"
    result["confidence_level"] = cl

    defaults: dict[str, Any] = {
        "plain_language_summary": "",
        "statistical_significance": "",
        "confidence_level": "low",
        "literature_comparison": "",
        "recommended_next_steps": [],
    }
    return {**defaults, **result}


def calculate_evidence_score(
    herb_name: str,
    scientific_name: str | None,
    trials: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Ask Claude to review all trials for a herb and produce an aggregate evidence score.

    Each dict in trials must contain: id, study_title, study_phase, status,
    patient_count, outcome_summary, effectiveness_score, is_verified, findings.

    Returns keys: evidence_score, verdict, key_findings, safety_signals.
    """
    if not trials:
        return {
            "evidence_score": 0,
            "verdict": "Needs more study",
            "key_findings": ["No clinical trials have been submitted for this herb yet."],
            "safety_signals": ["Insufficient data to assess safety profile."],
        }

    lines = []
    for t in trials:
        verified = "VERIFIED" if t.get("is_verified") else "unverified"
        lines.append(
            f"[{verified}] Trial #{t.get('id')} — {t.get('study_title', 'Untitled')}\n"
            f"  Phase: {_fmt(t.get('study_phase'))} | Status: {_fmt(t.get('status'))}\n"
            f"  Patients: {_fmt(t.get('patient_count'))} | "
            f"Effectiveness: {_fmt(t.get('effectiveness_score'))}/100\n"
            f"  Summary: {_fmt(t.get('outcome_summary'))}\n"
            f"  Findings: {_fmt(t.get('findings'))}"
        )

    prompt = _EVIDENCE_SCORE_PROMPT.format(
        herb_name=herb_name,
        scientific_name=scientific_name or "unknown",
        trial_count=len(trials),
        verified_count=sum(1 for t in trials if t.get("is_verified")),
        trials_summary="\n\n".join(lines),
    )
    result = _call_claude(prompt)

    # Clamp score to 0-100
    score = result.get("evidence_score", 0)
    if not isinstance(score, int):
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = 0
    result["evidence_score"] = max(0, min(100, score))

    # Normalise verdict
    allowed_verdicts = {"Promising", "Needs more study", "Not recommended"}
    if result.get("verdict") not in allowed_verdicts:
        result["verdict"] = "Needs more study"

    defaults: dict[str, Any] = {
        "evidence_score": 0,
        "verdict": "Needs more study",
        "key_findings": [],
        "safety_signals": [],
    }
    return {**defaults, **result}
