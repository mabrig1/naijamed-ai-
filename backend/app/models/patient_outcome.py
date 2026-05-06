"""
PatientOutcome — anonymized clinical observations logged by doctors.

PRIVACY CONTRACT: This model deliberately omits patient_name, patient_id,
date_of_birth, and any other direct identifiers. Only aggregate/statistical
attributes are stored. logged_by tracks the clinician (a User), not the patient.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, Enum, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class AgeGroup(str, enum.Enum):
    child = "child"       # 0–17
    adult = "adult"       # 18–64
    elderly = "elderly"   # 65+


class Sex(str, enum.Enum):
    male = "male"
    female = "female"
    not_disclosed = "not_disclosed"


class OutcomeResult(str, enum.Enum):
    improved = "improved"
    no_change = "no_change"
    worsened = "worsened"
    adverse_reaction = "adverse_reaction"


class PatientOutcome(Base):
    __tablename__ = "patient_outcomes"
    __table_args__ = (
        CheckConstraint(
            "duration_days IS NULL OR duration_days > 0",
            name="ck_outcome_duration_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    herb_id: Mapped[int] = mapped_column(
        ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # SET NULL: outcome records survive if the linked trial is deleted
    trial_id: Mapped[int | None] = mapped_column(
        ForeignKey("clinical_trials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # SET NULL: outcome records survive if the logging clinician's account is removed
    logged_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Anonymized demographic attributes — NO names, NO national IDs, NO DOB
    age_group: Mapped[AgeGroup] = mapped_column(
        Enum(AgeGroup, name="agegroup"), nullable=False
    )
    sex: Mapped[Sex] = mapped_column(
        Enum(Sex, name="sex"), nullable=False, default=Sex.not_disclosed
    )

    condition_treated: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dosage_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    outcome: Mapped[OutcomeResult] = mapped_column(
        Enum(OutcomeResult, name="outcomeresult"), nullable=False, index=True
    )
    # Additional detail for adverse reactions — must remain anonymized
    adverse_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form anonymized clinical notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    herb: Mapped["Herb"] = relationship(back_populates="patient_outcomes")
    trial: Mapped["ClinicalTrial | None"] = relationship(back_populates="outcomes")
    logged_by_user: Mapped["User | None"] = relationship(
        back_populates="patient_outcomes", foreign_keys=[logged_by]
    )

    def __repr__(self) -> str:
        return f"<PatientOutcome id={self.id} herb_id={self.herb_id} outcome={self.outcome.value}>"
