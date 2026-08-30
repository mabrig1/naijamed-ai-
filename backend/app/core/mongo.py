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
    return db
