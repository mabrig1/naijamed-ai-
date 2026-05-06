"""
AI Drug Formulation Lab — Claude-powered formulation generation for NaijaMed AI.

All functions are synchronous; FastAPI runs them in its thread pool.
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_GENERATE_PROMPT = """
You are a senior pharmaceutical formulation scientist with expertise in African botanicals and NAFDAC-regulated drug development.

Herb: "{herb_name}" (scientific name: {scientific_name})
Target disease: "{target_disease}"
Key active compound: "{compound_used}"
Desired formulation form: {formulation_type}

Design a complete drug formulation for the given herb and disease target.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "recommended_dosage": "<dosage string e.g. '500 mg twice daily for adults'>",
  "estimated_stability_months": <integer number of months>,
  "excipients_needed": [
    "<excipient 1 and its role e.g. Microcrystalline cellulose — binder>",
    "<excipient 2>"
  ],
  "manufacturing_process_summary": "<step-by-step process from raw herb to finished {formulation_type}>",
  "predicted_side_effects": ["<side effect 1>", "<side effect 2>"],
  "ai_notes": "<key formulation insights, stability challenges, or bioavailability considerations>",
  "estimated_cost_savings_usd": <number — estimated USD cost saving per 1000 units vs synthetic equivalent>,
  "next_steps": [
    "<step 1 e.g. Commission stability study at 40°C/75% RH>",
    "<step 2>"
  ],
  "disclaimer": "<mandatory safety/regulatory disclaimer for this formulation>"
}}

Rules:
- Be scientifically accurate and evidence-based.
- excipients_needed: list at least 4 excipients with their functional roles.
- next_steps: list at least 3 actionable development milestones.
- manufacturing_process_summary: include at least 5 numbered steps.
- Return only the JSON — no surrounding text.
"""

_COMPARE_PROMPT = """
You are a pharmaceutical development consultant advising a Nigerian biotech company.

You must compare two drug formulations and recommend which one to advance to clinical trials.

Formulation A (ID {id_1}):
- Herb: {herb_name_1}
- Type: {type_1}
- Target disease: {disease_1}
- Dosage: {dosage_1}
- Stability (months): {stability_1}
- Excipients: {excipients_1}
- Manufacturing summary: {manufacturing_1}
- Predicted side effects: {side_effects_1}
- Estimated cost savings (USD/1000 units): {cost_1}
- AI notes: {notes_1}

Formulation B (ID {id_2}):
- Herb: {herb_name_2}
- Type: {type_2}
- Target disease: {disease_2}
- Dosage: {dosage_2}
- Stability (months): {stability_2}
- Excipients: {excipients_2}
- Manufacturing summary: {manufacturing_2}
- Predicted side effects: {side_effects_2}
- Estimated cost savings (USD/1000 units): {cost_2}
- AI notes: {notes_2}

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "recommended_id": <{id_1} or {id_2}>,
  "reasoning": "<detailed explanation of why this formulation is preferred>",
  "trade_offs": [
    "<trade-off 1 describing what is sacrificed by choosing the recommended formulation>",
    "<trade-off 2>"
  ],
  "combined_next_steps": [
    "<step that applies to whichever formulation is taken forward>",
    "<step 2>"
  ]
}}

Rules:
- recommended_id must be exactly {id_1} or {id_2} — an integer, not a string.
- trade_offs: list at least 2.
- combined_next_steps: list at least 3 actionable milestones.
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
    """Call Claude and return parsed JSON dict. Raises HTTPException on failure."""
    client = _get_client()
    try:
        message = client.messages.create(
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


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def generate_formulation(
    herb_name: str,
    scientific_name: str | None,
    target_disease: str,
    compound_used: str,
    formulation_type: str,
) -> dict[str, Any]:
    """
    Ask Claude to design a drug formulation for an herb targeting a specific disease.

    Returns keys: recommended_dosage, estimated_stability_months, excipients_needed,
    manufacturing_process_summary, predicted_side_effects, ai_notes,
    estimated_cost_savings_usd, next_steps, disclaimer.
    """
    prompt = _GENERATE_PROMPT.format(
        herb_name=herb_name.strip(),
        scientific_name=scientific_name or "unknown",
        target_disease=target_disease.strip(),
        compound_used=compound_used.strip() if compound_used else "primary active compound",
        formulation_type=formulation_type,
    )
    result = _call_claude(prompt)

    defaults: dict[str, Any] = {
        "recommended_dosage": None,
        "estimated_stability_months": None,
        "excipients_needed": [],
        "manufacturing_process_summary": None,
        "predicted_side_effects": [],
        "ai_notes": None,
        "estimated_cost_savings_usd": None,
        "next_steps": [],
        "disclaimer": None,
    }
    return {**defaults, **result}


def compare_formulations(f1: dict[str, Any], f2: dict[str, Any]) -> dict[str, Any]:
    """
    Ask Claude to compare two formulation dicts and recommend which to advance.

    Each dict must contain: id, herb_name, formulation_type, target_disease,
    dosage_suggestion, stability_prediction, excipients_needed,
    manufacturing_process_summary, side_effects_prediction,
    estimated_cost_savings_usd, ai_notes.

    Returns keys: recommended_id, reasoning, trade_offs, combined_next_steps.
    """
    prompt = _COMPARE_PROMPT.format(
        id_1=f1["id"],
        herb_name_1=f1.get("herb_name", "Unknown"),
        type_1=f1.get("formulation_type", "unknown"),
        disease_1=f1.get("target_disease", "unspecified"),
        dosage_1=f1.get("dosage_suggestion", "not specified"),
        stability_1=f1.get("stability_prediction", "unknown"),
        excipients_1=", ".join(f1.get("excipients_needed") or []) or "not specified",
        manufacturing_1=f1.get("manufacturing_process_summary", "not specified"),
        side_effects_1=", ".join(f1.get("side_effects_prediction") or []) or "none listed",
        cost_1=f1.get("estimated_cost_savings_usd", "unknown"),
        notes_1=f1.get("ai_notes", "none"),
        id_2=f2["id"],
        herb_name_2=f2.get("herb_name", "Unknown"),
        type_2=f2.get("formulation_type", "unknown"),
        disease_2=f2.get("target_disease", "unspecified"),
        dosage_2=f2.get("dosage_suggestion", "not specified"),
        stability_2=f2.get("stability_prediction", "unknown"),
        excipients_2=", ".join(f2.get("excipients_needed") or []) or "not specified",
        manufacturing_2=f2.get("manufacturing_process_summary", "not specified"),
        side_effects_2=", ".join(f2.get("side_effects_prediction") or []) or "none listed",
        cost_2=f2.get("estimated_cost_savings_usd", "unknown"),
        notes_2=f2.get("ai_notes", "none"),
    )
    result = _call_claude(prompt)

    defaults: dict[str, Any] = {
        "recommended_id": f1["id"],
        "reasoning": "",
        "trade_offs": [],
        "combined_next_steps": [],
    }
    return {**defaults, **result}
