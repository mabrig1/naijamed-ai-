"""
Herbal Intelligence Engine — Gemini-powered analysis for NaijaMed AI.

All functions are synchronous so FastAPI can run them in its thread-pool
without blocking the event loop (declare routes as `def`, not `async def`).
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_ANALYZE_PROMPT = """
You are a senior pharmaceutical researcher specialising in African ethnobotany and drug discovery.

Analyse the Nigerian medicinal herb "{herb_name}".
User context: "{user_description}"

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "scientific_name": "<binomial name or null>",
  "medicinal_properties": ["<property 1>", "<property 2>", "..."],
  "active_compounds": [
    {{"name": "<compound name>", "formula": "<molecular formula or null>", "role": "<pharmacological role>"}}
  ],
  "diseases_treated": ["<disease 1>", "<disease 2>", "..."],
  "drug_production_pathways": [
    "<pathway description e.g. extraction method → formulation type>"
  ],
  "research_gaps": ["<gap 1>", "<gap 2>", "..."],
  "safety_warnings": ["<warning 1>", "<warning 2>", "..."]
}}

Rules:
- List at least 4 medicinal_properties, 3 active_compounds, 4 diseases_treated.
- Be scientifically accurate; cite consensus where it exists.
- If information is uncertain, note it inside the relevant string value.
- Return only the JSON — no surrounding text.
"""

_SUGGEST_DRUG_PROMPT = """
You are a drug-development expert advising a Nigerian pharmaceutical startup.

Herb: "{herb_name}" (scientific name: {scientific_name})
Target disease: "{target_disease}"

Assess how this herb could be developed into a pharmaceutical drug for the target disease.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "feasibility_score": <integer 0-100>,
  "mechanism_of_action": "<how active compounds would work against the disease>",
  "relevant_compounds": ["<compound 1>", "<compound 2>", "..."],
  "production_pathway": "<step-by-step pathway from raw herb to final drug form>",
  "clinical_trial_recommendations": [
    "<phase and recommendation 1>",
    "<recommendation 2>"
  ],
  "regulatory_considerations": "<NAFDAC and international regulatory notes>",
  "estimated_timeline_years": "<range e.g. 8-12 years>",
  "risks": ["<risk 1>", "<risk 2>", "..."]
}}

Rules:
- feasibility_score: 0 = impossible, 100 = already in clinical trials.
- Be realistic and evidence-based.
- Return only the JSON — no surrounding text.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_model():
    key = settings.effective_gemini_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env.",
        )
    import google.generativeai as genai

    genai.configure(api_key=key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2,       # low temperature for factual, reproducible output
            max_output_tokens=2048,
        ),
    )


def _call_gemini(prompt: str) -> dict[str, Any]:
    """Call Gemini and return parsed JSON dict. Raises HTTPException on failure."""
    model = _get_model()
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {exc}",
        )

    # Gemini with response_mime_type=application/json should return clean JSON,
    # but defensively strip markdown code fences if present.
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

def analyze_herb(herb_name: str, user_description: str = "") -> dict[str, Any]:
    """
    Ask Gemini to analyse a Nigerian herb and return a structured dict.

    Returns keys: scientific_name, medicinal_properties, active_compounds,
    diseases_treated, drug_production_pathways, research_gaps, safety_warnings.
    """
    prompt = _ANALYZE_PROMPT.format(
        herb_name=herb_name.strip(),
        user_description=user_description.strip() or "No additional context provided.",
    )
    result = _call_gemini(prompt)

    # Normalise: guarantee all expected keys exist, even if the model omits one.
    defaults: dict[str, Any] = {
        "scientific_name": None,
        "medicinal_properties": [],
        "active_compounds": [],
        "diseases_treated": [],
        "drug_production_pathways": [],
        "research_gaps": [],
        "safety_warnings": [],
    }
    return {**defaults, **result}


def suggest_drug_possibility(
    herb_name: str,
    scientific_name: str | None,
    target_disease: str,
) -> dict[str, Any]:
    """
    Ask Gemini to assess how an herb could be turned into a drug for a disease.

    Returns keys: feasibility_score, mechanism_of_action, relevant_compounds,
    production_pathway, clinical_trial_recommendations, regulatory_considerations,
    estimated_timeline_years, risks.
    """
    prompt = _SUGGEST_DRUG_PROMPT.format(
        herb_name=herb_name.strip(),
        scientific_name=scientific_name or "unknown",
        target_disease=target_disease.strip(),
    )
    result = _call_gemini(prompt)

    defaults: dict[str, Any] = {
        "feasibility_score": 0,
        "mechanism_of_action": "",
        "relevant_compounds": [],
        "production_pathway": "",
        "clinical_trial_recommendations": [],
        "regulatory_considerations": "",
        "estimated_timeline_years": "unknown",
        "risks": [],
    }
    return {**defaults, **result}
