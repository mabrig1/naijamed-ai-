from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.farm_listing import FarmListing
from app.models.herb import Herb
from app.models.user import User, UserRole
from app.schemas.farming import (
    FarmListingCreate,
    FarmListingRead,
    FarmListingUpdate,
    InquiryRequest,
    InquiryResponse,
    MarketDemandResponse,
)
from app.services.farming_service import predict_herb_demand

router = APIRouter()

_LISTING_OPTS = [selectinload(FarmListing.herb), selectinload(FarmListing.farmer)]


def _get_listing_or_404(listing_id: int, db: Session) -> FarmListing:
    listing = db.get(FarmListing, listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


def _require_owner_or_admin(listing: FarmListing, current_user: User) -> None:
    if current_user.role != UserRole.admin and listing.farmer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _with_relations(listing_id: int, db: Session) -> FarmListing:
    """Re-fetch a listing with herb + farmer eagerly loaded."""
    return (
        db.query(FarmListing)
        .options(*_LISTING_OPTS)
        .filter(FarmListing.id == listing_id)
        .first()
    )


# ---------------------------------------------------------------------------
# Non-parameterised sub-routes — registered BEFORE /listings/{listing_id}
# ---------------------------------------------------------------------------

@router.get("/my-listings", response_model=List[FarmListingRead])
def my_listings(
    is_available: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.farmer, UserRole.admin)),
):
    """Return the authenticated farmer's own listings."""
    query = (
        db.query(FarmListing)
        .options(*_LISTING_OPTS)
        .filter(FarmListing.farmer_id == current_user.id)
    )
    if is_available is not None:
        query = query.filter(FarmListing.is_available.is_(is_available))
    return query.order_by(FarmListing.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/market-demand", response_model=MarketDemandResponse)
def market_demand(
    season: str = Query(
        "rainy season",
        description="Current or upcoming season (e.g. 'dry season', 'rainy season', 'harmattan')",
    ),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """AI-powered demand forecast built from live marketplace supply data."""
    rows = (
        db.query(
            Herb.name_english.label("herb_name"),
            func.count(FarmListing.id).label("listing_count"),
            func.sum(FarmListing.quantity_kg).label("total_quantity_kg"),
            func.avg(FarmListing.price_per_kg).label("avg_price_per_kg"),
        )
        .join(FarmListing, FarmListing.herb_id == Herb.id, isouter=True)
        .filter(FarmListing.is_available.is_(True))
        .group_by(Herb.name_english)
        .all()
    )

    aggregated = [
        {
            "herb_name": row.herb_name,
            "listing_count": row.listing_count or 0,
            "total_quantity_kg": float(row.total_quantity_kg or 0),
            "avg_price_per_kg": float(row.avg_price_per_kg or 0),
        }
        for row in rows
    ]

    result = predict_herb_demand(season=season, current_listings=aggregated)

    return MarketDemandResponse(
        season=season,
        top_herbs=result.get("top_herbs", []),
        planting_recommendations=result.get("planting_recommendations", []),
        price_forecasts=result.get("price_forecasts", []),
        quality_improvement_tips=result.get("quality_improvement_tips", []),
    )


# ---------------------------------------------------------------------------
# Listings — list + create
# ---------------------------------------------------------------------------

@router.get("/listings", response_model=List[FarmListingRead])
def list_listings(
    herb_id: Optional[int] = Query(None, description="Filter by herb"),
    region: Optional[str] = Query(None, description="Partial match on location"),
    min_price: Optional[Decimal] = Query(None, description="Min price per kg (NGN)"),
    max_price: Optional[Decimal] = Query(None, description="Max price per kg (NGN)"),
    available_only: bool = Query(True, description="Show only available listings"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(FarmListing).options(*_LISTING_OPTS)

    if herb_id is not None:
        query = query.filter(FarmListing.herb_id == herb_id)
    if region:
        query = query.filter(FarmListing.location.ilike(f"%{region}%"))
    if min_price is not None:
        query = query.filter(FarmListing.price_per_kg >= min_price)
    if max_price is not None:
        query = query.filter(FarmListing.price_per_kg <= max_price)
    if available_only:
        query = query.filter(FarmListing.is_available.is_(True))

    return query.order_by(FarmListing.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/listings", response_model=FarmListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    body: FarmListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.farmer, UserRole.admin)),
):
    if not db.get(Herb, body.herb_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")

    listing = FarmListing(farmer_id=current_user.id, **body.model_dump())
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return _with_relations(listing.id, db)


# ---------------------------------------------------------------------------
# Listings — single-item operations (parameterised)
# ---------------------------------------------------------------------------

@router.get("/listings/{listing_id}", response_model=FarmListingRead)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    listing = _with_relations(listing_id, db)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


@router.put("/listings/{listing_id}", response_model=FarmListingRead)
def update_listing(
    listing_id: int,
    body: FarmListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(listing_id, db)
    _require_owner_or_admin(listing, current_user)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    db.commit()
    db.refresh(listing)
    return _with_relations(listing.id, db)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(listing_id, db)
    _require_owner_or_admin(listing, current_user)
    db.delete(listing)
    db.commit()


@router.post("/listings/{listing_id}/inquire", response_model=InquiryResponse)
def inquire(
    listing_id: int,
    body: InquiryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.pharma_company, UserRole.researcher, UserRole.admin)
    ),
):
    """
    Pharma company or researcher sends a purchase inquiry.
    In production this triggers an email/notification to the farmer;
    here it returns a structured acknowledgment.
    """
    listing = _with_relations(listing_id, db)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if not listing.is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This listing is no longer available",
        )

    herb_name = listing.herb.name_english if listing.herb else "Unknown herb"
    farmer_name = listing.farmer.full_name if listing.farmer else "Unknown farmer"

    return InquiryResponse(
        listing_id=listing_id,
        herb_name=herb_name,
        farmer_name=farmer_name,
        message=body.message,
        quantity_kg_requested=body.quantity_kg_requested,
        status="inquiry_received",
    )
