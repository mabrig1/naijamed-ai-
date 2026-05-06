from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.drug_formulation import FormulationType


# ---------------------------------------------------------------------------
# Generate request / response
# ---------------------------------------------------------------------------

class FormulationGenerateRequest(BaseModel):
    herb_id: int
    target_disease: str
    compound_used: str | None = None
    formulation_type: FormulationType = FormulationType.tablet

    model_config = {"str_strip_whitespace": True}

    @field_validator("target_disease")
    @classmethod
    def disease_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_disease cannot be blank")
        return v


# ---------------------------------------------------------------------------
# CRUD schemas
# ---------------------------------------------------------------------------

class FormulationRead(BaseModel):
    id: int
    herb_id: int
    created_by: int | None
    formulation_type: FormulationType
    target_disease: str | None
    compound_used: str | None

    dosage_suggestion: str | None
    stability_prediction: str | None
    side_effects_prediction: str | None
    ai_notes: str | None

    excipients_needed: list[Any] | None
    manufacturing_process_summary: str | None
    estimated_cost_savings_usd: Decimal | None
    next_steps: list[Any] | None
    disclaimer: str | None

    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FormulationUpdate(BaseModel):
    """Fields a researcher/admin may manually edit after generation."""
    target_disease: str | None = None
    compound_used: str | None = None
    dosage_suggestion: str | None = None
    stability_prediction: str | None = None
    side_effects_prediction: str | None = None
    ai_notes: str | None = None
    excipients_needed: list[Any] | None = None
    manufacturing_process_summary: str | None = None
    estimated_cost_savings_usd: Decimal | None = None
    next_steps: list[Any] | None = None
    disclaimer: str | None = None

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Compare schemas
# ---------------------------------------------------------------------------

class FormulationCompareRequest(BaseModel):
    formulation_id_1: int
    formulation_id_2: int


class FormulationCompareResponse(BaseModel):
    formulation_id_1: int
    formulation_id_2: int
    recommended_id: int
    reasoning: str
    trade_offs: list[str]
    combined_next_steps: list[str]
