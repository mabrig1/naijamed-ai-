import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Enum,
    ForeignKey, Integer, Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class TrialStatus(str, enum.Enum):
    submitted = "submitted"
    active = "active"
    completed = "completed"
    withdrawn = "withdrawn"


class ClinicalTrial(Base):
    __tablename__ = "clinical_trials"
    __table_args__ = (
        CheckConstraint(
            "patient_count IS NULL OR patient_count > 0",
            name="ck_trial_patient_count_positive",
        ),
        CheckConstraint(
            "effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 100)",
            name="ck_trial_effectiveness_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    herb_id: Mapped[int] = mapped_column(
        ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    researcher_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    study_title: Mapped[str] = mapped_column(Text, nullable=False)
    study_phase: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TrialStatus] = mapped_column(
        Enum(TrialStatus, name="trialstatus"),
        nullable=False,
        default=TrialStatus.submitted,
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    patient_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    effectiveness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    statistical_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    publication_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Cached Claude-generated research summary (populated by /ai-summary endpoint)
    ai_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    herb: Mapped["Herb"] = relationship(back_populates="clinical_trials")
    researcher: Mapped["User | None"] = relationship(
        back_populates="clinical_trials", foreign_keys=[researcher_id]
    )
    outcomes: Mapped[list["PatientOutcome"]] = relationship(
        back_populates="trial", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ClinicalTrial id={self.id} herb_id={self.herb_id} status={self.status.value}>"
