"""
Logistics Intelligence Engine — freight quotes, document generation, and anomaly detection.

Four public functions:
  get_freight_quotes         → Gemini simulates freight options across all 4 channels
  recommend_best_freight     → Claude picks the single best freight option
  generate_shipping_document → Claude generates structured JSON for any export document
  detect_shipment_anomaly    → Claude scans event timeline for delays, breaches, and risks
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_FREIGHT_QUOTES_PROMPT = """
You are a Nigerian agricultural export logistics specialist with deep knowledge of
international freight rates, Nigerian export infrastructure, and herb shipping requirements.

Generate realistic freight quotes for shipping Nigerian herbs:
- Origin: {origin_state} State, Nigeria
- Destination: {destination_country}
- Quantity: {quantity_kg} kg
- Herb type: {herb_type}

Return ONLY a valid JSON array (no markdown, no explanation) with exactly 4 items,
one per freight channel: air, sea, road, ecommerce.

Structure for each item:
{{
  "channel": "<air|sea|road|ecommerce>",
  "carrier": "<carrier name e.g. DHL Express, Ethiopian Airlines Cargo, Maersk Line>",
  "estimated_cost_usd": <realistic total cost as a number>,
  "transit_days": <integer — realistic transit time>,
  "recommended_for": "<best use case e.g. perishable herbs under 500kg, urgent orders>",
  "pros": ["<pro 1>", "<pro 2>", "<pro 3>"],
  "cons": ["<con 1>", "<con 2>"],
  "departure_airport": "<MMIA Lagos (LOS) for air/ecommerce | Apapa Port Lagos for sea | Seme Border for road>",
  "ai_recommended": <true for exactly ONE channel that is the best fit, false for others>
}}

Realistic rate guidance:
- Air: USD 8–15/kg from Nigeria. Fast (3–7 days). Best for perishable, aromatic, or high-value herbs.
- Sea: USD 1.5–4/kg (LCL/FCL). Slow (18–45 days). Best for large volumes of dried/processed herbs.
- Road: Only viable for African destinations (Ghana, Benin, Togo, Cameroon). 3–10 days.
  For non-African destinations, set estimated_cost_usd to null and add a "con" about unavailability.
- Ecommerce: DHL/FedEx/UPS parcel. Best under 50 kg. Higher per-kg rate. 4–10 days.
- Mark EXACTLY ONE channel as ai_recommended: true.
- Return only the JSON array.
"""

_RECOMMEND_FREIGHT_PROMPT = """
You are a senior Nigerian export logistics consultant.

A seller has received these freight quotes for shipping herbs:
{quotes}

Herb details:
{herb}

Buyer profile:
{buyer}

Select the SINGLE best freight option and explain your reasoning.

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "recommended_channel": "<air|sea|road|ecommerce>",
  "recommended_carrier": "<carrier name>",
  "reason": "<3-4 sentence explanation considering the herb's perishability, buyer's industry, volume, and cost>",
  "estimated_cost_usd": <number>,
  "transit_days": <integer>,
  "risk_factors": ["<risk 1>", "<risk 2>"],
  "cost_saving_tip": "<one actionable tip to reduce cost or improve this shipment>"
}}
"""

_GENERATE_DOC_PROMPT = """
You are a Nigerian export documentation specialist with expertise in international trade,
NAFDAC certification, and ECOWAS/WTO trade documentation standards.

Generate a complete, professional {doc_type} for this export transaction.

Order details:
{order}

Seller information:
{seller}

Buyer information:
{buyer}

Herb / product details:
{herb}

Document requirements:
{doc_requirements}

Return ONLY a valid JSON object (no markdown, no explanation) containing ALL fields
appropriate for this document type. Use realistic values where exact data is absent
(e.g., standard HS codes for Nigerian herbs under Chapter 12, standard NAFDAC clauses).

The output must be complete and ready for PDF rendering — include every field a bank,
customs office, or freight forwarder would require on this document.
"""

_DOC_TYPE_REQUIREMENTS = {
    "commercial_invoice": """
Required fields:
- invoice_number (format: NM-2025-XXXXX, auto-generate)
- invoice_date (today's date)
- seller: {name, address, nepc_reg_number, bank_name, bank_account, swift_code}
- buyer: {name, address, country, contact_email}
- items: [{description, hs_code, quantity_kg, unit_price_usd, total_usd}]
  (Nigerian herbs HS codes: dried herbs 1211, essential oils 3301, herbal extracts 1302)
- incoterms (from order)
- payment_terms (e.g., "30% advance, 70% against shipping documents")
- total_amount_usd
- currency: "USD"
- country_of_origin: "Nigeria"
- declaration: standard export declaration clause
""",
    "packing_list": """
Required fields:
- packing_list_number (linked to commercial invoice)
- date
- seller and buyer info (name, address)
- packages: [{package_number, description, net_weight_kg, gross_weight_kg, dimensions_cm, quantity}]
- total_packages
- total_net_weight_kg
- total_gross_weight_kg
- shipping_marks (seller initials, destination, package numbers)
- special_handling: any cold-chain or fragile notes
""",
    "certificate_of_origin": """
Required fields (Form A / GSP Certificate of Origin):
- certificate_number
- exporter: {name, address, country: "Nigeria"}
- consignee: {name, address, country}
- transport_details: {departure_date, vessel_or_flight, port_of_loading, port_of_discharge}
- item_number: 1
- marks_and_numbers
- description_of_goods
- hs_tariff_code
- origin_criterion: "WO (Wholly Obtained — Nigerian origin)"
- gross_weight_or_quantity
- invoice_number_and_date
- declaration_by_exporter: standard declaration text
- issuing_authority: "Nigerian Export Promotion Council (NEPC)"
- certification_date
""",
    "customs_declaration": """
Required fields (NCS Form M equivalent):
- form_m_number (auto-generate: FM25XXXXXXXX)
- declaration_date
- applicant: {importer_name, address, country, registration_number}
- supplier: {nigerian_exporter_name, address, nepc_reg, nafdac_reg_if_applicable}
- goods_description
- hs_code
- quantity_kg
- unit_price_usd
- total_fob_value_usd
- country_of_origin: "Nigeria"
- port_of_loading
- port_of_destination
- incoterms
- mode_of_transport
- estimated_arrival_date
- special_conditions: phytosanitary or NAFDAC requirements
- declaration: "I declare that the information provided is accurate to the best of my knowledge"
""",
}

_DEFAULT_DOC_REQUIREMENTS = """
Generate all standard fields appropriate for this export document type.
Include HS codes, regulatory references, and standard clauses as applicable.
Use Nigerian export standards and international trade conventions.
"""

_ANOMALY_DETECT_PROMPT = """
You are an expert international trade logistics monitor specialising in Nigerian herb exports.

Shipment details:
{shipment}

Shipment event timeline (chronological):
{events}

Analyse this shipment for anomalies and risks. Consider:
1. Transit delays — compare current date vs estimated_arrival; is it overdue?
2. Temperature breaches — temperature_breach events for cold-chain herbs are critical.
3. Customs holds — customs_hold events or lack of customs_cleared status after expected clearance.
4. Carrier silence — long gaps between events may indicate a problem.
5. Geographic routing — is the shipment in an expected location for its stage?

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "anomaly_detected": <true|false>,
  "severity": "<none|low|medium|high|critical>",
  "anomaly_type": "<delay|temperature_breach|customs_hold|carrier_silence|geographic_anomaly|none>",
  "summary": "<1-2 sentence summary of the current situation>",
  "details": ["<specific finding 1>", "<specific finding 2>"],
  "estimated_new_delivery_date": "<ISO date YYYY-MM-DD if delayed, null if on track>",
  "recommended_action": "<concrete next step for seller or buyer>",
  "risk_to_cargo": "<description of risk to the herb cargo specifically>"
}}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_gemini_model():
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
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )


def _get_claude_client():
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env.",
        )
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_gemini_json(prompt: str) -> Any:
    model = _get_gemini_model()
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {exc}",
        )
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned non-JSON response: {exc}. Raw: {raw[:300]}",
        )


def _call_claude_json(prompt: str, max_tokens: int = 2000) -> Any:
    client = _get_claude_client()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        )
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned non-JSON response: {exc}. Raw: {raw[:300]}",
        )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_freight_quotes(
    origin_state: str,
    destination_country: str,
    quantity_kg: float,
    herb_type: str,
) -> list[dict[str, Any]]:
    """
    Gemini simulates freight quotes for all 4 channels (air, sea, road, ecommerce).
    Returns a list of 4 dicts, exactly one with ai_recommended=True.
    """
    prompt = _FREIGHT_QUOTES_PROMPT.format(
        origin_state=origin_state,
        destination_country=destination_country,
        quantity_kg=quantity_kg,
        herb_type=herb_type,
    )
    result = _call_gemini_json(prompt)

    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for freight quotes.",
        )

    # Enforce exactly one ai_recommended=True; tie-break by fastest transit
    recommended = [q for q in result if q.get("ai_recommended") is True]
    if len(recommended) != 1:
        for q in result:
            q["ai_recommended"] = False
        if result:
            best = min(
                (q for q in result if isinstance(q.get("transit_days"), int)),
                key=lambda q: q["transit_days"],
                default=result[0],
            )
            best["ai_recommended"] = True

    return result


def recommend_best_freight(
    quotes: list[dict[str, Any]],
    herb: dict[str, Any],
    buyer: dict[str, Any],
) -> dict[str, Any]:
    """
    Claude picks the single best freight option given the herb profile and buyer.
    Returns a dict with recommended_channel, reason, risk_factors, cost_saving_tip.
    """
    prompt = _RECOMMEND_FREIGHT_PROMPT.format(
        quotes=json.dumps(quotes, indent=2),
        herb=json.dumps(herb, indent=2),
        buyer=json.dumps(buyer, indent=2),
    )
    return _call_claude_json(prompt, max_tokens=800)


def generate_shipping_document(
    doc_type: str,
    order: dict[str, Any],
    seller: dict[str, Any],
    buyer: dict[str, Any],
    herb: dict[str, Any],
) -> dict[str, Any]:
    """
    Claude generates a complete, structured export document as JSON ready for PDF rendering.
    Supported doc_type values: commercial_invoice, packing_list, certificate_of_origin,
    customs_declaration, and any ExportDocType enum value.
    """
    requirements = _DOC_TYPE_REQUIREMENTS.get(doc_type, _DEFAULT_DOC_REQUIREMENTS)
    prompt = _GENERATE_DOC_PROMPT.format(
        doc_type=doc_type.replace("_", " ").title(),
        order=json.dumps(order, indent=2),
        seller=json.dumps(seller, indent=2),
        buyer=json.dumps(buyer, indent=2),
        herb=json.dumps(herb, indent=2),
        doc_requirements=requirements,
    )
    return _call_claude_json(prompt, max_tokens=3000)


def detect_shipment_anomaly(
    shipment: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Claude scans the shipment and its event timeline for delays, temperature breaches,
    customs hold risk, and other anomalies. Always returns a safe dict with all keys.
    """
    prompt = _ANOMALY_DETECT_PROMPT.format(
        shipment=json.dumps(shipment, indent=2),
        events=json.dumps(events, indent=2),
    )
    result = _call_claude_json(prompt, max_tokens=800)

    # Ensure all keys are present even if Claude omits some
    result.setdefault("anomaly_detected", False)
    result.setdefault("severity", "none")
    result.setdefault("anomaly_type", "none")
    result.setdefault("summary", "No anomalies detected.")
    result.setdefault("details", [])
    result.setdefault("estimated_new_delivery_date", None)
    result.setdefault("recommended_action", "Continue monitoring.")
    result.setdefault("risk_to_cargo", "No immediate risk detected.")
    return result
