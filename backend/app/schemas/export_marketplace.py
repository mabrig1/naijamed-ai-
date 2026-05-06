from datetime import datetime, date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from app.models.export_enums import (
    BuyerType, HerbGrade, Incoterms, PackagingType,
)


# ---------------------------------------------------------------------------
# Shared nested summaries
# ---------------------------------------------------------------------------

class HerbSummary(BaseModel):
    id: int
    name_english: str
    scientific_name: str | None

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Export Listings
# ---------------------------------------------------------------------------

class ExportListingCreate(BaseModel):
    herb_id: int
    quantity_kg: Decimal
    price_per_kg_usd: Decimal
    minimum_order_kg: Decimal = Decimal("1")
    herb_grade: HerbGrade
    packaging_type: PackagingType
    available_from_date: date | None = None
    certificate_nafdac: str | None = None
    certificate_naqs: str | None = None
    certificate_nepc: str | None = None
    is_organic: bool = False
    origin_state: str | None = None
    origin_lga: str | None = None
    farm_gps_lat: Decimal | None = None
    farm_gps_lng: Decimal | None = None
    export_ready: bool = False

    model_config = {"str_strip_whitespace": True}

    @field_validator("quantity_kg", "price_per_kg_usd", "minimum_order_kg")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Must be greater than zero")
        return v

    @model_validator(mode="after")
    def minimum_order_lte_quantity(self) -> "ExportListingCreate":
        if self.minimum_order_kg > self.quantity_kg:
            raise ValueError("minimum_order_kg cannot exceed quantity_kg")
        return self


class ExportListingUpdate(BaseModel):
    quantity_kg: Decimal | None = None
    price_per_kg_usd: Decimal | None = None
    minimum_order_kg: Decimal | None = None
    herb_grade: HerbGrade | None = None
    packaging_type: PackagingType | None = None
    available_from_date: date | None = None
    certificate_nafdac: str | None = None
    certificate_naqs: str | None = None
    certificate_nepc: str | None = None
    is_organic: bool | None = None
    origin_state: str | None = None
    origin_lga: str | None = None
    farm_gps_lat: Decimal | None = None
    farm_gps_lng: Decimal | None = None
    export_ready: bool | None = None

    model_config = {"str_strip_whitespace": True}


class ExportListingRead(BaseModel):
    id: int
    herb_id: int
    seller_id: int
    herb: HerbSummary | None = None
    seller: UserSummary | None = None

    quantity_kg: Decimal
    price_per_kg_usd: Decimal
    minimum_order_kg: Decimal
    herb_grade: HerbGrade
    packaging_type: PackagingType
    available_from_date: date | None

    certificate_nafdac: str | None
    certificate_naqs: str | None
    certificate_nepc: str | None
    is_organic: bool

    origin_state: str | None
    origin_lga: str | None
    farm_gps_lat: Decimal | None
    farm_gps_lng: Decimal | None

    export_ready: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CertVerifyBody(BaseModel):
    """Admin marks export certificates as reviewed and listing as export-ready."""
    export_ready: bool = True
    notes: str | None = None

    model_config = {"str_strip_whitespace": True}


# ---------------------------------------------------------------------------
# Global Buyers
# ---------------------------------------------------------------------------

class GlobalBuyerCreate(BaseModel):
    company_name: str | None = None
    country: str
    city: str | None = None
    buyer_type: BuyerType
    preferred_herbs: list[str] = []
    preferred_volume_kg_per_month: Decimal | None = None
    preferred_incoterms: Incoterms | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("country")
    @classmethod
    def country_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("country cannot be blank")
        return v


class GlobalBuyerUpdate(BaseModel):
    company_name: str | None = None
    country: str | None = None
    city: str | None = None
    buyer_type: BuyerType | None = None
    preferred_herbs: list[str] | None = None
    preferred_volume_kg_per_month: Decimal | None = None
    preferred_incoterms: Incoterms | None = None

    model_config = {"str_strip_whitespace": True}


class GlobalBuyerRead(BaseModel):
    id: int
    user_id: int
    company_name: str | None
    country: str
    city: str | None
    buyer_type: BuyerType
    preferred_herbs: list[Any]
    preferred_volume_kg_per_month: Decimal | None
    preferred_incoterms: Incoterms | None
    verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# AI Matchmaking
# ---------------------------------------------------------------------------

class BuyerMatchResult(BaseModel):
    buyer_id: int
    match_score: int
    reason: str
    buyer: GlobalBuyerRead | None = None


class ListingMatchResult(BaseModel):
    listing_id: int
    match_score: int
    reason: str
    listing: ExportListingRead | None = None


class BuyerMatchResponse(BaseModel):
    listing_id: int
    matches: list[BuyerMatchResult]
    total_buyers_evaluated: int


class ListingMatchResponse(BaseModel):
    buyer_id: int
    matches: list[ListingMatchResult]
    total_listings_evaluated: int


# ---------------------------------------------------------------------------
# Trade Introduction / Interest Request
# ---------------------------------------------------------------------------

class MatchInterestRequest(BaseModel):
    """Buyer expresses interest in a listing and requests a trade introduction."""
    listing_id: int
    message: str | None = None

    model_config = {"str_strip_whitespace": True}


class TradeIntroductionResponse(BaseModel):
    listing_id: int
    seller_name: str
    buyer_company: str
    herb_name: str
    introduction_letter: str
