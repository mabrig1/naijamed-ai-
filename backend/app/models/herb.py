from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base


class Herb(Base):
    __tablename__ = "herbs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_english: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    scientific_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    name_igbo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_yoruba: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_hausa: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    region_found: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Compounds cascade-delete with herb (child data, no independent meaning)
    compounds: Mapped[list["HerbCompound"]] = relationship(
        back_populates="herb", cascade="all, delete-orphan"
    )
    # RESTRICT via FK ondelete — formulations/trials/compliance must be cleared first
    farm_listings: Mapped[list["FarmListing"]] = relationship(back_populates="herb")
    formulations: Mapped[list["DrugFormulation"]] = relationship(back_populates="herb")
    clinical_trials: Mapped[list["ClinicalTrial"]] = relationship(back_populates="herb")
    compliance_documents: Mapped[list["ComplianceDocument"]] = relationship(back_populates="herb")
    patient_outcomes: Mapped[list["PatientOutcome"]] = relationship(back_populates="herb")

    def __repr__(self) -> str:
        return f"<Herb id={self.id} name_english={self.name_english!r}>"
