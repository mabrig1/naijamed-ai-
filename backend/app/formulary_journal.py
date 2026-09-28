from __future__ import annotations

import json
import re
from typing import Any

from .core.config import settings


APPRAISAL_TEMPLATES: dict[str, list[dict[str, str]]] = {
    "general": [
        {"id": "question", "label": "Research question", "prompt": "Is the research question clearly defined and clinically/scientifically relevant?"},
        {"id": "design", "label": "Study design", "prompt": "Is the design appropriate for the stated question?"},
        {"id": "population", "label": "Population", "prompt": "Are participants/sample selection and setting appropriate and clearly described?"},
        {"id": "bias", "label": "Bias & confounding", "prompt": "What important sources of bias or confounding remain?"},
        {"id": "outcomes", "label": "Outcomes", "prompt": "Are outcomes valid, prespecified and measured appropriately?"},
        {"id": "statistics", "label": "Statistics", "prompt": "Are the statistical methods, uncertainty and effect estimates appropriate?"},
        {"id": "harms", "label": "Safety / harms", "prompt": "Are adverse events, safety signals or other harms adequately reported?"},
        {"id": "applicability", "label": "Applicability", "prompt": "How applicable are the findings to the intended population, setting or research question?"},
        {"id": "limitations", "label": "Limitations", "prompt": "What limitations materially affect interpretation?"},
        {"id": "bottom_line", "label": "Bottom line", "prompt": "What is the most defensible conclusion from this paper?"},        
    ],
    "rct": [
        {"id": "randomization", "label": "Randomization", "prompt": "Was allocation randomized and adequately concealed?"},
        {"id": "blinding", "label": "Blinding", "prompt": "Were participants, investigators and outcome assessors blinded where feasible?"},
        {"id": "baseline", "label": "Baseline balance", "prompt": "Were groups comparable at baseline?"},
        {"id": "followup", "label": "Follow-up", "prompt": "Was follow-up complete and were withdrawals handled appropriately?"},
        {"id": "analysis", "label": "Analysis", "prompt": "Was the analysis appropriate, including intention-to-treat where relevant?"},
        {"id": "effect", "label": "Effect estimate", "prompt": "Are absolute/relative effects and confidence intervals clinically meaningful?"},
        {"id": "harms", "label": "Harms", "prompt": "Were adverse events and serious adverse events reported adequately?"},
        {"id": "applicability", "label": "Applicability", "prompt": "Can the findings reasonably apply to the target population or setting?"},
    ],
    "pk": [
        {"id": "sampling", "label": "Sampling schedule", "prompt": "Is the concentration-time sampling schedule adequate for the PK parameters claimed?"},
        {"id": "assay", "label": "Bioanalytical method", "prompt": "Is assay validation/sensitivity sufficient for the reported concentrations?"},
        {"id": "nca_model", "label": "PK method", "prompt": "Are NCA/model assumptions appropriate and transparently described?"},
        {"id": "terminal", "label": "Terminal phase", "prompt": "Is terminal-phase selection adequate for half-life and AUC extrapolation?"},
        {"id": "variability", "label": "Variability", "prompt": "Are intersubject variability and uncertainty adequately reported?"},
        {"id": "covariates", "label": "Covariates", "prompt": "Are important covariates, food effects, organ impairment or interactions addressed where relevant?"},
        {"id": "dose", "label": "Dose proportionality", "prompt": "Are dose proportionality/exposure relationships supported by the data?"},
        {"id": "interpretation", "label": "Interpretation", "prompt": "Do the conclusions stay within the limits of the PK evidence?"},
    ],
}


def appraisal_template(name: str | None) -> list[dict[str, str]]:
    key = name if name in APPRAISAL_TEMPLATES else "general"
    return [dict(item) for item in APPRAISAL_TEMPLATES[key]]


def evidence_snapshot(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        extraction = entry.get("extraction") or {}
        rows.append(
            {
                "id": entry["_id"],
                "title": entry.get("title"),
                "doi": entry.get("doi"),
                "journal": entry.get("journal"),
                "published": entry.get("published"),
                "study_design": extraction.get("study_design"),
                "population": extraction.get("population"),
                "sample_size": extraction.get("sample_size"),
                "intervention": extraction.get("intervention"),
                "comparator": extraction.get("comparator"),
                "dosing_regimen": extraction.get("dosing_regimen") or [],
                "primary_endpoints": extraction.get("primary_endpoints") or [],
                "p_values": extraction.get("p_values") or [],
                "confidence_intervals": extraction.get("confidence_intervals") or [],
                "adverse_events": extraction.get("adverse_events") or [],
                "pk_parameters": extraction.get("pk_parameters") or {},
                "key_findings": extraction.get("key_findings") or [],
                "limitations": extraction.get("limitations") or [],
                "evidence_spans": (extraction.get("evidence_spans") or [])[:20],
            }
        )
    return rows


def _fallback_fact_check(claim: str, snapshot: list[dict[str, Any]]) -> dict[str, Any]:
    citations = [f"PAPER:{row['id']}" for row in snapshot[:5]]
    return {
        "claim": claim,
        "verdict": "unclear",
        "confidence": "low",
        "rationale": (
            "The automated fact-check model is unavailable or the linked structured evidence is insufficient "
            "to determine whether this claim is supported. Review the cited paper records and original sources."
        ),
        "citations": citations,
        "contradictory_points": [],
        "verification_steps": [
            "Check the original article text for the exact outcome, population and analysis.",
            "Confirm effect estimates, confidence intervals and statistical methods.",
            "Do not treat structured extraction as a substitute for source verification.",
        ],
        "method": "deterministic_fallback",
    }


def fact_check_claim(claim: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = evidence_snapshot(entries)
    if not snapshot:
        return _fallback_fact_check(claim, snapshot)

    allowed = {f"PAPER:{row['id']}" for row in snapshot}
    if not settings.effective_gemini_key:
        return _fallback_fact_check(claim, snapshot)

    evidence_text = "\n\n".join(
        f"[PAPER:{row['id']}]\n{json.dumps(row, ensure_ascii=False, default=str)}"
        for row in snapshot
    )
    prompt = f"""
You are Formulary Journal Club Fact Check. Evaluate a discussion claim ONLY against the linked
structured evidence below. This is research appraisal, not patient-specific medical advice.

CLAIM:
{claim}

LINKED EVIDENCE:
{evidence_text}

Return ONLY JSON with exactly:
{{
  "verdict": "supported" | "contradicted" | "mixed" | "unclear",
  "confidence": "low" | "medium" | "high",
  "rationale": "brief explanation",
  "citations": ["PAPER:entry-id"],
  "contradictory_points": ["..."],
  "verification_steps": ["..."]
}}

Rules:
- Cite only PAPER IDs shown above.
- Do not infer missing data.
- Distinguish statistical significance from clinical/scientific importance.
- If evidence does not directly answer the claim, verdict must be unclear or mixed.
- If an extraction could be wrong, say the original article must be checked.
"""
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.effective_gemini_key)
        model_name = settings.FORMULARY_LLM_MODEL or settings.CLINICAL_LLM_MODEL
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        raw = (getattr(response, "text", "") or "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
        parsed = json.loads(raw)
        citations = [str(value) for value in parsed.get("citations") or []]
        if any(value not in allowed for value in citations):
            return _fallback_fact_check(claim, snapshot)
        verdict = str(parsed.get("verdict") or "unclear").lower()
        if verdict not in {"supported", "contradicted", "mixed", "unclear"}:
            verdict = "unclear"
        confidence = str(parsed.get("confidence") or "low").lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        return {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "rationale": str(parsed.get("rationale") or "").strip(),
            "citations": citations,
            "contradictory_points": [str(value) for value in (parsed.get("contradictory_points") or [])][:10],
            "verification_steps": [str(value) for value in (parsed.get("verification_steps") or [])][:10],
            "method": f"gemini:{model_name}",
        }
    except Exception:
        return _fallback_fact_check(claim, snapshot)
