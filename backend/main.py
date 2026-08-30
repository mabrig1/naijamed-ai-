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
    ClinicalCase, ClinicalConsultation, ClinicalAuditLog, ProviderProfile,
    ExportListing, ExportOrder, Shipment, ShipmentEvent,
    ExportDocument, GlobalBuyer, FreightQuote, ExportPriceIndex, EscrowTransaction,
)
from app.routers import ai, admin, auth, clinical, compliance, customs, escrow, export_marketplace, farming, formulations, herbs, logistics, payments, price_intelligence, research, users
from app.seeds.herbs import seed_herbs
from app.seeds.price_index import seed_price_index
from app.seeds.export_data import seed_export_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_herbs(db)
        seed_price_index(db)
        seed_export_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="Agentic Nigerian healthcare decision-support, telemedicine coordination, clinical scribing and legacy bio-sciences services.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",         tags=["auth"])
app.include_router(users.router,        prefix="/api/users",        tags=["users"])
app.include_router(clinical.router,     prefix="/api/clinical",     tags=["clinical"])
app.include_router(herbs.router,        prefix="/api/herbs",        tags=["legacy-herbs"])
app.include_router(ai.router,           prefix="/api/ai",           tags=["legacy-ai"])
app.include_router(formulations.router, prefix="/api/formulations", tags=["legacy-formulations"])
app.include_router(farming.router,      prefix="/api/farming",      tags=["legacy-farming"])
app.include_router(payments.router,     prefix="/api/payments",     tags=["payments"])
app.include_router(research.router,     prefix="/api/research",     tags=["research"])
app.include_router(compliance.router,   prefix="/api/compliance",   tags=["compliance"])
app.include_router(admin.router,        prefix="/api/admin",        tags=["admin"])
app.include_router(export_marketplace.router, prefix="/api/export", tags=["legacy-export"])
app.include_router(logistics.router, prefix="/api/logistics", tags=["legacy-logistics"])
app.include_router(customs.router, prefix="/api/customs", tags=["legacy-customs"])
app.include_router(price_intelligence.router, prefix="/api/prices", tags=["legacy-prices"])
app.include_router(escrow.router, prefix="/api/escrow", tags=["legacy-escrow"])
app.include_router(escrow.webhook_router, prefix="/api/webhooks", tags=["webhooks"])


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME, "env": settings.APP_ENV, "clinical_engine": "agentic-v2"}
