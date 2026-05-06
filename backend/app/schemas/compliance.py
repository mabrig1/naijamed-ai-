from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.compliance_document import ComplianceStatus


# ---------------------------------------------------------------------------
# Document CRUD schemas
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    herb_id: int
    document_type: str
    product_type: str | None = None
    product_name: str | None = None
    formulation_id: int | None = None
    nafdac_stage: str | None = None
    content_json: dict[str, Any] = {}

    model_config = {"str_strip_whitespace": True}

    @field_validator("document_type")
    @classmethod
    def doc_type_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("document_type cannot be blank")
        return v


class HerbSummary(BaseModel):
    id: int
    name_english: str
    scientific_name: str | None = None

    model_config = {"from_attributes": True}


class DocumentRead(BaseModel):
    id: int
    user_id: int
    herb_id: int
    formulation_id: int | None
    herb: HerbSummary | None = None

    document_type: str
    product_type: str | None
    product_name: str | None
    content_json: dict[str, Any]
    nafdac_stage: str | None
    status: ComplianceStatus
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    document_type: str | None = None
    product_type: str | None = None
    product_name: str | None = None
    formulation_id: int | None = None
    nafdac_stage: str | None = None
    content_json: dict[str, Any] | None = None

    model_config = {"str_strip_whitespace": True}


class DocumentGenerateRequest(BaseModel):
    """
    Triggers AI auto-fill. product_type overrides the value stored on the document.
    formulation_id, if supplied, takes precedence over any FK already on the document.
    """
    product_type: str | None = None
    formulation_id: int | None = None

    model_config = {"str_strip_whitespace": True}


class DocumentSubmitResponse(BaseModel):
    id: int
    status: ComplianceStatus
    submitted_at: datetime | None
    nafdac_stage: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Checklist schemas
# ---------------------------------------------------------------------------

class ChecklistItem(BaseModel):
    step: int
    title: str
    description: str
    required_documents: list[str]
    estimated_time: str
    tips: list[str] = []


class ComplianceChecklistResponse(BaseModel):
    product_type: str
    total_steps: int
    items: list[ChecklistItem]


# ---------------------------------------------------------------------------
# NAFDAC stages schema (hardcoded — factual regulatory data)
# ---------------------------------------------------------------------------

class NafdacStage(BaseModel):
    stage_number: int
    name: str
    description: str
    key_requirements: list[str]
    typical_duration: str
    fees_approximate: str


class NafdacStagesResponse(BaseModel):
    total_stages: int
    stages: list[NafdacStage]
    general_notes: list[str]


# ---------------------------------------------------------------------------
# Compliance chat schemas
# ---------------------------------------------------------------------------

class ComplianceChatRequest(BaseModel):
    question: str
    context: dict[str, Any] = {}

    model_config = {"str_strip_whitespace": True}

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question cannot be blank")
        return v


class ComplianceChatResponse(BaseModel):
    answer: str
    disclaimer: str
    suggested_next_questions: list[str] = []
