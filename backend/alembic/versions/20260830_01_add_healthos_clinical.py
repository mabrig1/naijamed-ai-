"""add Mabrig HealthOS clinical workflow tables

Revision ID: 20260830_01
Revises: c329d61de11c
Create Date: 2026-08-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260830_01"
down_revision: Union[str, None] = "c329d61de11c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider_type", sa.String(32), nullable=False, server_default="doctor"),
        sa.Column("license_number", sa.String(100), nullable=False, unique=True),
        sa.Column("licensing_body", sa.String(100), nullable=False, server_default="MDCN"),
        sa.Column("specialties", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(100)),
        sa.Column("lga", sa.String(100)),
        sa.Column("available_online", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("consultation_fee_kobo", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paystack_subaccount_code", sa.String(100)),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_provider_profiles_user_id", "provider_profiles", ["user_id"])
    op.create_index("ix_provider_profiles_verified", "provider_profiles", ["verified"])
    op.create_index("ix_provider_profiles_state", "provider_profiles", ["state"])
    op.create_index("ix_provider_profiles_lga", "provider_profiles", ["lga"])

    op.create_table(
        "clinical_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_doctor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("urgency", sa.String(32), nullable=False, server_default="routine"),
        sa.Column("status", sa.String(32), nullable=False, server_default="triaged"),
        sa.Column("state", sa.String(100)),
        sa.Column("lga", sa.String(100)),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("encryption_key_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clinical_cases_patient_id", "clinical_cases", ["patient_id"])
    op.create_index("ix_clinical_cases_assigned_doctor_id", "clinical_cases", ["assigned_doctor_id"])
    op.create_index("ix_clinical_cases_urgency", "clinical_cases", ["urgency"])
    op.create_index("ix_clinical_cases_status", "clinical_cases", ["status"])

    op.create_table(
        "clinical_consultations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("clinical_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount_kobo", sa.Integer(), nullable=False),
        sa.Column("platform_fee_kobo", sa.Integer(), nullable=False),
        sa.Column("provider_net_kobo", sa.Integer(), nullable=False),
        sa.Column("payment_reference", sa.String(120), unique=True),
        sa.Column("payment_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("consultation_status", sa.String(32), nullable=False, server_default="awaiting_payment"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clinical_consultations_case_id", "clinical_consultations", ["case_id"])
    op.create_index("ix_clinical_consultations_payment_reference", "clinical_consultations", ["payment_reference"])

    op.create_table(
        "clinical_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("clinical_cases.id", ondelete="SET NULL")),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_clinical_audit_logs_case_id", "clinical_audit_logs", ["case_id"])
    op.create_index("ix_clinical_audit_logs_actor_user_id", "clinical_audit_logs", ["actor_user_id"])
    op.create_index("ix_clinical_audit_logs_action", "clinical_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("clinical_audit_logs")
    op.drop_table("clinical_consultations")
    op.drop_table("clinical_cases")
    op.drop_table("provider_profiles")
