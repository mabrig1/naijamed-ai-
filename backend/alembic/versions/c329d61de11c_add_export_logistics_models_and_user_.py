"""add export logistics models and user token_version

Revision ID: c329d61de11c
Revises:
Create Date: 2026-05-06

Changes:
- users.token_version (INT NOT NULL DEFAULT 0) — refresh-token rotation
- export_listings, export_orders, shipments, shipment_events
- export_documents, global_buyers, freight_quotes
- export_price_index, escrow_transactions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c329d61de11c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create all new PostgreSQL enum types first ────────────────────────────
    _enums = [
        ("herbgrade",         ["A", "B", "C", "premium"]),
        ("packagingtype",     ["bulk_bag", "vacuum_sealed", "drum", "carton"]),
        ("freightchannel",    ["air", "sea", "road", "ecommerce"]),
        ("incoterms",         ["FOB", "CIF", "EXW", "DDP", "DAP"]),
        ("paymentmethod",     ["paystack", "flutterwave", "stripe", "paypal", "swift"]),
        ("paymentstatus",     ["pending", "escrow_held", "released", "refunded"]),
        ("orderstatus",       ["placed", "confirmed", "processing", "shipped",
                               "in_transit", "cleared_customs", "delivered", "disputed"]),
        ("shipmenteventtype", ["departure", "arrival", "customs_hold", "delay",
                               "customs_cleared", "delivered", "temperature_breach"]),
        ("exportdoctype",     ["commercial_invoice", "packing_list", "bill_of_lading",
                               "airway_bill", "certificate_of_origin",
                               "phytosanitary_certificate", "nafdac_export_cert",
                               "nepc_certificate", "customs_declaration"]),
        ("buyertype",         ["pharma_company", "herbal_retailer", "cosmetics_brand",
                               "research_institution", "distributor", "individual"]),
        ("marketregion",      ["europe", "north_america", "asia", "middle_east", "africa"]),
        ("escrowstatus",      ["held", "released", "refunded", "disputed"]),
    ]
    for name, values in _enums:
        postgresql.ENUM(*values, name=name, create_type=True).create(op.get_bind())

    # ── users: token_version for refresh-token rotation ───────────────────────
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))

    # ── export_listings ───────────────────────────────────────────────────────
    op.create_table(
        "export_listings",
        sa.Column("id",                  sa.Integer(),            primary_key=True),
        sa.Column("herb_id",             sa.Integer(),            sa.ForeignKey("herbs.id",  ondelete="RESTRICT"), nullable=False),
        sa.Column("seller_id",           sa.Integer(),            sa.ForeignKey("users.id",  ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_kg",         sa.Numeric(12, 3),       nullable=False),
        sa.Column("price_per_kg_usd",    sa.Numeric(10, 4),       nullable=False),
        sa.Column("minimum_order_kg",    sa.Numeric(10, 3),       nullable=False, server_default="1"),
        sa.Column("herb_grade",          sa.Enum(name="herbgrade",      create_type=False), nullable=False),
        sa.Column("packaging_type",      sa.Enum(name="packagingtype",  create_type=False), nullable=False),
        sa.Column("available_from_date", sa.Date(),               nullable=True),
        sa.Column("certificate_nafdac",  sa.String(255),          nullable=True),
        sa.Column("certificate_naqs",    sa.String(255),          nullable=True),
        sa.Column("certificate_nepc",    sa.String(255),          nullable=True),
        sa.Column("is_organic",          sa.Boolean(),            nullable=False, server_default="false"),
        sa.Column("origin_state",        sa.String(100),          nullable=True),
        sa.Column("origin_lga",          sa.String(100),          nullable=True),
        sa.Column("farm_gps_lat",        sa.Numeric(9, 6),        nullable=True),
        sa.Column("farm_gps_lng",        sa.Numeric(9, 6),        nullable=True),
        sa.Column("export_ready",        sa.Boolean(),            nullable=False, server_default="false"),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_export_listings_id",        "export_listings", ["id"])
    op.create_index("ix_export_listings_herb_id",   "export_listings", ["herb_id"])
    op.create_index("ix_export_listings_seller_id", "export_listings", ["seller_id"])

    # ── export_orders ─────────────────────────────────────────────────────────
    op.create_table(
        "export_orders",
        sa.Column("id",                      sa.Integer(),        primary_key=True),
        sa.Column("listing_id",              sa.Integer(),        sa.ForeignKey("export_listings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("buyer_id",                sa.Integer(),        sa.ForeignKey("users.id",           ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_kg",             sa.Numeric(12, 3),   nullable=False),
        sa.Column("agreed_price_usd",        sa.Numeric(14, 4),   nullable=False),
        sa.Column("freight_channel",         sa.Enum(name="freightchannel", create_type=False), nullable=False),
        sa.Column("destination_country",     sa.String(100),      nullable=False),
        sa.Column("destination_port",        sa.String(200),      nullable=True),
        sa.Column("incoterms",               sa.Enum(name="incoterms",      create_type=False), nullable=False),
        sa.Column("payment_method",          sa.Enum(name="paymentmethod",  create_type=False), nullable=False),
        sa.Column("payment_status",          sa.Enum(name="paymentstatus",  create_type=False), nullable=False, server_default="pending"),
        sa.Column("order_status",            sa.Enum(name="orderstatus",    create_type=False), nullable=False, server_default="placed"),
        sa.Column("estimated_delivery_date", sa.Date(),           nullable=True),
        sa.Column("created_at",              sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_export_orders_id",         "export_orders", ["id"])
    op.create_index("ix_export_orders_listing_id", "export_orders", ["listing_id"])
    op.create_index("ix_export_orders_buyer_id",   "export_orders", ["buyer_id"])

    # ── shipments ─────────────────────────────────────────────────────────────
    op.create_table(
        "shipments",
        sa.Column("id",                  sa.Integer(),       primary_key=True),
        sa.Column("order_id",            sa.Integer(),       sa.ForeignKey("export_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tracking_number",     sa.String(100),     nullable=True),
        sa.Column("carrier_name",        sa.String(200),     nullable=True),
        sa.Column("freight_channel",     sa.Enum(name="freightchannel", create_type=False), nullable=False),
        sa.Column("origin_port",         sa.String(200),     nullable=True),
        sa.Column("destination_port",    sa.String(200),     nullable=True),
        sa.Column("vessel_or_flight",    sa.String(200),     nullable=True),
        sa.Column("container_number",    sa.String(100),     nullable=True),
        sa.Column("departure_date",      sa.Date(),          nullable=True),
        sa.Column("estimated_arrival",   sa.Date(),          nullable=True),
        sa.Column("actual_arrival",      sa.Date(),          nullable=True),
        sa.Column("current_status",      sa.String(200),     nullable=True),
        sa.Column("current_location",    sa.String(300),     nullable=True),
        sa.Column("temperature_celsius", sa.Numeric(5, 2),   nullable=True),
        sa.Column("last_gps_lat",        sa.Numeric(9, 6),   nullable=True),
        sa.Column("last_gps_lng",        sa.Numeric(9, 6),   nullable=True),
        sa.Column("customs_cleared",     sa.Boolean(),       nullable=False, server_default="false"),
        sa.Column("created_at",          sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shipments_id",              "shipments", ["id"])
    op.create_index("ix_shipments_order_id",        "shipments", ["order_id"])
    op.create_index("ix_shipments_tracking_number", "shipments", ["tracking_number"])

    # ── shipment_events ───────────────────────────────────────────────────────
    op.create_table(
        "shipment_events",
        sa.Column("id",              sa.Integer(),   primary_key=True),
        sa.Column("shipment_id",     sa.Integer(),   sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type",      sa.Enum(name="shipmenteventtype", create_type=False), nullable=False),
        sa.Column("location",        sa.String(300), nullable=True),
        sa.Column("description",     sa.Text(),      nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_shipment_events_id",          "shipment_events", ["id"])
    op.create_index("ix_shipment_events_shipment_id", "shipment_events", ["shipment_id"])

    # ── export_documents ──────────────────────────────────────────────────────
    op.create_table(
        "export_documents",
        sa.Column("id",               sa.Integer(),    primary_key=True),
        sa.Column("order_id",         sa.Integer(),    sa.ForeignKey("export_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type",         sa.Enum(name="exportdoctype", create_type=False), nullable=False),
        sa.Column("document_url",     sa.String(1000), nullable=True),
        sa.Column("issued_by",        sa.String(300),  nullable=True),
        sa.Column("issue_date",       sa.Date(),       nullable=True),
        sa.Column("expiry_date",      sa.Date(),       nullable=True),
        sa.Column("is_ai_generated",  sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("is_verified",      sa.Boolean(),    nullable=False, server_default="false"),
    )
    op.create_index("ix_export_documents_id",       "export_documents", ["id"])
    op.create_index("ix_export_documents_order_id", "export_documents", ["order_id"])

    # ── global_buyers ─────────────────────────────────────────────────────────
    op.create_table(
        "global_buyers",
        sa.Column("id",                            sa.Integer(),    primary_key=True),
        sa.Column("user_id",                       sa.Integer(),    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("company_name",                  sa.String(300),  nullable=True),
        sa.Column("country",                       sa.String(100),  nullable=False),
        sa.Column("city",                          sa.String(100),  nullable=True),
        sa.Column("buyer_type",                    sa.Enum(name="buyertype",  create_type=False), nullable=False),
        sa.Column("preferred_herbs",               postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("preferred_volume_kg_per_month", sa.Numeric(12, 3), nullable=True),
        sa.Column("preferred_incoterms",           sa.Enum(name="incoterms", create_type=False), nullable=True),
        sa.Column("verified",                      sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("created_at",                    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_global_buyers_id",      "global_buyers", ["id"])
    op.create_index("ix_global_buyers_user_id", "global_buyers", ["user_id"])

    # ── freight_quotes ────────────────────────────────────────────────────────
    op.create_table(
        "freight_quotes",
        sa.Column("id",              sa.Integer(),    primary_key=True),
        sa.Column("listing_id",      sa.Integer(),    sa.ForeignKey("export_listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("buyer_id",        sa.Integer(),    sa.ForeignKey("global_buyers.id",   ondelete="CASCADE"), nullable=False),
        sa.Column("freight_channel", sa.Enum(name="freightchannel", create_type=False), nullable=False),
        sa.Column("carrier_name",    sa.String(200),  nullable=True),
        sa.Column("origin",          sa.String(300),  nullable=False),
        sa.Column("destination",     sa.String(300),  nullable=False),
        sa.Column("quantity_kg",     sa.Numeric(12, 3), nullable=False),
        sa.Column("quoted_cost_usd", sa.Numeric(14, 4), nullable=False),
        sa.Column("transit_days",    sa.Integer(),    nullable=True),
        sa.Column("valid_until",     sa.Date(),       nullable=True),
        sa.Column("ai_recommended",  sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_freight_quotes_id",         "freight_quotes", ["id"])
    op.create_index("ix_freight_quotes_listing_id", "freight_quotes", ["listing_id"])
    op.create_index("ix_freight_quotes_buyer_id",   "freight_quotes", ["buyer_id"])

    # ── export_price_index ────────────────────────────────────────────────────
    op.create_table(
        "export_price_index",
        sa.Column("id",               sa.Integer(),    primary_key=True),
        sa.Column("herb_id",          sa.Integer(),    sa.ForeignKey("herbs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("market_region",    sa.Enum(name="marketregion", create_type=False), nullable=False),
        sa.Column("price_per_kg_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("currency",         sa.String(10),   nullable=False, server_default="USD"),
        sa.Column("recorded_date",    sa.Date(),       nullable=False),
        sa.Column("source",           sa.String(500),  nullable=True),
    )
    op.create_index("ix_export_price_index_id",      "export_price_index", ["id"])
    op.create_index("ix_export_price_index_herb_id", "export_price_index", ["herb_id"])

    # ── escrow_transactions ───────────────────────────────────────────────────
    op.create_table(
        "escrow_transactions",
        sa.Column("id",                sa.Integer(),    primary_key=True),
        sa.Column("order_id",          sa.Integer(),    sa.ForeignKey("export_orders.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("amount_usd",        sa.Numeric(14, 4), nullable=False),
        sa.Column("held_at",           sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("released_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_condition", sa.Text(),       nullable=True),
        sa.Column("status",            sa.Enum(name="escrowstatus", create_type=False), nullable=False, server_default="held"),
    )
    op.create_index("ix_escrow_transactions_id",       "escrow_transactions", ["id"])
    op.create_index("ix_escrow_transactions_order_id", "escrow_transactions", ["order_id"])


def downgrade() -> None:
    op.drop_table("escrow_transactions")
    op.drop_table("export_price_index")
    op.drop_table("freight_quotes")
    op.drop_table("global_buyers")
    op.drop_table("export_documents")
    op.drop_table("shipment_events")
    op.drop_table("shipments")
    op.drop_table("export_orders")
    op.drop_table("export_listings")
    op.drop_column("users", "token_version")

    for name in ("escrowstatus", "marketregion", "buyertype", "exportdoctype",
                 "shipmenteventtype", "orderstatus", "paymentstatus", "paymentmethod",
                 "incoterms", "freightchannel", "packagingtype", "herbgrade"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
