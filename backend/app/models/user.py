import enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base


class UserRole(str, enum.Enum):
    farmer = "farmer"
    researcher = "researcher"
    pharma_company = "pharma_company"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), nullable=False, default=UserRole.researcher
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    farm_listings: Mapped[list["FarmListing"]] = relationship(back_populates="farmer")
    formulations: Mapped[list["DrugFormulation"]] = relationship(
        back_populates="created_by_user", foreign_keys="DrugFormulation.created_by"
    )
    clinical_trials: Mapped[list["ClinicalTrial"]] = relationship(
        back_populates="researcher", foreign_keys="ClinicalTrial.researcher_id"
    )
    compliance_documents: Mapped[list["ComplianceDocument"]] = relationship(back_populates="user")
    subscription: Mapped["Subscription"] = relationship(back_populates="user", uselist=False)
    patient_outcomes: Mapped[list["PatientOutcome"]] = relationship(
        back_populates="logged_by_user", foreign_keys="PatientOutcome.logged_by"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
