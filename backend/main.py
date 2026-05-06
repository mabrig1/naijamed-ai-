from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.limiter import limiter

# Must import models before create_all so SQLAlchemy sees every table definition.
from app.models import (  # noqa: F401
    User, Herb, HerbCompound, FarmListing,
    DrugFormulation, ClinicalTrial, PatientOutcome,
    ComplianceDocument, Subscription,
    # Export & Logistics engine
    ExportListing, ExportOrder, Shipment, ShipmentEvent,
    ExportDocument, GlobalBuyer, FreightQuote, ExportPriceIndex, EscrowTransaction,
)
from app.routers import ai, admin, auth, compliance, export_marketplace, farming, formulations, herbs, logistics, payments, research, users
from app.seeds.herbs import seed_herbs


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables and seed reference data on first startup."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_herbs(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="NaijaMed AI API",
    description="AI-powered Nigerian herbal medicine platform — from soil to science to pharmacy.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/auth",         tags=["auth"])
app.include_router(users.router,        prefix="/api/users",        tags=["users"])
app.include_router(herbs.router,        prefix="/api/herbs",        tags=["herbs"])
app.include_router(ai.router,           prefix="/api/ai",           tags=["ai"])
app.include_router(formulations.router, prefix="/api/formulations", tags=["formulations"])
app.include_router(farming.router,      prefix="/api/farming",      tags=["farming"])
app.include_router(payments.router,     prefix="/api/payments",     tags=["payments"])
app.include_router(research.router,     prefix="/api/research",     tags=["research"])
app.include_router(compliance.router,   prefix="/api/compliance",   tags=["compliance"])
app.include_router(admin.router,        prefix="/api/admin",        tags=["admin"])
app.include_router(export_marketplace.router, prefix="/api/export",   tags=["export"])
app.include_router(logistics.router,          prefix="/api/logistics", tags=["logistics"])


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "env": settings.APP_ENV}
