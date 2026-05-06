"""
Customs Intelligence — HS code lookup, duties calculator, country requirements,
customs Q&A, herb restrictions, and static regulatory guides.

Route ordering rule (FastAPI): literal/static paths must be declared BEFORE
parameterised siblings at the same depth.
  GET  /hs-code              (static)   → before any /{param}
  GET  /restrictions         (static)   → safe (different prefix from /{country})
  GET  /nepc-guide           (static)   → safe
  GET  /cbn-repatriation     (static)   → safe
  POST /form-m               (POST)     → no GET conflict
  GET  /requirements/{country}   — these two param routes are safe relative to
  GET  /regulations/{country}    — each other (different literal prefix segments)
"""
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.customs import (
    CBNRepatriationResponse,
    CustomsChatRequest,
    CustomsChatResponse,
    DutiesCalculatorRequest,
    FormMGuidanceResponse,
    HerbRestrictionsResponse,
    HSCodeResponse,
    NEPCGuideResponse,
)
from app.services.customs_service import (
    CBN_REPATRIATION_DATA,
    FORM_M_GUIDANCE,
    HERB_RESTRICTIONS,
    NEPC_EXPORT_GUIDE,
    calculate_import_duties,
    customs_chat,
    get_country_import_requirements,
    get_hs_code,
)

router = APIRouter()

_DISCLAIMER = (
    "Always confirm with a licensed customs agent (CAC-registered). "
    "This guidance is for informational purposes only and does not constitute "
    "legal, tax, or regulatory advice."
)


# ── 1. HS Code lookup ─────────────────────────────────────────────────────────

@router.get(
    "/hs-code",
    response_model=HSCodeResponse,
    summary="Look up HS code for a Nigerian herb",
    description=(
        "Returns the correct Harmonized System (HS) code for a Nigerian export herb "
        "in a given form (dried root, oil, extract, etc.). Checks an in-memory seed "
        "table of 50 common herbs first — falls back to Claude AI for unknown herbs."
    ),
    status_code=status.HTTP_200_OK,
)
def lookup_hs_code(
    herb: str = Query(..., description="Herb name, e.g. 'Ginger', 'Moringa', 'Shea Butter'"),
    form: str = Query("dried herb", description="Product form, e.g. 'dried root', 'essential oil', 'extract'"),
    _current_user: User = Depends(get_current_user),
) -> HSCodeResponse:
    result = get_hs_code(herb_name=herb, form=form)
    return HSCodeResponse(
        herb_name=result.get("herb_name", herb),
        scientific_name=result.get("scientific_name"),
        common_forms=result.get("common_forms") or result.get("alternative_codes") or [],
        queried_form=form,
        hs_code=result["hs_code"],
        hs_code_processed=result.get("hs_code_processed") or result.get("hs_code"),
        hs_chapter=result.get("hs_chapter"),
        description=result.get("description"),
        duty_rate_eu_percent=result.get("duty_rate_eu_percent"),
        duty_rate_us_percent=result.get("duty_rate_us_percent"),
        duty_rate_china_percent=result.get("duty_rate_china_percent"),
        gsp_eligible=result.get("gsp_eligible", True),
        agoa_eligible=result.get("agoa_eligible", True),
        notes=result.get("notes") or result.get("classification_notes"),
        export_restrictions=result.get("export_restrictions", False),
        certifications_required=result.get("certifications_required", []),
        source=result.get("source", "ai_generated"),
    )


# ── 2. Duties calculator ──────────────────────────────────────────────────────

@router.post(
    "/duties-calculator",
    summary="Calculate import duties for a destination country",
    description=(
        "Calculates the full landed-cost breakdown for a Nigerian herb shipment: "
        "CIF value, import duty, VAT, port fees, anti-dumping charges, and total "
        "landed cost. Applies GSP/AGOA/EPA preferential rates where applicable."
    ),
    status_code=status.HTTP_200_OK,
)
def duties_calculator(
    body: DutiesCalculatorRequest,
    _current_user: User = Depends(get_current_user),
) -> dict:
    # Compute effective FOB for the AI (it adds its own freight/insurance estimates)
    result = calculate_import_duties(
        hs_code=body.hs_code,
        destination_country=body.destination_country,
        value_usd=body.fob_value_usd,
    )
    result["disclaimer"] = _DISCLAIMER
    return result


# ── 3. Country import requirements ───────────────────────────────────────────

@router.get(
    "/requirements/{destination_country}",
    summary="Import requirements for a destination country",
    description=(
        "Returns certifications, MRL limits, labeling rules, quarantine conditions, "
        "and recommended freight agents for importing a Nigerian herb into a specific country."
    ),
    status_code=status.HTTP_200_OK,
)
def country_requirements(
    destination_country: str,
    herb: str = Query("Nigerian herbs", description="Specific herb or 'Nigerian herbs' for general requirements"),
    _current_user: User = Depends(get_current_user),
) -> dict:
    result = get_country_import_requirements(country=destination_country, herb=herb)
    result["disclaimer"] = _DISCLAIMER
    return result


# ── 4. Customs chat ───────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=CustomsChatResponse,
    summary="AI-powered Nigerian customs Q&A",
    description=(
        "Ask any question about Nigerian export customs procedures. The AI answers "
        "with reference to NCS, NAFDAC, NEPC, NAQS, and CBN regulations, and "
        "suggests relevant follow-up questions."
    ),
    status_code=status.HTTP_200_OK,
)
def customs_chat_endpoint(
    body: CustomsChatRequest,
    _current_user: User = Depends(get_current_user),
) -> CustomsChatResponse:
    result = customs_chat(question=body.question, context=body.context)
    return CustomsChatResponse(
        question=body.question,
        answer=result.get("answer", ""),
        cited_agencies=result.get("cited_agencies", []),
        suggested_next_questions=result.get("suggested_next_questions", []),
        disclaimer=_DISCLAIMER,
    )


# ── 5. Herb restrictions ──────────────────────────────────────────────────────

@router.get(
    "/restrictions",
    response_model=HerbRestrictionsResponse,
    summary="List globally restricted or controlled herbs",
    description=(
        "Returns a curated list of herbs that are banned, heavily controlled, or "
        "require special permits (CITES, NDLEA, etc.) in major export markets. "
        "No authentication required."
    ),
    status_code=status.HTTP_200_OK,
)
def herb_restrictions() -> HerbRestrictionsResponse:
    return HerbRestrictionsResponse(
        count=len(HERB_RESTRICTIONS),
        restrictions=HERB_RESTRICTIONS,
        disclaimer=_DISCLAIMER,
    )


# ── 6. Country regulations brief (AI) ────────────────────────────────────────

@router.get(
    "/regulations/{country}",
    summary="Full regulatory brief for importing herbs into a country",
    description=(
        "AI-generated comprehensive regulatory overview: applicable regulatory bodies, "
        "certifications, MRLs, labeling requirements, quarantine rules, and banned herbs "
        "for the specified destination country. Optionally scoped to a specific herb."
    ),
    status_code=status.HTTP_200_OK,
)
def country_regulations(
    country: str,
    herb: str = Query(None, description="Optional: specific herb to focus the regulatory brief on"),
    _current_user: User = Depends(get_current_user),
) -> dict:
    herb_query = herb or "Nigerian herb exports (general)"
    result = get_country_import_requirements(country=country, herb=herb_query)

    # Shape the response to match CountryRegulationBriefResponse
    return {
        "country": country,
        "herb": herb,
        "regulatory_overview": result.get("special_requirements"),
        "key_agencies": result.get("regulatory_bodies", []),
        "certifications_required": [
            c.get("cert_name") or c if isinstance(c, dict) else c
            for c in result.get("required_certifications", [])
        ],
        "mrls": {
            item.get("substance", f"item_{i}"): item.get("limit_mg_per_kg")
            for i, item in enumerate(result.get("maximum_residue_limits", []))
            if isinstance(item, dict)
        },
        "labeling_requirements": result.get("labeling_rules", []),
        "quarantine_rules": result.get("quarantine_rules", []),
        "banned_herbs": [
            s.get("substance") or s if isinstance(s, dict) else s
            for s in result.get("banned_substances", [])
        ],
        "preferred_incoterms": [],
        "notes": (
            f"Import licence required: {result.get('import_licence_required')}. "
            f"Issued by: {result.get('import_licence_body', 'N/A')}. "
            f"Typical clearance: {result.get('processing_time_days', 'varies')} days."
            if result.get("import_licence_required") is not None
            else result.get("special_requirements")
        ),
        "disclaimer": _DISCLAIMER,
    }


# ── 7. Form M guidance (static) ───────────────────────────────────────────────

@router.post(
    "/form-m",
    response_model=FormMGuidanceResponse,
    summary="CBN / NCS Form M step-by-step guide",
    description=(
        "Returns the complete step-by-step guide for Form M (Nigeria's mandatory import "
        "finance document under the CBN Trade Monitoring System). Useful for sellers who "
        "need to understand their Nigerian buyer's documentation process. "
        "No request body required."
    ),
    status_code=status.HTTP_200_OK,
)
def form_m_guidance() -> FormMGuidanceResponse:
    return FormMGuidanceResponse(**FORM_M_GUIDANCE)


# ── 8. NEPC registration guide (static) ──────────────────────────────────────

@router.get(
    "/nepc-guide",
    response_model=NEPCGuideResponse,
    summary="NEPC export registration guide",
    description=(
        "Returns the complete Nigerian Export Promotion Council (NEPC) registration "
        "guide: all 8 steps from CAC registration through CBN repatriation, including "
        "fees, timelines, contacts, and tips."
    ),
    status_code=status.HTTP_200_OK,
)
def nepc_guide() -> NEPCGuideResponse:
    return NEPCGuideResponse(**NEPC_EXPORT_GUIDE)


# ── 9. CBN repatriation rules (static) ───────────────────────────────────────

@router.get(
    "/cbn-repatriation",
    response_model=CBNRepatriationResponse,
    summary="CBN foreign exchange repatriation requirements",
    description=(
        "Returns CBN rules for repatriating Nigerian herb export proceeds: 90-day window, "
        "NXP form requirements, penalties for non-compliance, accepted payment instruments, "
        "and practical tips for meeting CBN obligations."
    ),
    status_code=status.HTTP_200_OK,
)
def cbn_repatriation() -> CBNRepatriationResponse:
    return CBNRepatriationResponse(**CBN_REPATRIATION_DATA)
