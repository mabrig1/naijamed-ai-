from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.clinical_trial import TrialStatus
from app.models.patient_outcome import AgeGroup, OutcomeResult, Sex


# ---------------------------------------------------------------------------
# Shared nested summaries
# ---------------------------------------------------------------------------

class HerbSummary(BaseModel):
    id: int
    name_english: str
    scientific_name: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Clinical trial schemas
# ---------------------------------------------------------------------------

class TrialCreate(BaseModel):
    herb_id: int
    study_title: str
    study_phase: str | None = None
    methodology: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    patient_count: int | None = None
    outcome_summary: str | None = None
    effectiveness_score: Decimal | None = None
    findings: str | None = None
    statistical_data: dict[str, Any] | None = None
    publication_doi: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("study_title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("study_title cannot be blank")
        return v

    @field_validator("effectiveness_score")
    @classmethod
    def score_range(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("effectiveness_score must be between 0 and 100")
        return v

    @field_validator("patient_count")
    @classmethod
    def patient_count_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("patient_count must be greater than 0")
        return v


class TrialRead(BaseModel):
    id: int
    herb_id: int
    researcher_id: int | None
    herb: HerbSummary | None = None

    study_title: str
    study_phase: str | None
    methodology: str | None
    status: TrialStatus

    start_date: date | None
    end_date: date | None
    patient_count: int | None
    outcome_summary: str | None
    effectiveness_score: Decimal | None
    findings: str | None
    statistical_data: dict[str, Any] | None
    publication_doi: str | None

    is_verified: bool
    ai_summary: dict[str, Any] | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrialUpdate(BaseModel):
    study_title: str | None = None
    study_phase: str | None = None
    methodology: str | None = None
    status: TrialStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    patient_count: int | None = None
    outcome_summary: str | None = None
    effectiveness_score: Decimal | None = None
    findings: str | None = None
    statistical_data: dict[str, Any] | None = None
    publication_doi: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("effectiveness_score")
    @classmethod
    def score_range(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("effectiveness_score must be between 0 and 100")
        return v

    @field_validator("patient_count")
    @classmethod
    def patient_count_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("patient_count must be greater than 0")
        return v


# ---------------------------------------------------------------------------
# Patient outcome schemas — NO patient-identifying fields in read schema
# ---------------------------------------------------------------------------

class OutcomeCreate(BaseModel):
    herb_id: int
    trial_id: int | None = None
    age_group: AgeGroup
    sex: Sex = Sex.not_disclosed
    condition_treated: str
    dosage_used: str | None = None
    duration_days: int | None = None
    outcome: OutcomeResult
    adverse_details: str | None = None
    notes: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("condition_treated")
    @classmethod
    def condition_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("condition_treated cannot be blank")
        return v

    @field_validator("duration_days")
    @classmethod
    def duration_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("duration_days must be greater than 0")
        return v


class OutcomeRead(BaseModel):
    """
    Anonymized read schema. logged_by is intentionally excluded.
    No patient names, IDs, or birthdates are ever stored or returned.
    """
    id: int
    herb_id: int
    trial_id: int | None
    age_group: AgeGroup
    sex: Sex
    condition_treated: str
    dosage_used: str | None
    duration_days: int | None
    outcome: OutcomeResult
    adverse_details: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# AI response schemas
# ---------------------------------------------------------------------------

class TrialSummaryResponse(BaseModel):
    trial_id: int
    plain_language_summary: str
    statistical_significance: str
    confidence_level: str
    literature_comparison: str
    recommended_next_steps: list[str]


class EvidenceScoreResponse(BaseModel):
    herb_id: int
    herb_name: str
    evidence_score: int
    verdict: str
    key_findings: list[str]
    safety_signals: list[str]
    trial_count: int
    verified_trial_count: int
