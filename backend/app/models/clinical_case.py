import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ProviderProfile(Base):
    __tablename__ = "provider_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), default="doctor", nullable=False)
    license_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    licensing_body: Mapped[str] = mapped_column(String(100), default="MDCN", nullable=False)
    specialties: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), index=True)
    lga: Mapped[str | None] = mapped_column(String(100), index=True)
    available_online: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consultation_fee_kobo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paystack_subaccount_code: Mapped[str | None] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClinicalCase(Base):
    __tablename__ = "clinical_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    assigned_doctor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    urgency: Mapped[str] = mapped_column(String(32), index=True, default="routine", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="triaged", nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), index=True)
    lga: Mapped[str | None] = mapped_column(String(100), index=True)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ClinicalConsultation(Base):
    __tablename__ = "clinical_consultations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("clinical_cases.id", ondelete="CASCADE"), index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    amount_kobo: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fee_kobo: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_net_kobo: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    payment_status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    consultation_status: Mapped[str] = mapped_column(String(32), default="awaiting_payment", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClinicalAuditLog(Base):
    __tablename__ = "clinical_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("clinical_cases.id", ondelete="SET NULL"), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
