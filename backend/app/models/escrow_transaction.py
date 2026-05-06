from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import EscrowStatus


class EscrowTransaction(Base):
    __tablename__ = "escrow_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("export_orders.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )

    amount_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    held_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    release_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, name="escrowstatus"), nullable=False, default=EscrowStatus.held,
    )

    # Relationships
    order: Mapped["ExportOrder"] = relationship(back_populates="escrow")
