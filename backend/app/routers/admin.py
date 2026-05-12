"""
Admin router — platform statistics, user management, bulk herb import.

All endpoints require admin role.
"""
import csv
import io
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.sanitize import sanitize_medium, sanitize_short
from app.core.security import require_role
from app.models.clinical_trial import ClinicalTrial
from app.models.compliance_document import ComplianceDocument
from app.models.drug_formulation import DrugFormulation
from app.models.escrow_transaction import EscrowTransaction
from app.models.export_enums import EscrowStatus, OrderStatus
from app.models.export_listing import ExportListing
from app.models.export_order import ExportOrder
from app.models.export_price_index import ExportPriceIndex
from app.models.farm_listing import FarmListing
from app.models.global_buyer import GlobalBuyer
from app.models.herb import Herb
from app.models.herb_compound import HerbCompound
from app.models.patient_outcome import PatientOutcome
from app.models.shipment import Shipment
from app.models.user import User, UserRole

router = APIRouter()

_ADMIN = Depends(require_role(UserRole.admin))


# ── Response schemas ──────────────────────────────────────────────────────────

class PlatformStats(BaseModel):
    total_herbs: int
    total_users: int
    total_formulations: int
    published_formulations: int
    total_trials: int
    verified_trials: int
    total_farm_listings: int
    active_listings: int
    total_patient_outcomes: int
    total_compliance_docs: int


class UserAdminRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class RoleUpdateRequest(BaseModel):
    role: UserRole


class BulkImportResult(BaseModel):
    created: int
    skipped: int
    errors: List[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Platform-wide statistics",
)
def get_stats(db: Session = Depends(get_db), _: User = _ADMIN):
    return PlatformStats(
        total_herbs=db.query(Herb).count(),
        total_users=db.query(User).count(),
        total_formulations=db.query(DrugFormulation).count(),
        published_formulations=db.query(DrugFormulation).filter(DrugFormulation.is_published.is_(True)).count(),
        total_trials=db.query(ClinicalTrial).count(),
        verified_trials=db.query(ClinicalTrial).filter(ClinicalTrial.is_verified.is_(True)).count(),
        total_farm_listings=db.query(FarmListing).count(),
        active_listings=db.query(FarmListing).filter(FarmListing.is_available.is_(True)).count(),
        total_patient_outcomes=db.query(PatientOutcome).count(),
        total_compliance_docs=db.query(ComplianceDocument).count(),
    )


@router.get(
    "/users",
    response_model=List[UserAdminRead],
    summary="List all users with role info",
)
def list_users(
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = _ADMIN,
):
    q = db.query(User)
    if role is not None:
        q = q.filter(User.role == role)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    return q.order_by(User.id).offset(skip).limit(limit).all()


@router.patch(
    "/users/{user_id}/role",
    response_model=UserAdminRead,
    summary="Change a user's role",
)
def update_user_role(
    user_id: int,
    body: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = _ADMIN,
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=UserAdminRead,
    summary="Deactivate a user account",
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = _ADMIN,
):
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/herbs/bulk-import",
    response_model=BulkImportResult,
    summary="Import herbs from CSV file",
    description="""
Upload a UTF-8 CSV file with a header row. Required columns:
`name_english`. Optional columns:
`scientific_name`, `name_igbo`, `name_yoruba`, `name_hausa`,
`description`, `region_found`.

Herbs whose `name_english` already exists are skipped (no overwrite).
Max file size: 1 MB.
""",
)
async def bulk_import_herbs(
    file: UploadFile = File(..., description="UTF-8 CSV file"),
    db: Session = Depends(get_db),
    _: User = _ADMIN,
):
    # Guard: content type and size
    if file.content_type not in ("text/csv", "text/plain", "application/csv", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    raw = await file.read()
    if len(raw) > 1_048_576:   # 1 MB
        raise HTTPException(status_code=400, detail="CSV must be ≤ 1 MB")

    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or "name_english" not in reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV must have a 'name_english' column")

    created = 0
    skipped = 0
    errors: List[str] = []

    for row_num, row in enumerate(reader, start=2):   # row 1 = header
        name = (row.get("name_english") or "").strip()
        if not name:
            errors.append(f"Row {row_num}: name_english is empty — skipped")
            continue

        try:
            name = sanitize_short(name)
        except ValueError as exc:
            errors.append(f"Row {row_num}: {exc}")
            continue

        if db.query(Herb).filter(Herb.name_english.ilike(name)).first():
            skipped += 1
            continue

        try:
            herb = Herb(
                name_english=name,
                scientific_name=_clean(row.get("scientific_name"), 255),
                name_igbo=_clean(row.get("name_igbo"), 100),
                name_yoruba=_clean(row.get("name_yoruba"), 100),
                name_hausa=_clean(row.get("name_hausa"), 100),
                description=_clean(row.get("description"), 5000),
                region_found=_clean(row.get("region_found"), 500),
            )
            db.add(herb)
            db.flush()
            created += 1
        except Exception as exc:
            db.rollback()
            errors.append(f"Row {row_num}: {exc}")

    db.commit()
    return BulkImportResult(created=created, skipped=skipped, errors=errors)


def _clean(value: str | None, max_len: int) -> str | None:
    """Strip and sanitize an optional CSV field."""
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    return sanitize_medium(v)[:max_len]


# ── Export Analytics ──────────────────────────────────────────────────────────

class ExportStatsResponse(BaseModel):
    total_listings: int
    active_listings: int
    total_orders: int
    completed_orders: int
    total_export_value_usd: float
    total_escrow_released_usd: float
    total_shipments: int
    total_global_buyers: int
    platform_commission_usd: float
    avg_order_value_usd: float


class TopHerbRow(BaseModel):
    herb_id: int
    herb_name: str
    total_orders: int
    total_quantity_kg: float
    total_value_usd: float
    avg_price_per_kg_usd: float


class TopMarketRow(BaseModel):
    country: str
    total_orders: int
    total_value_usd: float
    buyer_count: int


class RevenueRow(BaseModel):
    period: str          # e.g. "2024-05" (YYYY-MM)
    gross_value_usd: float
    commission_usd: float
    order_count: int


_COMMISSION_RATE = Decimal("0.025")   # 2.5% platform commission on released escrow


@router.get(
    "/export/stats",
    response_model=ExportStatsResponse,
    summary="Export engine overview statistics",
)
def get_export_stats(
    db: Session = Depends(get_db),
    _: User = _ADMIN,
) -> ExportStatsResponse:
    total_listings   = db.query(ExportListing).count()
    # ExportListing uses export_ready as the "available" flag
    active_listings  = db.query(ExportListing).filter(ExportListing.export_ready.is_(True)).count()
    total_orders     = db.query(ExportOrder).count()
    completed_orders = db.query(ExportOrder).filter(
        ExportOrder.order_status == OrderStatus.delivered
    ).count()
    total_shipments  = db.query(Shipment).count()
    total_buyers     = db.query(GlobalBuyer).count()

    # Aggregate from released escrow transactions
    released_sum = (
        db.query(func.coalesce(func.sum(EscrowTransaction.amount_usd), Decimal("0")))
        .filter(EscrowTransaction.status == EscrowStatus.released)
        .scalar() or Decimal("0")
    )
    total_export_value_usd   = float(released_sum)
    platform_commission_usd  = float(released_sum * _COMMISSION_RATE)

    # Average order value: agreed_price_usd × quantity_kg per order
    avg_result = (
        db.query(
            func.avg(ExportOrder.agreed_price_usd * ExportOrder.quantity_kg)
        ).scalar()
    )
    avg_order_value_usd = round(float(avg_result or 0), 2)

    return ExportStatsResponse(
        total_listings=total_listings,
        active_listings=active_listings,
        total_orders=total_orders,
        completed_orders=completed_orders,
        total_export_value_usd=round(total_export_value_usd, 2),
        total_escrow_released_usd=round(total_export_value_usd, 2),
        total_shipments=total_shipments,
        total_global_buyers=total_buyers,
        platform_commission_usd=round(platform_commission_usd, 2),
        avg_order_value_usd=avg_order_value_usd,
    )


@router.get(
    "/export/top-herbs",
    response_model=List[TopHerbRow],
    summary="Top exported herbs by volume and value",
)
def get_top_herbs(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = _ADMIN,
) -> List[TopHerbRow]:
    # Join ExportOrder → ExportListing to get herb_id
    rows = (
        db.query(
            ExportListing.herb_id,
            func.count(ExportOrder.id).label("total_orders"),
            func.coalesce(func.sum(ExportOrder.quantity_kg), 0).label("total_quantity_kg"),
            func.coalesce(
                func.sum(ExportOrder.agreed_price_usd * ExportOrder.quantity_kg), 0
            ).label("total_value_usd"),
            func.coalesce(func.avg(ExportOrder.agreed_price_usd), 0).label("avg_price_per_kg_usd"),
        )
        .join(ExportListing, ExportOrder.listing_id == ExportListing.id)
        .group_by(ExportListing.herb_id)
        .order_by(desc("total_value_usd"))
        .limit(limit)
        .all()
    )

    result = []
    for row in rows:
        herb = db.get(Herb, row.herb_id)
        result.append(TopHerbRow(
            herb_id=row.herb_id,
            herb_name=herb.name_english if herb else f"Herb #{row.herb_id}",
            total_orders=row.total_orders,
            total_quantity_kg=round(float(row.total_quantity_kg), 2),
            total_value_usd=round(float(row.total_value_usd), 2),
            avg_price_per_kg_usd=round(float(row.avg_price_per_kg_usd), 2),
        ))
    return result


@router.get(
    "/export/top-markets",
    response_model=List[TopMarketRow],
    summary="Top destination markets by order value",
)
def get_top_markets(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = _ADMIN,
) -> List[TopMarketRow]:
    rows = (
        db.query(
            ExportOrder.destination_country,
            func.count(ExportOrder.id).label("total_orders"),
            func.coalesce(
                func.sum(ExportOrder.agreed_price_usd * ExportOrder.quantity_kg), 0
            ).label("total_value_usd"),
            func.count(func.distinct(ExportOrder.buyer_id)).label("buyer_count"),
        )
        .filter(ExportOrder.destination_country.isnot(None))
        .group_by(ExportOrder.destination_country)
        .order_by(desc("total_value_usd"))
        .limit(limit)
        .all()
    )

    return [
        TopMarketRow(
            country=row.destination_country,
            total_orders=row.total_orders,
            total_value_usd=round(float(row.total_value_usd), 2),
            buyer_count=row.buyer_count,
        )
        for row in rows
    ]


@router.get(
    "/export/revenue",
    response_model=List[RevenueRow],
    summary="Monthly export revenue and platform commission",
    description=(
        "Returns month-by-month gross export value and NigerFlora platform commission "
        "(2.5% of released escrow). Covers the last N months."
    ),
)
def get_export_revenue(
    months: int = Query(12, ge=1, le=36, description="Number of past months to include"),
    db: Session = Depends(get_db),
    _: User = _ADMIN,
) -> List[RevenueRow]:
    # Group released escrow by YYYY-MM using PostgreSQL to_char
    rows = (
        db.query(
            func.to_char(EscrowTransaction.released_at, "YYYY-MM").label("period"),
            func.sum(EscrowTransaction.amount_usd).label("gross_value"),
            func.count(EscrowTransaction.id).label("order_count"),
        )
        .filter(
            EscrowTransaction.status == EscrowStatus.released,
            EscrowTransaction.released_at.isnot(None),
        )
        .group_by("period")
        .order_by(desc("period"))
        .limit(months)
        .all()
    )

    return [
        RevenueRow(
            period=row.period,
            gross_value_usd=round(float(row.gross_value), 2),
            commission_usd=round(float(row.gross_value) * 0.025, 2),
            order_count=row.order_count,
        )
        for row in rows
    ]
