from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import ExportDocType


class ExportDocument(Base):
    __tablename__ = "export_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("export_orders.id", ondelete="CASCADE"), nullable=False, index=True)

    doc_type: Mapped[ExportDocType] = mapped_column(Enum(ExportDocType, name="exportdoctype"), nullable=False)
    document_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    issued_by: Mapped[str | None] = mapped_column(String(300), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    order: Mapped["ExportOrder"] = relationship(back_populates="documents")
