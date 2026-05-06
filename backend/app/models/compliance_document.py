import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class ComplianceStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    approved = "approved"
    rejected = "rejected"


class ComplianceDocument(Base):
    __tablename__ = "compliance_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    herb_id: Mapped[int] = mapped_column(
        ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Optional link to a specific formulation — AI generation draws on it if present
    formulation_id: Mapped[int | None] = mapped_column(
        ForeignKey("drug_formulations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # document_type: the kind of regulatory document ("product_registration", "label_design", …)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # product_type: the regulatory product category ("herbal medicine", "food supplement", …)
    product_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # product_name: AI-suggested or manually set name for the finished product
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # JSONB gives indexable, queryable storage for flexible NAFDAC form payloads
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    nafdac_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliancestatus"),
        nullable=False,
        default=ComplianceStatus.draft,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="compliance_documents")
    herb: Mapped["Herb"] = relationship(back_populates="compliance_documents")
    formulation: Mapped["DrugFormulation | None"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<ComplianceDocument id={self.id} "
            f"type={self.document_type!r} status={self.status.value}>"
        )
