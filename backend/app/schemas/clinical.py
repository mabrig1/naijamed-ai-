from typing import Any

from pydantic import BaseModel, Field, field_validator


class ClinicalTriageRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    duration: str | None = Field(default=None, max_length=200)
    severity: int | None = Field(default=None, ge=1, le=10)
    medical_history: list[str] = Field(default_factory=list, max_length=30)
    medications: list[str] = Field(default_factory=list, max_length=30)
    allergies: list[str] = Field(default_factory=list, max_length=30)
    state: str | None = Field(default=None, max_length=100)
    lga: str | None = Field(default=None, max_length=100)

    @field_validator("medical_history", "medications", "allergies")
    @classmethod
    def trim_list_items(cls, values: list[str]) -> list[str]:
        return [v.strip()[:200] for v in values if v.strip()]


class ClinicalTriageResponse(BaseModel):
    case_id: str
    urgency: str
    emergency: bool
    red_flags: list[str]
    structured_intake: dict[str, Any]
    differential_for_clinician_review: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    referrals: list[dict[str, Any]]
    patient_notice: str
    doctor_handoff_ready: bool = True
    medication_recommendation: None = None


class ProviderProfileCreate(BaseModel):
    license_number: str = Field(min_length=3, max_length=100)
    licensing_body: str = Field(default="MDCN", max_length=100)
    specialties: list[str] = Field(default_factory=list, max_length=20)
    state: str | None = Field(default=None, max_length=100)
    lga: str | None = Field(default=None, max_length=100)
    available_online: bool = True
    consultation_fee_kobo: int = Field(default=0, ge=0, le=100_000_000)
    paystack_subaccount_code: str | None = Field(default=None, max_length=100)


class ConsultationCheckoutRequest(BaseModel):
    case_id: str
    provider_user_id: int
    callback_url: str | None = None


class SMSRequest(BaseModel):
    phone_number: str = Field(min_length=7, max_length=30)
    message: str = Field(min_length=1, max_length=1000)
