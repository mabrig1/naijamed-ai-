import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, Numeric,
    String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class FormulationType(str, enum.Enum):
    tablet = "tablet"
    syrup = "syrup"
    extract = "extract"
    capsule = "capsule"
    cream = "cream"


class DrugFormulation(Base):
    __tablename__ = "drug_formulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    herb_id: Mapped[int] = mapped_column(
        ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    formulation_type: Mapped[FormulationType] = mapped_column(
        Enum(FormulationType, name="formulationtype"), nullable=False
    )

    # Context fields — what the formulation was generated for
    target_disease: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    compound_used: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # AI-generated fields (existing, renamed for clarity)
    dosage_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    stability_prediction: Mapped[str | None] = mapped_column(Text, nullable=True)
    side_effects_prediction: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extended Claude response fields
    excipients_needed: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    manufacturing_process_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_cost_savings_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    next_steps: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Publishing
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    herb: Mapped["Herb"] = relationship(back_populates="formulations")
    created_by_user: Mapped["User | None"] = relationship(
        back_populates="formulations", foreign_keys=[created_by]
    )

    def __repr__(self) -> str:
        return f"<DrugFormulation id={self.id} herb_id={self.herb_id} type={self.formulation_type.value}>"
