from typing import Any

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# HS Code lookup
# ---------------------------------------------------------------------------

class HSCodeResponse(BaseModel):
    herb_name: str
    scientific_name: str | None = None
    common_forms: list[str] = []
    queried_form: str | None = None
    hs_code: str
    hs_code_processed: str | None = None
    hs_chapter: str | None = None
    description: str | None = None
    duty_rate_eu_percent: float | None = None
    duty_rate_us_percent: float | None = None
    duty_rate_china_percent: float | None = None
    gsp_eligible: bool = True
    agoa_eligible: bool = True
    notes: str | None = None
    export_restrictions: bool = False
    certifications_required: list[str] = []
    source: str  # "seed_table" | "ai_generated"


# ---------------------------------------------------------------------------
# Duties calculator
# ---------------------------------------------------------------------------

class DutiesCalculatorRequest(BaseModel):
    hs_code: str
    destination_country: str
    fob_value_usd: float
    freight_cost_usd: float = 0.0
    insurance_cost_usd: float = 0.0

    model_config = {"str_strip_whitespace": True}

    @field_validator("fob_value_usd")
    @classmethod
    def positive_fob(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("fob_value_usd must be greater than 0")
        return v


class DutyCostLine(BaseModel):
    label: str
    rate_percent: float | None = None
    amount_usd: float


class DutiesCalculatorResponse(BaseModel):
    hs_code: str
    destination_country: str
    fob_value_usd: float
    freight_cost_usd: float
    insurance_cost_usd: float
    cif_value_usd: float
    duty_rate_percent: float
    duty_amount_usd: float
    vat_rate_percent: float | None = None
    vat_amount_usd: float | None = None
    other_fees: list[DutyCostLine] = []
    anti_dumping_percent: float | None = None
    anti_dumping_amount_usd: float | None = None
    total_landed_cost_usd: float
    gsp_preference_available: bool
    gsp_duty_rate_percent: float | None = None
    gsp_savings_usd: float | None = None
    notes: str | None = None
    disclaimer: str | None = None


# ---------------------------------------------------------------------------
# Country import requirements
# ---------------------------------------------------------------------------

class CountryRequirementsResponse(BaseModel):
    destination_country: str
    herb: str | None = None
    certifications_required: list[str] = []
    mrls: dict[str, Any] = {}
    labeling_requirements: list[str] = []
    quarantine_rules: list[str] = []
    banned_substances: list[str] = []
    recommended_freight_agents: list[str] = []
    regulatory_bodies: list[str] = []
    notes: str | None = None
    disclaimer: str | None = None


# ---------------------------------------------------------------------------
# Customs chat
# ---------------------------------------------------------------------------

class CustomsChatRequest(BaseModel):
    question: str
    context: dict[str, Any] = {}

    model_config = {"str_strip_whitespace": True}

    @field_validator("question")
    @classmethod
    def non_empty_question(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be empty")
        return v


class CustomsChatResponse(BaseModel):
    question: str
    answer: str
    cited_agencies: list[str] = []
    suggested_next_questions: list[str] = []
    disclaimer: str


# ---------------------------------------------------------------------------
# Herb restrictions
# ---------------------------------------------------------------------------

class HerbRestriction(BaseModel):
    herb_name: str
    scientific_name: str
    restriction_type: str
    countries_affected: list[str] = []
    reason: str
    reference: str | None = None
    export_guidance: str | None = None


class HerbRestrictionsResponse(BaseModel):
    count: int
    restrictions: list[HerbRestriction]
    disclaimer: str


# ---------------------------------------------------------------------------
# Country regulations brief (AI-generated, general)
# ---------------------------------------------------------------------------

class CountryRegulationBriefResponse(BaseModel):
    country: str
    herb: str | None = None
    regulatory_overview: str | None = None
    key_agencies: list[str] = []
    certifications_required: list[str] = []
    mrls: dict[str, Any] = {}
    labeling_requirements: list[str] = []
    quarantine_rules: list[str] = []
    banned_herbs: list[str] = []
    preferred_incoterms: list[str] = []
    notes: str | None = None
    disclaimer: str | None = None


# ---------------------------------------------------------------------------
# Static regulatory guides (Form M, NEPC, CBN)
# ---------------------------------------------------------------------------

class FormMStep(BaseModel):
    step: int
    title: str
    description: str
    requirements: list[str] = []
    responsible_party: str | None = None
    timeline: str | None = None


class FormMFee(BaseModel):
    fee_name: str
    amount: str
    paid_by: str


class FormMGuidanceResponse(BaseModel):
    title: str
    overview: str
    who_needs_it: str
    steps: list[dict[str, Any]]
    required_documents: list[str]
    fees: list[dict[str, Any]]
    processing_time: str
    tips: list[str]
    key_agencies: list[str]
    useful_links: list[str]


class NEPCStep(BaseModel):
    step: int
    title: str
    description: str
    documents: list[str] = []
    fees: str | None = None
    duration: str | None = None


class NEPCContact(BaseModel):
    headquarters: str
    phone: str
    email: str
    website: str
    state_offices: str | None = None


class NEPCGuideResponse(BaseModel):
    title: str
    overview: str
    why_register: list[str]
    steps: list[dict[str, Any]]
    contact: dict[str, Any]
    notes: list[str]


class CBNRepatriationResponse(BaseModel):
    title: str
    overview: str
    requirements: list[dict[str, Any]]
    timeline: str
    penalties: list[str]
    forex_accounts: list[str]
    payment_instruments: list[str]
    tips: list[str]
    key_contacts: dict[str, Any]
