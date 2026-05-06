from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.export_enums import MarketRegion


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class PricePoint(BaseModel):
    """One recorded price for a herb in a region."""
    id: int
    herb_id: int
    market_region: MarketRegion
    price_per_kg_usd: Decimal
    currency: str
    recorded_date: date
    source: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 1. GET /prices/index — global price index (latest per herb × region)
# ---------------------------------------------------------------------------

class PriceIndexItem(BaseModel):
    herb_id: int
    herb_name: str
    scientific_name: str | None = None
    region: MarketRegion
    latest_price_usd: float
    currency: str
    recorded_date: date
    change_30d_pct: float | None = None   # % change vs 30 days ago (None if not enough data)
    source: str | None = None


class PriceIndexResponse(BaseModel):
    total_entries: int
    herbs_covered: int
    regions_covered: list[str]
    prices: list[PriceIndexItem]
    as_of: date


# ---------------------------------------------------------------------------
# 2. GET /prices/herb/{herb_id} — history + forecast for one herb
# ---------------------------------------------------------------------------

class HerbPriceHistoryPoint(BaseModel):
    date: date
    price_usd: float
    region: MarketRegion
    currency: str
    source: str | None = None


class HerbPriceResponse(BaseModel):
    herb_id: int
    herb_name: str
    scientific_name: str | None = None
    regions_available: list[str]
    price_history: list[HerbPriceHistoryPoint]
    total_data_points: int
    forecast: dict[str, Any] | None = None     # populated when ?forecast=true


# ---------------------------------------------------------------------------
# 3. GET /prices/compare — cross-region price comparison
# ---------------------------------------------------------------------------

class RegionPriceSummary(BaseModel):
    region: MarketRegion
    latest_price_usd: float | None = None
    price_30d_ago_usd: float | None = None
    change_30d_pct: float | None = None
    min_price_usd: float | None = None
    max_price_usd: float | None = None
    avg_price_usd: float | None = None
    data_points: int = 0


class PriceCompareResponse(BaseModel):
    herb_id: int | None = None
    herb_name: str | None = None
    comparison_period_days: int
    region_summaries: list[RegionPriceSummary]
    best_region_now: str | None = None        # region with highest current price
    biggest_mover: str | None = None          # region with largest % move


# ---------------------------------------------------------------------------
# 4. GET /prices/forecast — AI 90-day forecast
# ---------------------------------------------------------------------------

class PriceForecastResponse(BaseModel):
    herb: str
    herb_id: int
    region: str
    current_avg_price_usd: float
    forecast_30_days_usd: float
    forecast_60_days_usd: float
    forecast_90_days_usd: float
    trend: str                  # bullish | bearish | neutral | volatile
    confidence: str             # high | medium | low
    drivers: list[str]
    risks: list[str]
    recommendation: str
    data_points_used: int


# ---------------------------------------------------------------------------
# 5. POST /prices/submit — seller submits a real transaction price
# ---------------------------------------------------------------------------

class PriceSubmitRequest(BaseModel):
    herb_id: int
    market_region: MarketRegion
    price_per_kg_usd: float
    currency: str = "USD"
    recorded_date: date | None = None
    source: str | None = None

    model_config = {"str_strip_whitespace": True}

    @field_validator("price_per_kg_usd")
    @classmethod
    def positive_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("price_per_kg_usd must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, v: str) -> str:
        allowed = {"USD", "EUR", "GBP", "NGN", "CNY", "AED", "SAR"}
        v = v.upper().strip()
        if v not in allowed:
            raise ValueError(f"currency must be one of: {', '.join(sorted(allowed))}")
        return v


class PriceSubmitResponse(BaseModel):
    id: int
    herb_id: int
    herb_name: str
    market_region: MarketRegion
    price_per_kg_usd: float
    currency: str
    recorded_date: date
    message: str


# ---------------------------------------------------------------------------
# 6 & 7. GET /prices/alerts + POST /prices/alerts/subscribe
# ---------------------------------------------------------------------------

class AlertSubscription(BaseModel):
    subscription_id: str
    herb_id: int
    herb_name: str | None = None
    market_region: MarketRegion
    threshold_usd: float
    alert_when: str       # "above" | "below"
    is_triggered: bool = False
    current_price_usd: float | None = None
    created_at: datetime


class AlertsResponse(BaseModel):
    user_id: int
    count: int
    subscriptions: list[AlertSubscription]
    note: str = (
        "Subscriptions are held in-memory and reset on server restart. "
        "Persistent alert storage will be added in a future release."
    )


class AlertSubscribeRequest(BaseModel):
    herb_id: int
    market_region: MarketRegion
    threshold_usd: float
    alert_when: str = "above"   # "above" (price spike alert) | "below" (buy-low signal)

    model_config = {"str_strip_whitespace": True}

    @field_validator("alert_when")
    @classmethod
    def valid_direction(cls, v: str) -> str:
        if v not in ("above", "below"):
            raise ValueError("alert_when must be 'above' or 'below'")
        return v

    @field_validator("threshold_usd")
    @classmethod
    def positive_threshold(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("threshold_usd must be greater than 0")
        return v


class AlertSubscribeResponse(BaseModel):
    message: str
    subscription: AlertSubscription


# ---------------------------------------------------------------------------
# 8. GET /prices/best-time-to-sell — AI market timing recommendation
# ---------------------------------------------------------------------------

class BestTimeToSellResponse(BaseModel):
    herb_id: int
    herb_name: str
    best_market: str
    best_market_net_return_usd: float | None = None
    best_market_reasoning: str
    second_best_market: str | None = None
    second_best_net_return_usd: float | None = None
    markets_to_avoid: list[str] = []
    avoidance_reasons: dict[str, str] = {}
    optimal_quantity_allocation_kg: dict[str, float] = {}
    allocation_reasoning: str | None = None
    best_window_days: int = 0
    total_expected_revenue_usd: float | None = None
    current_prices: dict[str, float] = {}
