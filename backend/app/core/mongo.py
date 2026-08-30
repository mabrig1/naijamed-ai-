from __future__ import annotations

from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from .config import settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI is required. Configure your MongoDB Atlas connection string in Vercel Environment Variables.")
    client = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        maxPoolSize=20,
        retryWrites=True,
    )
    client.admin.command("ping")
    return client


@lru_cache(maxsize=1)
def get_db() -> Database:
    db = get_client()[settings.MONGODB_DB]
    # Idempotent index declarations are safe across Vercel cold starts.
    db.users.create_index([("email", ASCENDING)], unique=True, name="uq_users_email")
    db.provider_profiles.create_index([("user_id", ASCENDING)], unique=True, name="uq_provider_user")
    db.provider_profiles.create_index([("license_number", ASCENDING)], unique=True, name="uq_provider_license")
    db.provider_profiles.create_index([("verified", ASCENDING), ("state", ASCENDING), ("lga", ASCENDING)], name="ix_provider_location")
    db.clinical_cases.create_index([("patient_id", ASCENDING), ("created_at", DESCENDING)], name="ix_case_patient")
    db.clinical_cases.create_index([("assigned_doctor_id", ASCENDING), ("created_at", DESCENDING)], name="ix_case_doctor")
    db.clinical_consultations.create_index([("payment_reference", ASCENDING)], unique=True, sparse=True, name="uq_consultation_payment")
    db.clinical_audit_logs.create_index([("case_id", ASCENDING), ("created_at", DESCENDING)], name="ix_audit_case")

    # Research & Discovery Studio
    db.research_service_orders.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_research_orders_user")
    db.research_service_orders.create_index([("payment_status", ASCENDING), ("created_at", DESCENDING)], name="ix_research_orders_payment")
    db.research_service_orders.create_index([("service_id", ASCENDING), ("created_at", DESCENDING)], name="ix_research_orders_service")
    db.polyherbal_synergy_projects.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_synergy_projects_user")
    db.polyherbal_synergy_projects.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="ix_synergy_projects_status")

    # Commercial bioinformatics storefront
    db.research_commerce_orders.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_commerce_orders_user")
    db.research_commerce_orders.create_index([("payment_status", ASCENDING), ("created_at", DESCENDING)], name="ix_commerce_orders_payment")
    db.research_commerce_orders.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="ix_commerce_orders_status")
    db.research_commerce_orders.create_index([("service_id", ASCENDING), ("market", ASCENDING), ("created_at", DESCENDING)], name="ix_commerce_orders_service_market")
    db.research_commerce_orders.create_index([("receipt_number", ASCENDING)], unique=True, sparse=True, name="uq_commerce_receipt")
    db.research_sales_leads.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="ix_research_leads_status")
    db.research_sales_leads.create_index([("email", ASCENDING), ("created_at", DESCENDING)], name="ix_research_leads_email")

    # Competitive Discovery Workbench
    db.discovery_assets.create_index(
        [("user_id", ASCENDING), ("kind", ASCENDING), ("external_id", ASCENDING)],
        unique=True,
        name="uq_discovery_asset",
    )
    db.discovery_assets.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_discovery_assets_user")
    db.discovery_screening_jobs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_screening_jobs_user")
    db.discovery_screening_jobs.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="ix_screening_jobs_status")
    db.discovery_networks.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)], name="ix_discovery_networks_user")
    return db
