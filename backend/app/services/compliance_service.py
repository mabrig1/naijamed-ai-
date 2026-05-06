"""
NAFDAC Compliance Intelligence — Claude-powered regulatory assistant for NaijaMed AI.

Synchronous functions; FastAPI runs them in its thread pool.
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings

_DISCLAIMER = (
    "This is AI-generated guidance for informational purposes only. "
    "It does not constitute legal or regulatory advice. "
    "Always consult a certified NAFDAC regulatory consultant before "
    "submitting any application or making compliance decisions."
)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_GENERATE_DOCUMENT_PROMPT = """
You are a senior NAFDAC regulatory affairs specialist in Nigeria with 15 years of experience registering herbal medicines and food supplements.

Generate a complete NAFDAC product registration document for the following product:

Herb Information:
- Common name: {herb_name}
- Scientific name: {scientific_name}
- Region of origin: {region_found}
- Description: {description}

Formulation Details:
- Formulation type: {formulation_type}
- Target disease/condition: {target_disease}
- Key active compound: {compound_used}
- Recommended dosage: {dosage_suggestion}
- Excipients: {excipients}
- Manufacturing process: {manufacturing_summary}
- Predicted side effects: {side_effects}
- Disclaimer: {formulation_disclaimer}

Product type (regulatory category): {product_type}

Generate all sections needed for a NAFDAC registration dossier.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "product_name": "<suggested commercial product name — memorable, regulatory-compliant>",
  "manufacturer_details_template": {{
    "company_name": "<placeholder — to be filled by applicant>",
    "nafdac_manufacturer_number": "<placeholder>",
    "address": "<placeholder>",
    "country": "Nigeria",
    "gmp_certificate_number": "<placeholder>",
    "contact_person": "<placeholder>",
    "phone": "<placeholder>",
    "email": "<placeholder>"
  }},
  "ingredient_declaration": [
    {{
      "ingredient": "<ingredient name>",
      "quantity_per_unit": "<e.g. 500 mg>",
      "function": "<active | excipient | preservative | flavour>",
      "source": "<plant / synthetic / mineral>"
    }}
  ],
  "dosage_and_usage": {{
    "recommended_dose": "<dose string>",
    "frequency": "<e.g. twice daily>",
    "route_of_administration": "<oral | topical | …>",
    "special_instructions": "<e.g. take with food>",
    "contraindications": ["<contraindication 1>", "<contraindication 2>"],
    "drug_interactions": ["<interaction 1>"]
  }},
  "safety_warnings": [
    "<warning 1 — e.g. Keep out of reach of children>",
    "<warning 2>"
  ],
  "labeling_requirements": {{
    "front_panel": ["<required element 1>", "<required element 2>"],
    "back_panel": ["<required element 1>", "<required element 2>"],
    "nafdac_number_placement": "<description of where NAFDAC number must appear>",
    "language_requirements": "<English + at least one local language recommended>"
  }},
  "storage_conditions": {{
    "temperature": "<e.g. Store below 30°C>",
    "humidity": "<e.g. Protect from moisture — below 65% RH>",
    "light": "<e.g. Keep away from direct sunlight>",
    "special_notes": "<any additional storage requirements>"
  }},
  "shelf_life_recommendation": "<e.g. 24 months from date of manufacture>",
  "nafdac_product_category": "<exact NAFDAC category code and name>",
  "required_supporting_documents": [
    "<document 1 needed to complete registration>",
    "<document 2>"
  ]
}}

Rules:
- ingredient_declaration: include ALL excipients, not just actives.
- safety_warnings: minimum 4 warnings appropriate for Nigerian consumers.
- required_supporting_documents: minimum 6 documents aligned to current NAFDAC guidelines.
- Return only the JSON — no surrounding text.
"""

_CHECKLIST_PROMPT = """
You are a NAFDAC regulatory affairs expert in Nigeria.

Generate a detailed, step-by-step NAFDAC product registration approval checklist
for the following product type: "{product_type}"

Return ONLY a valid JSON array where each element has this exact structure
(no markdown, no explanation):
[
  {{
    "step": <integer starting at 1>,
    "title": "<short action title>",
    "description": "<detailed description of what must be done at this step>",
    "required_documents": ["<document 1>", "<document 2>"],
    "estimated_time": "<e.g. 2-4 weeks>",
    "tips": ["<practical tip 1>", "<practical tip 2>"]
  }}
]

Rules:
- Cover the FULL NAFDAC registration journey from initial preparation to certificate issuance.
- Minimum 8 steps.
- required_documents: list every document needed at that specific step.
- tips: at least 1 practical tip per step drawn from real NAFDAC applicant experience.
- Be specific to Nigerian regulatory practice — do not genericise.
- Return only the JSON array — no surrounding text.
"""

_CHAT_PROMPT = """
You are NaijaMed AI's NAFDAC regulatory compliance assistant — an expert in Nigerian pharmaceutical and herbal medicine regulation with deep knowledge of NAFDAC guidelines, SON standards, and West African regulatory harmonisation.

User context:
{context_block}

User question: "{question}"

Provide a thorough, accurate answer grounded in current NAFDAC regulatory practice.
After your answer, suggest 2-3 follow-up questions the user might find useful.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "answer": "<complete answer — can be multiple paragraphs>",
  "suggested_next_questions": [
    "<follow-up question 1>",
    "<follow-up question 2>",
    "<follow-up question 3>"
  ]
}}

Rules:
- Be specific to Nigeria — reference actual NAFDAC departments, fee schedules, or guidelines where relevant.
- If the question requires on-site inspection or laboratory work, say so explicitly.
- Return only the JSON — no surrounding text.
"""

# ---------------------------------------------------------------------------
# Hardcoded NAFDAC approval stages (factual, doesn't require AI)
# ---------------------------------------------------------------------------

NAFDAC_STAGES = [
    {
        "stage_number": 1,
        "name": "Pre-Submission Preparation",
        "description": (
            "Compile all technical dossiers, conduct stability studies, and obtain "
            "GMP certificate for your manufacturing site."
        ),
        "key_requirements": [
            "Certificate of Analysis (CoA) from accredited laboratory",
            "GMP compliance certificate",
            "Stability study data (minimum 6 months accelerated)",
            "Trademark registration from FCCPC or CAC",
            "Evidence of business registration (CAC certificate)",
        ],
        "typical_duration": "3–6 months",
        "fees_approximate": "No NAFDAC fee at this stage",
    },
    {
        "stage_number": 2,
        "name": "Application Submission (NAFDAC SON Portal)",
        "description": (
            "Submit dossier via the NAFDAC e-submission portal. Pay the applicable "
            "screening fee. Receive an application reference number."
        ),
        "key_requirements": [
            "Complete product dossier (CTD format recommended)",
            "Application form duly signed by a Pharmacist/Regulatory Affairs officer",
            "Proof of payment of screening fee",
            "Product samples (minimum 5 units)",
            "Labeling artwork (draft and final)",
        ],
        "typical_duration": "1–2 weeks",
        "fees_approximate": "₦50,000 – ₦200,000 screening fee (product-type dependent)",
    },
    {
        "stage_number": 3,
        "name": "Dossier Screening and Acceptance",
        "description": (
            "NAFDAC evaluates the completeness of the dossier. Deficiency letters "
            "are issued within 30 days if information is missing."
        ),
        "key_requirements": [
            "All documents from Stage 1 & 2",
            "Response to any deficiency queries within specified timeline",
        ],
        "typical_duration": "4–8 weeks",
        "fees_approximate": "No additional fee",
    },
    {
        "stage_number": 4,
        "name": "Product Evaluation and Laboratory Analysis",
        "description": (
            "NAFDAC scientists review formulation, safety, and efficacy data. "
            "Product samples are tested in NAFDAC laboratories."
        ),
        "key_requirements": [
            "Product samples for laboratory testing",
            "Analytical method validation data",
            "Reference standards if applicable",
            "Pharmacovigilance plan for new herbal products",
        ],
        "typical_duration": "3–6 months",
        "fees_approximate": "₦100,000 – ₦500,000 laboratory fees",
    },
    {
        "stage_number": 5,
        "name": "Facility Inspection (GMP Audit)",
        "description": (
            "NAFDAC inspectors visit the manufacturing facility to verify GMP compliance. "
            "Foreign manufacturers may require WHO pre-qualification."
        ),
        "key_requirements": [
            "Site master file (SMF)",
            "Standard Operating Procedures (SOPs) — minimum 20 core SOPs",
            "Batch manufacturing records",
            "Qualified Person (QP) on site",
            "Equipment calibration and validation records",
        ],
        "typical_duration": "1–3 months (scheduling dependent)",
        "fees_approximate": "₦200,000 – ₦800,000 inspection fee + travel costs",
    },
    {
        "stage_number": 6,
        "name": "Labeling Review",
        "description": (
            "NAFDAC reviews final label artwork for compliance with labeling "
            "regulations under NAFDAC Act CAP N1 LFN 2004."
        ),
        "key_requirements": [
            "Final label artwork (front, back, sides)",
            "Package insert / patient information leaflet",
            "All text in English; local language translation encouraged",
            "NAFDAC registration number placement confirmed",
        ],
        "typical_duration": "4–6 weeks",
        "fees_approximate": "Included in overall registration fee",
    },
    {
        "stage_number": 7,
        "name": "Approval and Registration Certificate",
        "description": (
            "Upon satisfactory evaluation, NAFDAC issues a registration certificate "
            "valid for 5 years. The NAFDAC registration number must appear on all packs."
        ),
        "key_requirements": [
            "Payment of final registration fee",
            "Signed undertaking for post-market surveillance cooperation",
            "Pharmacovigilance contact designation",
        ],
        "typical_duration": "2–4 weeks after approval decision",
        "fees_approximate": "₦250,000 – ₦1,500,000 registration fee (category-based)",
    },
    {
        "stage_number": 8,
        "name": "Post-Market Surveillance and Renewal",
        "description": (
            "Maintain registration through periodic renewal (every 5 years), "
            "adverse event reporting, and batch release notifications."
        ),
        "key_requirements": [
            "Annual renewal notification to NAFDAC",
            "Adverse event / pharmacovigilance reports",
            "Post-market stability data",
            "Renewal application 6 months before expiry",
        ],
        "typical_duration": "Ongoing — renewal every 5 years",
        "fees_approximate": "₦150,000 – ₦500,000 renewal fee",
    },
]

NAFDAC_GENERAL_NOTES = [
    "All fees are indicative and subject to change — verify current rates on nafdac.gov.ng.",
    "Engage a certified regulatory affairs consultant registered with PSN or RAPS for best results.",
    "The NAFDAC e-submission portal (eSub) is the mandatory channel for all new applications as of 2023.",
    "Herbal medicines must comply with the NAFDAC Guidelines for Registration of Traditional Medicines.",
    "Products with therapeutic claims require clinical evidence; food supplements may not make disease claims.",
]


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


def _call_claude_json(prompt: str) -> dict[str, Any] | list:
    try:
        message = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
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
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else fallback
    return str(value)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def generate_nafdac_document(
    herb: dict[str, Any],
    formulation: dict[str, Any],
    product_type: str,
) -> dict[str, Any]:
    """
    Generate a structured NAFDAC registration document draft using Claude.

    herb dict keys: name_english, scientific_name, region_found, description.
    formulation dict keys: formulation_type, target_disease, compound_used,
        dosage_suggestion, excipients_needed, manufacturing_process_summary,
        side_effects_prediction, disclaimer.

    Returns a rich dict with all document sections stored in content_json.
    """
    prompt = _GENERATE_DOCUMENT_PROMPT.format(
        herb_name=_fmt(herb.get("name_english")),
        scientific_name=_fmt(herb.get("scientific_name")),
        region_found=_fmt(herb.get("region_found")),
        description=_fmt(herb.get("description")),
        formulation_type=_fmt(formulation.get("formulation_type")),
        target_disease=_fmt(formulation.get("target_disease")),
        compound_used=_fmt(formulation.get("compound_used")),
        dosage_suggestion=_fmt(formulation.get("dosage_suggestion")),
        excipients=_fmt(formulation.get("excipients_needed")),
        manufacturing_summary=_fmt(formulation.get("manufacturing_process_summary")),
        side_effects=_fmt(formulation.get("side_effects_prediction")),
        formulation_disclaimer=_fmt(formulation.get("disclaimer")),
        product_type=product_type.strip(),
    )

    result = _call_claude_json(prompt)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unexpected response format for document generation.",
        )

    defaults: dict[str, Any] = {
        "product_name": None,
        "manufacturer_details_template": {},
        "ingredient_declaration": [],
        "dosage_and_usage": {},
        "safety_warnings": [],
        "labeling_requirements": {},
        "storage_conditions": {},
        "shelf_life_recommendation": None,
        "nafdac_product_category": None,
        "required_supporting_documents": [],
    }
    return {**defaults, **result}


def answer_compliance_question(question: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Answer a NAFDAC compliance question using Claude acting as a regulatory expert.

    Returns a dict with keys: answer, suggested_next_questions.
    The caller is responsible for appending the standard disclaimer.
    """
    if context:
        context_lines = [f"- {k}: {v}" for k, v in context.items() if v]
        context_block = "\n".join(context_lines) if context_lines else "No additional context provided."
    else:
        context_block = "No additional context provided."

    prompt = _CHAT_PROMPT.format(
        question=question.strip(),
        context_block=context_block,
    )

    result = _call_claude_json(prompt)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unexpected response format for chat.",
        )

    defaults: dict[str, Any] = {
        "answer": "",
        "suggested_next_questions": [],
    }
    return {**defaults, **result}


def get_approval_checklist(product_type: str) -> list[dict[str, Any]]:
    """
    Generate a product-type-specific NAFDAC approval checklist using Claude.

    Returns a list of step dicts with keys:
    step, title, description, required_documents, estimated_time, tips.
    """
    prompt = _CHECKLIST_PROMPT.format(product_type=product_type.strip())

    result = _call_claude_json(prompt)
    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unexpected format for checklist generation.",
        )

    # Normalise each step — fill any missing keys with safe defaults
    normalised = []
    for i, item in enumerate(result, start=1):
        normalised.append({
            "step": item.get("step", i),
            "title": item.get("title", f"Step {i}"),
            "description": item.get("description", ""),
            "required_documents": item.get("required_documents", []),
            "estimated_time": item.get("estimated_time", "varies"),
            "tips": item.get("tips", []),
        })
    return normalised
