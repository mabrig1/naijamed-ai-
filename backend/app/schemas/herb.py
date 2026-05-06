from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Compound schemas
# ---------------------------------------------------------------------------

class HerbCompoundCreate(BaseModel):
    compound_name: str
    chemical_formula: str | None = None
    medicinal_use: str | None = None
    source_study: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("compound_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("compound_name cannot be blank")
        return v


class HerbCompoundRead(BaseModel):
    id: int
    herb_id: int
    compound_name: str
    chemical_formula: str | None
    medicinal_use: str | None
    source_study: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Herb schemas
# ---------------------------------------------------------------------------

class HerbCreate(BaseModel):
    name_english: str
    scientific_name: str | None = None
    name_igbo: str | None = None
    name_yoruba: str | None = None
    name_hausa: str | None = None
    description: str | None = None
    image_url: str | None = None
    region_found: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("name_english")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name_english cannot be blank")
        return v


class HerbRead(BaseModel):
    """Lightweight herb — used in list responses."""

    id: int
    name_english: str
    scientific_name: str | None
    name_igbo: str | None
    name_yoruba: str | None
    name_hausa: str | None
    description: str | None
    image_url: str | None
    region_found: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HerbDetail(HerbRead):
    """Full herb — includes all compounds. Used in single-herb responses."""

    compounds: list[HerbCompoundRead] = []


class HerbUpdate(BaseModel):
    name_english: str | None = None
    scientific_name: str | None = None
    name_igbo: str | None = None
    name_yoruba: str | None = None
    name_hausa: str | None = None
    description: str | None = None
    image_url: str | None = None
    region_found: str | None = None

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# AI scan / drug-suggestion schemas
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    herb_name: str
    user_description: str = ""

    model_config = {"str_strip_whitespace": True}


class ActiveCompound(BaseModel):
    name: str
    formula: str | None = None
    role: str | None = None


class ScanResponse(BaseModel):
    herb_name: str
    scientific_name: str | None = None
    medicinal_properties: list[str]
    active_compounds: list[ActiveCompound]
    diseases_treated: list[str]
    drug_production_pathways: list[str]
    research_gaps: list[str]
    safety_warnings: list[str]
    raw: dict[str, Any] | None = None


class DrugSuggestionRequest(BaseModel):
    target_disease: str

    model_config = {"str_strip_whitespace": True}


class DrugSuggestionResponse(BaseModel):
    herb_name: str
    scientific_name: str | None = None
    target_disease: str
    feasibility_score: int
    mechanism_of_action: str
    relevant_compounds: list[str]
    production_pathway: str
    clinical_trial_recommendations: list[str]
    regulatory_considerations: str
    estimated_timeline_years: str
    risks: list[str]
