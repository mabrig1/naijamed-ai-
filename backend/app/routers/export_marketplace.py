"""
Export Marketplace — herb export listings, global buyer registry, and
AI-powered buyer/seller matchmaking.

Route ordering rule (FastAPI): every literal sub-path (/my, /all, /verify-certs,
/register, /my-profile) must be declared BEFORE its sibling /{id} param route.
"""
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.export_listing import ExportListing
from app.models.export_enums import HerbGrade, PackagingType
from app.models.global_buyer import GlobalBuyer
from app.models.herb import Herb
from app.models.user import User, UserRole
from app.schemas.export_marketplace import (
    BuyerMatchResponse,
    BuyerMatchResult,
    CertVerifyBody,
    ExportListingCreate,
    ExportListingRead,
    ExportListingUpdate,
    GlobalBuyerCreate,
    GlobalBuyerRead,
    GlobalBuyerUpdate,
    ListingMatchResponse,
    ListingMatchResult,
    MatchInterestRequest,
    TradeIntroductionResponse,
)
from app.services.export_matching_service import (
    generate_trade_introduction,
    match_buyers_to_herb,
    match_listings_to_buyer,
)

router = APIRouter()

_ADMIN = Depends(require_role(UserRole.admin))

# Max buyers/listings sent to the AI to keep prompt size bounded
_AI_CANDIDATE_LIMIT = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_listing_or_404(listing_id: int, db: Session) -> ExportListing:
    listing = db.get(ExportListing, listing_id)
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export listing not found")
    return listing


def _get_buyer_or_404(buyer_id: int, db: Session) -> GlobalBuyer:
    buyer = db.get(GlobalBuyer, buyer_id)
    if not buyer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer profile not found")
    return buyer


def _listing_to_dict(listing: ExportListing) -> dict[str, Any]:
    """Flat dict representation used by the AI matching service."""
    return {
        "id": listing.id,
        "herb_name": listing.herb.name_english if listing.herb else "",
        "scientific_name": listing.herb.scientific_name if listing.herb else None,
        "quantity_kg": str(listing.quantity_kg),
        "price_per_kg_usd": str(listing.price_per_kg_usd),
        "minimum_order_kg": str(listing.minimum_order_kg),
        "herb_grade": listing.herb_grade.value if listing.herb_grade else None,
        "packaging_type": listing.packaging_type.value if listing.packaging_type else None,
        "is_organic": listing.is_organic,
        "origin_state": listing.origin_state,
        "certificate_nafdac": listing.certificate_nafdac,
        "certificate_naqs": listing.certificate_naqs,
        "certificate_nepc": listing.certificate_nepc,
        "export_ready": listing.export_ready,
    }


def _buyer_to_dict(buyer: GlobalBuyer) -> dict[str, Any]:
    return {
        "id": buyer.id,
        "company_name": buyer.company_name,
        "country": buyer.country,
        "city": buyer.city,
        "buyer_type": buyer.buyer_type.value if buyer.buyer_type else None,
        "preferred_herbs": buyer.preferred_herbs or [],
        "preferred_volume_kg_per_month": str(buyer.preferred_volume_kg_per_month) if buyer.preferred_volume_kg_per_month else None,
        "preferred_incoterms": buyer.preferred_incoterms.value if buyer.preferred_incoterms else None,
        "verified": buyer.verified,
    }


def _load_listing_with_relations(listing_id: int, db: Session) -> ExportListing:
    listing = (
        db.query(ExportListing)
        .options(selectinload(ExportListing.herb), selectinload(ExportListing.seller))
        .filter(ExportListing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export listing not found")
    return listing


# ===========================================================================
# EXPORT LISTINGS — seller side
# ===========================================================================

# ── IMPORTANT: /my must be declared before /{id} ────────────────────────────

@router.get(
    "/listings/my",
    response_model=List[ExportListingRead],
    summary="Seller's own export listings",
)
def my_listings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ExportListing)
        .options(selectinload(ExportListing.herb), selectinload(ExportListing.seller))
        .filter(ExportListing.seller_id == current_user.id)
        .order_by(ExportListing.created_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.post(
    "/listings",
    response_model=ExportListingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an export-ready herb listing (seller)",
)
def create_listing(
    body: ExportListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(
        UserRole.farmer, UserRole.researcher, UserRole.pharma_company, UserRole.admin
    )),
):
    herb = db.get(Herb, body.herb_id)
    if not herb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")

    listing = ExportListing(
        seller_id=current_user.id,
        **body.model_dump(),
    )
    db.add(listing)
    db.commit()
    return _load_listing_with_relations(listing.id, db)


@router.get(
    "/listings",
    response_model=List[ExportListingRead],
    summary="Browse all export listings with optional filters",
)
def list_listings(
    herb_id: Optional[int] = Query(None, description="Filter by herb"),
    grade: Optional[HerbGrade] = Query(None, description="Filter by herb grade"),
    country: Optional[str] = Query(None, description="Filter by seller origin state/country (partial match)"),
    min_qty: Optional[Decimal] = Query(None, description="Minimum quantity available (kg)"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price per kg (USD)"),
    organic: Optional[bool] = Query(None, description="Filter organic-only listings"),
    certified: Optional[bool] = Query(None, description="True = must have at least one cert"),
    export_ready: Optional[bool] = Query(None, description="Filter by export_ready flag"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ExportListing).options(
        selectinload(ExportListing.herb),
        selectinload(ExportListing.seller),
    )

    if herb_id is not None:
        q = q.filter(ExportListing.herb_id == herb_id)
    if grade is not None:
        q = q.filter(ExportListing.herb_grade == grade)
    if country:
        q = q.filter(ExportListing.origin_state.ilike(f"%{country}%"))
    if min_qty is not None:
        q = q.filter(ExportListing.quantity_kg >= min_qty)
    if max_price is not None:
        q = q.filter(ExportListing.price_per_kg_usd <= max_price)
    if organic is not None:
        q = q.filter(ExportListing.is_organic.is_(organic))
    if certified is True:
        q = q.filter(
            (ExportListing.certificate_nafdac.isnot(None)) |
            (ExportListing.certificate_naqs.isnot(None)) |
            (ExportListing.certificate_nepc.isnot(None))
        )
    if export_ready is not None:
        q = q.filter(ExportListing.export_ready.is_(export_ready))

    return q.order_by(ExportListing.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/listings/{listing_id}",
    response_model=ExportListingRead,
    summary="Single export listing with full cert details",
)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _load_listing_with_relations(listing_id, db)


@router.put(
    "/listings/{listing_id}",
    response_model=ExportListingRead,
    summary="Update an export listing (owner or admin)",
)
def update_listing(
    listing_id: int,
    body: ExportListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(listing_id, db)
    if current_user.role != UserRole.admin and listing.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)
    db.commit()
    return _load_listing_with_relations(listing_id, db)


@router.delete(
    "/listings/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an export listing (owner or admin)",
)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(listing_id, db)
    if current_user.role != UserRole.admin and listing.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    db.delete(listing)
    db.commit()


@router.post(
    "/listings/{listing_id}/verify-certs",
    response_model=ExportListingRead,
    summary="Admin verifies NAFDAC/NEPC certificates and marks listing export-ready",
)
def verify_certs(
    listing_id: int,
    body: CertVerifyBody,
    db: Session = Depends(get_db),
    _: User = _ADMIN,
):
    listing = _get_listing_or_404(listing_id, db)
    listing.export_ready = body.export_ready
    db.commit()
    return _load_listing_with_relations(listing_id, db)


# ===========================================================================
# GLOBAL BUYERS
# ===========================================================================

# ── Literal routes first: /register, /my-profile, /all ─────────────────────

@router.post(
    "/buyers/register",
    response_model=GlobalBuyerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register as a global buyer",
)
def register_buyer(
    body: GlobalBuyerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a buyer profile. Use PUT /buyers/my-profile to update it.",
        )
    buyer = GlobalBuyer(user_id=current_user.id, **body.model_dump())
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return buyer


@router.get(
    "/buyers/my-profile",
    response_model=GlobalBuyerRead,
    summary="Get the current user's buyer profile",
)
def my_buyer_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buyer = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No buyer profile found. Register at POST /export/buyers/register.",
        )
    return buyer


@router.put(
    "/buyers/my-profile",
    response_model=GlobalBuyerRead,
    summary="Update the current user's buyer profile",
)
def update_my_buyer_profile(
    body: GlobalBuyerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buyer = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No buyer profile found. Register at POST /export/buyers/register.",
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(buyer, field, value)
    db.commit()
    db.refresh(buyer)
    return buyer


@router.get(
    "/buyers/all",
    response_model=List[GlobalBuyerRead],
    summary="Admin: list all registered global buyers",
)
def list_all_buyers(
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    buyer_type: Optional[str] = Query(None, description="Filter by buyer_type"),
    country: Optional[str] = Query(None, description="Filter by country (partial match)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = _ADMIN,
):
    q = db.query(GlobalBuyer)
    if verified is not None:
        q = q.filter(GlobalBuyer.verified.is_(verified))
    if buyer_type:
        q = q.filter(GlobalBuyer.buyer_type == buyer_type)
    if country:
        q = q.filter(GlobalBuyer.country.ilike(f"%{country}%"))
    return q.order_by(GlobalBuyer.created_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/buyers/verify/{buyer_id}",
    response_model=GlobalBuyerRead,
    summary="Admin: verify a global buyer profile",
)
def verify_buyer(
    buyer_id: int,
    db: Session = Depends(get_db),
    _: User = _ADMIN,
):
    buyer = _get_buyer_or_404(buyer_id, db)
    if buyer.verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Buyer is already verified",
        )
    buyer.verified = True
    db.commit()
    db.refresh(buyer)
    return buyer


# ===========================================================================
# AI-POWERED MATCHMAKING
# ===========================================================================

@router.get(
    "/match/buyers-for-listing/{listing_id}",
    response_model=BuyerMatchResponse,
    summary="AI: find the best global buyers for this export listing",
)
def match_buyers_for_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    listing = _load_listing_with_relations(listing_id, db)
    listing_dict = _listing_to_dict(listing)

    # Prefer verified buyers and those whose preferred_herbs includes this herb
    herb_name = listing_dict["herb_name"].lower()
    all_buyers_raw = (
        db.query(GlobalBuyer)
        .order_by(
            # True sorts before False in PostgreSQL (DESC puts True first)
            GlobalBuyer.verified.desc(),
            GlobalBuyer.created_at.desc(),
        )
        .limit(_AI_CANDIDATE_LIMIT)
        .all()
    )

    # Re-sort: buyers who list this herb in their preferences float to top
    def _preference_key(b: GlobalBuyer) -> tuple:
        herb_match = any(
            herb_name in (pref.lower() if isinstance(pref, str) else "")
            for pref in (b.preferred_herbs or [])
        )
        return (not herb_match, not b.verified)

    all_buyers_raw.sort(key=_preference_key)
    buyer_dicts = [_buyer_to_dict(b) for b in all_buyers_raw]

    if not buyer_dicts:
        return BuyerMatchResponse(
            listing_id=listing_id,
            matches=[],
            total_buyers_evaluated=0,
        )

    raw_matches = match_buyers_to_herb(listing_dict, buyer_dicts)

    # Enrich each match result with the buyer object
    buyer_index = {b.id: b for b in all_buyers_raw}
    enriched = [
        BuyerMatchResult(
            buyer_id=m["buyer_id"],
            match_score=m["match_score"],
            reason=m["reason"],
            buyer=GlobalBuyerRead.model_validate(buyer_index[m["buyer_id"]])
            if m["buyer_id"] in buyer_index else None,
        )
        for m in raw_matches
    ]

    return BuyerMatchResponse(
        listing_id=listing_id,
        matches=enriched,
        total_buyers_evaluated=len(buyer_dicts),
    )


@router.get(
    "/match/listings-for-buyer/{buyer_id}",
    response_model=ListingMatchResponse,
    summary="AI: find the best export listings for this buyer profile",
)
def match_listings_for_buyer(
    buyer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buyer = _get_buyer_or_404(buyer_id, db)

    # Non-admin users can only run matching for their own buyer profile
    if current_user.role != UserRole.admin and buyer.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    buyer_dict = _buyer_to_dict(buyer)

    # Prefer export-ready listings, float herb preferences to top
    preferred = {h.lower() for h in (buyer.preferred_herbs or []) if isinstance(h, str)}

    all_listings_raw = (
        db.query(ExportListing)
        .options(selectinload(ExportListing.herb), selectinload(ExportListing.seller))
        .order_by(ExportListing.export_ready.desc(), ExportListing.created_at.desc())
        .limit(_AI_CANDIDATE_LIMIT)
        .all()
    )

    def _listing_key(lst: ExportListing) -> tuple:
        herb_name = (lst.herb.name_english if lst.herb else "").lower()
        match = herb_name in preferred
        return (not match, not lst.export_ready)

    all_listings_raw.sort(key=_listing_key)
    listing_dicts = [_listing_to_dict(l) for l in all_listings_raw]

    if not listing_dicts:
        return ListingMatchResponse(
            buyer_id=buyer_id,
            matches=[],
            total_listings_evaluated=0,
        )

    raw_matches = match_listings_to_buyer(buyer_dict, listing_dicts)

    listing_index = {l.id: l for l in all_listings_raw}
    enriched = [
        ListingMatchResult(
            listing_id=m["listing_id"],
            match_score=m["match_score"],
            reason=m["reason"],
            listing=ExportListingRead.model_validate(listing_index[m["listing_id"]])
            if m["listing_id"] in listing_index else None,
        )
        for m in raw_matches
    ]

    return ListingMatchResponse(
        buyer_id=buyer_id,
        matches=enriched,
        total_listings_evaluated=len(listing_dicts),
    )


@router.post(
    "/match/request",
    response_model=TradeIntroductionResponse,
    summary="Buyer sends a trade interest request — AI generates a professional introduction",
)
def request_trade_introduction(
    body: MatchInterestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Load listing with relations
    listing = _load_listing_with_relations(body.listing_id, db)

    # Buyer must have a registered profile
    buyer_profile = db.query(GlobalBuyer).filter(GlobalBuyer.user_id == current_user.id).first()
    if not buyer_profile:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must register as a global buyer before sending interest. "
                   "Use POST /export/buyers/register.",
        )

    seller_user: User = listing.seller
    herb: Herb = listing.herb

    seller_dict = {
        "full_name": seller_user.full_name if seller_user else "Nigerian Seller",
        "company_name": None,
        "origin_state": listing.origin_state,
    }
    buyer_dict = _buyer_to_dict(buyer_profile)
    herb_dict = {
        "name_english": herb.name_english if herb else "",
        "scientific_name": herb.scientific_name if herb else None,
        "description": herb.description if herb else "",
    }
    listing_dict = _listing_to_dict(listing)

    letter = generate_trade_introduction(seller_dict, buyer_dict, herb_dict, listing_dict)

    return TradeIntroductionResponse(
        listing_id=listing.id,
        seller_name=seller_user.full_name if seller_user else "Seller",
        buyer_company=buyer_profile.company_name or current_user.full_name,
        herb_name=herb.name_english if herb else "",
        introduction_letter=letter,
    )
