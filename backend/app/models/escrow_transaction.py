"""
EscrowTransaction — tracks the full lifecycle of a buyer-seller escrow payment.

Extended from the original stub to add:
  - gateway / gateway IDs   (which payment processor + their transaction refs)
  - dispute tracking fields  (reason, timestamps, AI recommendation, admin notes)
  - timing fields            (auto_release_at, delivery_confirmed_at)

NOTE: If the escrow_transactions table already exists in your dev DB,
run `DROP TABLE escrow_transactions;` then restart the server so
create_all() can build it fresh with the new columns.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .export_enums import EscrowStatus


class EscrowTransaction(Base):
    __tablename__ = "escrow_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("export_orders.id", ondelete="RESTRICT"),
        nullable=False, unique=True, index=True,
    )

    # ── Core amounts ────────────────────────────────────────────────────────
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)

    # ── Timing ──────────────────────────────────────────────────────────────
    held_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(),
    )
    # Set when buyer explicitly confirms delivery
    delivery_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # Calculated: held_at + 7 days. If buyer hasn't confirmed by this time, auto-release.
    auto_release_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── Status & condition ──────────────────────────────────────────────────
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, name="escrowstatus"),
        nullable=False, default=EscrowStatus.held,
    )
    # Free-text notes (e.g. "auto-released after 7 days", "buyer confirmed delivery")
    release_condition: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Payment gateway ─────────────────────────────────────────────────────
    gateway: Mapped[str | None] = mapped_column(
        String(50), nullable=True,          # "flutterwave" | "stripe"
    )
    gateway_tx_id: Mapped[str | None] = mapped_column(
        String(300), nullable=True, index=True,   # FLW tx_ref / Stripe PaymentIntent ID
    )
    gateway_transfer_id: Mapped[str | None] = mapped_column(
        String(300), nullable=True,         # transfer ref once funds released to seller
    )
    gateway_payment_link: Mapped[str | None] = mapped_column(
        String(500), nullable=True,         # Flutterwave hosted checkout URL
    )

    # ── Dispute tracking ────────────────────────────────────────────────────
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispute_raised_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    dispute_resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    # JSON blob from Claude (advisory only; stored as text for portability)
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human admin's resolution notes and final decision
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    order: Mapped["ExportOrder"] = relationship(back_populates="escrow")
