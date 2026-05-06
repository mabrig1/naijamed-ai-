from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Nested summaries — embedded in FarmListingRead
# ---------------------------------------------------------------------------

class HerbSummary(BaseModel):
    id: int
    name_english: str
    scientific_name: str | None = None

    model_config = {"from_attributes": True}


class FarmerSummary(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Farm listing schemas
# ---------------------------------------------------------------------------

class FarmListingCreate(BaseModel):
    herb_id: int
    quantity_kg: Decimal
    price_per_kg: Decimal
    location: str
    harvest_date: date
    quality_score: Decimal | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("quantity_kg")
    @classmethod
    def quantity_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity_kg must be greater than 0")
        return v

    @field_validator("price_per_kg")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("price_per_kg must be greater than 0")
        return v

    @field_validator("quality_score")
    @classmethod
    def quality_range(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (0 <= v <= 10):
            raise ValueError("quality_score must be between 0 and 10")
        return v

    @field_validator("location")
    @classmethod
    def location_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("location cannot be blank")
        return v


class FarmListingRead(BaseModel):
    id: int
    farmer_id: int
    herb_id: int
    herb: HerbSummary | None = None
    farmer: FarmerSummary | None = None
    quantity_kg: Decimal
    price_per_kg: Decimal
    location: str
    harvest_date: date
    quality_score: Decimal | None
    is_available: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FarmListingUpdate(BaseModel):
    quantity_kg: Decimal | None = None
    price_per_kg: Decimal | None = None
    location: str | None = None
    harvest_date: date | None = None
    quality_score: Decimal | None = None
    is_available: bool | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("quantity_kg")
    @classmethod
    def quantity_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("quantity_kg must be greater than 0")
        return v

    @field_validator("price_per_kg")
    @classmethod
    def price_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("price_per_kg must be greater than 0")
        return v

    @field_validator("quality_score")
    @classmethod
    def quality_range(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and not (0 <= v <= 10):
            raise ValueError("quality_score must be between 0 and 10")
        return v


# ---------------------------------------------------------------------------
# Inquiry schemas
# ---------------------------------------------------------------------------

class InquiryRequest(BaseModel):
    message: str
    contact_email: str
    quantity_kg_requested: Decimal | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message cannot be blank")
        return v


class InquiryResponse(BaseModel):
    listing_id: int
    herb_name: str
    farmer_name: str
    message: str
    quantity_kg_requested: Decimal | None
    status: str = "inquiry_received"


# ---------------------------------------------------------------------------
# Market demand AI schemas
# ---------------------------------------------------------------------------

class HerbDemandItem(BaseModel):
    herb_name: str
    demand_level: str
    reasoning: str


class PlantingRecommendation(BaseModel):
    herb_name: str
    best_planting_months: list[str]
    regions: list[str]
    notes: str


class PriceForecast(BaseModel):
    herb_name: str
    current_avg_price_per_kg: float | None
    forecast_price_per_kg: float | None
    trend: str


class MarketDemandResponse(BaseModel):
    season: str
    top_herbs: list[HerbDemandItem]
    planting_recommendations: list[PlantingRecommendation]
    price_forecasts: list[PriceForecast]
    quality_improvement_tips: list[str]
    raw: dict[str, Any] | None = None
