"""
Price Intelligence — herb price index, history, AI forecasts, crowdsourced
price submission, and price-alert subscriptions.

Route ordering rule (FastAPI): all literal/static paths must appear BEFORE
any parameterised sibling at the same path depth.

Router paths under prefix /api/prices:
  GET  /index                 (literal)  ← before /{herb_id}
  GET  /compare               (literal)  ← before /{herb_id}
  GET  /forecast              (literal)  ← before /{herb_id}
  GET  /best-time-to-sell     (literal)  ← before /{herb_id}
  POST /submit                (literal, POST — no conflict)
  GET  /alerts                (literal)  ← no conflict; starts with different segment
  POST /alerts/subscribe      (literal, POST)
  GET  /herb/{herb_id}        (parameterised — declared last)
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import get_current_user, require_role
from app.models.export_enums import MarketRegion
from app.models.export_price_index import ExportPriceIndex
from app.models.herb import Herb
from app.models.user import User, UserRole
from app.schemas.price_intelligence import (
    AlertSubscribeRequest,
    AlertSubscribeResponse,
    AlertsResponse,
    AlertSubscription,
    BestTimeToSellResponse,
    HerbPriceHistoryPoint,
    HerbPriceResponse,
    PriceCompareResponse,
    PriceForecastResponse,
    PriceIndexItem,
    PriceIndexResponse,
    PriceSubmitRequest,
    PriceSubmitResponse,
    RegionPriceSummary,
)
from app.services.price_intelligence_service import (
    best_market_for_herb,
    forecast_herb_price,
    price_alert_trigger,
)

router = APIRouter()

_ADMIN = Depends(require_role(UserRole.admin))

# ---------------------------------------------------------------------------
# In-memory price alert store  (user_id → list[subscription_dict])
# Persists for server lifetime; resets on restart.
# ---------------------------------------------------------------------------
_ALERT_STORE: dict[int, list[dict]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_herb_or_404(herb_id: int, db: Session) -> Herb:
    herb = db.get(Herb, herb_id)
    if not herb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Herb with id={herb_id} not found.",
        )
    return herb


def _latest_price_per_region(herb_id: int, db: Session) -> dict[str, float]:
    """Return {region_str: latest_price_usd} for a herb."""
    subq = (
        db.query(
            ExportPriceIndex.market_region,
            func.max(ExportPriceIndex.recorded_date).label("max_date"),
        )
        .filter(ExportPriceIndex.herb_id == herb_id)
        .group_by(ExportPriceIndex.market_region)
        .subquery()
    )
    rows = (
        db.query(ExportPriceIndex)
        .join(
            subq,
            and_(
                ExportPriceIndex.market_region == subq.c.market_region,
                ExportPriceIndex.recorded_date == subq.c.max_date,
                ExportPriceIndex.herb_id == herb_id,
            ),
        )
        .all()
    )
    return {row.market_region.value: float(row.price_per_kg_usd) for row in rows}


def _pct_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old == 0:
        return None
    return round((new - old) / old * 100, 2)


# ---------------------------------------------------------------------------
# 1. GET /prices/index — global price index
# ---------------------------------------------------------------------------

@router.get(
    "/index",
    response_model=PriceIndexResponse,
    summary="Global herb price index",
    description=(
        "Returns the latest recorded price for every herb × market-region pair "
        "in the database, together with the 30-day price change where available."
    ),
    status_code=status.HTTP_200_OK,
)
def price_index(
    region: Optional[MarketRegion] = Query(None, description="Filter by a specific market region"),
    limit: int = Query(200, ge=1, le=500, description="Max rows to return"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PriceIndexResponse:
    today = date.today()

    # Subquery: latest recorded_date per herb × region
    subq = (
        db.query(
            ExportPriceIndex.herb_id,
            ExportPriceIndex.market_region,
            func.max(ExportPriceIndex.recorded_date).label("max_date"),
        )
        .group_by(ExportPriceIndex.herb_id, ExportPriceIndex.market_region)
    )
    if region:
        subq = subq.filter(ExportPriceIndex.market_region == region)
    subq = subq.subquery()

    latest = (
        db.query(ExportPriceIndex)
        .join(
            subq,
            and_(
                ExportPriceIndex.herb_id == subq.c.herb_id,
                ExportPriceIndex.market_region == subq.c.market_region,
                ExportPriceIndex.recorded_date == subq.c.max_date,
            ),
        )
        .options(selectinload(ExportPriceIndex.herb))
        .limit(limit)
        .all()
    )

    # Build 30-days-ago lookup (approximate: fetch all records ≥30 days old grouped)
    # For simplicity, fetch all data and compute change inline per row
    items: list[PriceIndexItem] = []
    herb_ids_seen: set[int] = set()
    regions_seen: set[str] = set()

    for row in latest:
        herb = row.herb
        herb_ids_seen.add(row.herb_id)
        regions_seen.add(row.market_region.value)

        # 30-day change: find the closest record ~30 days before latest
        thirty_days_ago = row.recorded_date - timedelta(days=30)
        old_row = (
            db.query(ExportPriceIndex)
            .filter(
                ExportPriceIndex.herb_id == row.herb_id,
                ExportPriceIndex.market_region == row.market_region,
                ExportPriceIndex.recorded_date <= thirty_days_ago,
            )
            .order_by(ExportPriceIndex.recorded_date.desc())
            .first()
        )
        change = _pct_change(
            float(old_row.price_per_kg_usd) if old_row else None,
            float(row.price_per_kg_usd),
        )

        items.append(
            PriceIndexItem(
                herb_id=row.herb_id,
                herb_name=herb.name_english if herb else f"Herb #{row.herb_id}",
                scientific_name=herb.scientific_name if herb else None,
                region=row.market_region,
                latest_price_usd=float(row.price_per_kg_usd),
                currency=row.currency,
                recorded_date=row.recorded_date,
                change_30d_pct=change,
                source=row.source,
            )
        )

    return PriceIndexResponse(
        total_entries=len(items),
        herbs_covered=len(herb_ids_seen),
        regions_covered=sorted(regions_seen),
        prices=items,
        as_of=today,
    )


# ---------------------------------------------------------------------------
# 2. GET /prices/compare — cross-region price comparison
# ---------------------------------------------------------------------------

@router.get(
    "/compare",
    response_model=PriceCompareResponse,
    summary="Compare herb prices across regions",
    description=(
        "Compares the latest prices and 30/90-day trends across all market regions "
        "for a specific herb. Identifies the best-paying region right now."
    ),
    status_code=status.HTTP_200_OK,
)
def compare_prices(
    herb_id: int = Query(..., description="Herb ID to compare across regions"),
    days: int = Query(90, ge=7, le=365, description="Lookback period in days"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PriceCompareResponse:
    herb = _get_herb_or_404(herb_id, db)
    cutoff = date.today() - timedelta(days=days)

    rows = (
        db.query(ExportPriceIndex)
        .filter(
            ExportPriceIndex.herb_id == herb_id,
            ExportPriceIndex.recorded_date >= cutoff,
        )
        .order_by(ExportPriceIndex.recorded_date.asc())
        .all()
    )

    # Group by region
    by_region: dict[str, list[ExportPriceIndex]] = {}
    for row in rows:
        key = row.market_region.value
        by_region.setdefault(key, []).append(row)

    summaries: list[RegionPriceSummary] = []
    best_price = -1.0
    best_region = None
    biggest_move = None
    biggest_move_pct = 0.0

    for region_str, region_rows in by_region.items():
        prices = [float(r.price_per_kg_usd) for r in region_rows]
        latest = prices[-1] if prices else None
        oldest = prices[0] if prices else None

        # 30-day ago price
        thirty_cutoff = date.today() - timedelta(days=30)
        old_30_rows = [r for r in region_rows if r.recorded_date <= thirty_cutoff]
        price_30d = float(old_30_rows[-1].price_per_kg_usd) if old_30_rows else None

        chg = _pct_change(price_30d, latest)
        summaries.append(
            RegionPriceSummary(
                region=MarketRegion(region_str),
                latest_price_usd=latest,
                price_30d_ago_usd=price_30d,
                change_30d_pct=chg,
                min_price_usd=round(min(prices), 4) if prices else None,
                max_price_usd=round(max(prices), 4) if prices else None,
                avg_price_usd=round(sum(prices) / len(prices), 4) if prices else None,
                data_points=len(prices),
            )
        )
        if latest and latest > best_price:
            best_price = latest
            best_region = region_str
        if chg and abs(chg) > abs(biggest_move_pct):
            biggest_move_pct = chg
            biggest_move = region_str

    return PriceCompareResponse(
        herb_id=herb_id,
        herb_name=herb.name_english,
        comparison_period_days=days,
        region_summaries=summaries,
        best_region_now=best_region,
        biggest_mover=biggest_move,
    )


# ---------------------------------------------------------------------------
# 3. GET /prices/forecast — AI 90-day price forecast
# ---------------------------------------------------------------------------

@router.get(
    "/forecast",
    response_model=PriceForecastResponse,
    summary="AI-powered 90-day price forecast",
    description=(
        "Fetches the last 12 months of price history for the specified herb and region, "
        "then uses Gemini AI to generate a bullish/bearish 90-day forecast with "
        "demand drivers, risks, and an actionable recommendation."
    ),
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
def price_forecast(
    request: Request,
    herb_id: int = Query(..., description="Herb ID to forecast"),
    region: MarketRegion = Query(..., description="Target market region"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PriceForecastResponse:
    herb = _get_herb_or_404(herb_id, db)
    cutoff = date.today() - timedelta(days=365)

    rows = (
        db.query(ExportPriceIndex)
        .filter(
            ExportPriceIndex.herb_id == herb_id,
            ExportPriceIndex.market_region == region,
            ExportPriceIndex.recorded_date >= cutoff,
        )
        .order_by(ExportPriceIndex.recorded_date.asc())
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data for herb_id={herb_id} in region={region.value}.",
        )

    historical = [
        {
            "date": row.recorded_date.isoformat(),
            "price_usd": float(row.price_per_kg_usd),
            "currency": row.currency,
            "source": row.source,
        }
        for row in rows
    ]

    ai_result = forecast_herb_price(
        herb_name=herb.name_english,
        market_region=region.value,
        historical_prices=historical,
    )

    return PriceForecastResponse(
        herb=herb.name_english,
        herb_id=herb_id,
        region=region.value,
        current_avg_price_usd=ai_result.get("current_avg_price_usd", float(rows[-1].price_per_kg_usd)),
        forecast_30_days_usd=ai_result.get("forecast_30_days_usd", 0.0),
        forecast_60_days_usd=ai_result.get("forecast_60_days_usd", 0.0),
        forecast_90_days_usd=ai_result.get("forecast_90_days_usd", 0.0),
        trend=ai_result.get("trend", "neutral"),
        confidence=ai_result.get("confidence", "low"),
        drivers=ai_result.get("drivers", []),
        risks=ai_result.get("risks", []),
        recommendation=ai_result.get("recommendation", ""),
        data_points_used=len(rows),
    )


# ---------------------------------------------------------------------------
# 4. GET /prices/best-time-to-sell — AI market timing
# ---------------------------------------------------------------------------

@router.get(
    "/best-time-to-sell",
    response_model=BestTimeToSellResponse,
    summary="AI: best time and market to sell",
    description=(
        "Fetches latest prices across all regions for the specified herb, then uses "
        "Gemini AI to recommend: the best market to sell right now, the optimal "
        "quantity split across markets, and how long to wait before shipping."
    ),
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
def best_time_to_sell(
    request: Request,
    herb_id: int = Query(..., description="Herb ID to analyse"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BestTimeToSellResponse:
    herb = _get_herb_or_404(herb_id, db)
    current_prices = _latest_price_per_region(herb_id, db)

    if not current_prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No price data found for herb_id={herb_id}. Ensure the price index is seeded.",
        )

    ai_result = best_market_for_herb(
        herb_name=herb.name_english,
        current_prices=current_prices,
    )

    return BestTimeToSellResponse(
        herb_id=herb_id,
        herb_name=herb.name_english,
        best_market=ai_result.get("best_market", ""),
        best_market_net_return_usd=ai_result.get("best_market_net_return_usd"),
        best_market_reasoning=ai_result.get("best_market_reasoning", ""),
        second_best_market=ai_result.get("second_best_market"),
        second_best_net_return_usd=ai_result.get("second_best_net_return_usd"),
        markets_to_avoid=ai_result.get("markets_to_avoid", []),
        avoidance_reasons=ai_result.get("avoidance_reasons", {}),
        optimal_quantity_allocation_kg=ai_result.get("optimal_quantity_allocation_kg", {}),
        allocation_reasoning=ai_result.get("allocation_reasoning"),
        best_window_days=ai_result.get("best_window_days", 0),
        total_expected_revenue_usd=ai_result.get("total_expected_revenue_usd"),
        current_prices=current_prices,
    )


# ---------------------------------------------------------------------------
# 5. POST /prices/submit — seller submits a real transaction price
# ---------------------------------------------------------------------------

@router.post(
    "/submit",
    response_model=PriceSubmitResponse,
    summary="Submit a real transaction price (crowdsourced)",
    description=(
        "Allows any authenticated seller to submit a real export transaction price. "
        "Crowdsourced prices improve the accuracy of the price index over time."
    ),
    status_code=status.HTTP_201_CREATED,
)
def submit_price(
    body: PriceSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PriceSubmitResponse:
    herb = _get_herb_or_404(body.herb_id, db)

    record_date = body.recorded_date or date.today()
    source_tag = f"crowdsourced — user #{current_user.id}"
    if body.source:
        source_tag = f"{body.source} (crowdsourced — user #{current_user.id})"

    entry = ExportPriceIndex(
        herb_id=body.herb_id,
        market_region=body.market_region,
        price_per_kg_usd=Decimal(str(body.price_per_kg_usd)),
        currency=body.currency,
        recorded_date=record_date,
        source=source_tag,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return PriceSubmitResponse(
        id=entry.id,
        herb_id=entry.herb_id,
        herb_name=herb.name_english,
        market_region=entry.market_region,
        price_per_kg_usd=float(entry.price_per_kg_usd),
        currency=entry.currency,
        recorded_date=entry.recorded_date,
        message=(
            f"Price submitted successfully for {herb.name_english} in "
            f"{entry.market_region.value}. Thank you for contributing to the "
            "NaijaMed price index!"
        ),
    )


# ---------------------------------------------------------------------------
# 6. GET /prices/alerts — list user's price alert subscriptions
# ---------------------------------------------------------------------------

@router.get(
    "/alerts",
    response_model=AlertsResponse,
    summary="List my price alert subscriptions",
    description=(
        "Returns all active price alert subscriptions for the current user, "
        "including whether each alert is currently triggered based on the latest "
        "available price data."
    ),
    status_code=status.HTTP_200_OK,
)
def get_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertsResponse:
    raw_subs = _ALERT_STORE.get(current_user.id, [])
    subscriptions: list[AlertSubscription] = []

    for sub in raw_subs:
        # Check if currently triggered
        current_price = _latest_price_per_region(sub["herb_id"], db).get(sub["market_region"])
        triggered = False
        if current_price is not None:
            triggered = price_alert_trigger(
                herb_id=sub["herb_id"],
                threshold_usd=sub["threshold_usd"],
                current_price=current_price,
                alert_when=sub["alert_when"],
            )

        # Fetch herb name
        herb = db.get(Herb, sub["herb_id"])
        subscriptions.append(
            AlertSubscription(
                subscription_id=sub["subscription_id"],
                herb_id=sub["herb_id"],
                herb_name=herb.name_english if herb else None,
                market_region=MarketRegion(sub["market_region"]),
                threshold_usd=sub["threshold_usd"],
                alert_when=sub["alert_when"],
                is_triggered=triggered,
                current_price_usd=current_price,
                created_at=sub["created_at"],
            )
        )

    return AlertsResponse(
        user_id=current_user.id,
        count=len(subscriptions),
        subscriptions=subscriptions,
    )


# ---------------------------------------------------------------------------
# 7. POST /prices/alerts/subscribe — create a price alert
# ---------------------------------------------------------------------------

@router.post(
    "/alerts/subscribe",
    response_model=AlertSubscribeResponse,
    summary="Subscribe to a price alert",
    description=(
        "Creates a price alert for a herb in a specific region. "
        "Set alert_when='above' to be notified of price spikes, "
        "or alert_when='below' to catch dips (buy-low signals for buyers)."
    ),
    status_code=status.HTTP_201_CREATED,
)
def subscribe_alert(
    body: AlertSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertSubscribeResponse:
    herb = _get_herb_or_404(body.herb_id, db)

    # Enforce per-user cap to prevent abuse
    existing = _ALERT_STORE.get(current_user.id, [])
    if len(existing) >= 50:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum 50 price alert subscriptions per user.",
        )

    sub_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)
    record = {
        "subscription_id": sub_id,
        "herb_id": body.herb_id,
        "market_region": body.market_region.value,
        "threshold_usd": body.threshold_usd,
        "alert_when": body.alert_when,
        "created_at": now,
    }
    _ALERT_STORE.setdefault(current_user.id, []).append(record)

    # Check current trigger state immediately
    current_price = _latest_price_per_region(body.herb_id, db).get(body.market_region.value)
    triggered = False
    if current_price is not None:
        triggered = price_alert_trigger(
            herb_id=body.herb_id,
            threshold_usd=body.threshold_usd,
            current_price=current_price,
            alert_when=body.alert_when,
        )

    direction_word = "above" if body.alert_when == "above" else "below"
    sub = AlertSubscription(
        subscription_id=sub_id,
        herb_id=body.herb_id,
        herb_name=herb.name_english,
        market_region=body.market_region,
        threshold_usd=body.threshold_usd,
        alert_when=body.alert_when,
        is_triggered=triggered,
        current_price_usd=current_price,
        created_at=now,
    )
    triggered_msg = (
        f" ⚠ ALERT ALREADY TRIGGERED — current price ${current_price:.2f} is "
        f"{direction_word} your threshold ${body.threshold_usd:.2f}."
        if triggered else ""
    )
    return AlertSubscribeResponse(
        message=(
            f"Alert created for {herb.name_english} in {body.market_region.value}. "
            f"You will be notified when price goes {direction_word} "
            f"${body.threshold_usd:.2f}/kg.{triggered_msg}"
        ),
        subscription=sub,
    )


# ---------------------------------------------------------------------------
# 8. GET /prices/herb/{herb_id} — price history + optional AI forecast
# ---------------------------------------------------------------------------

@router.get(
    "/herb/{herb_id}",
    response_model=HerbPriceResponse,
    summary="Price history and forecast for one herb",
    description=(
        "Returns the full recorded price history for a herb across all available "
        "regions. Pass ?region= to filter to one region. "
        "Pass ?forecast=true to also include a Gemini AI 90-day price forecast "
        "(requires region to be specified)."
    ),
    status_code=status.HTTP_200_OK,
)
def herb_price_history(
    herb_id: int,
    region: Optional[MarketRegion] = Query(None, description="Filter to a specific market region"),
    forecast: bool = Query(False, description="Also return AI 90-day forecast (requires region)"),
    days: int = Query(365, ge=30, le=730, description="History lookback in days"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HerbPriceResponse:
    herb = _get_herb_or_404(herb_id, db)
    cutoff = date.today() - timedelta(days=days)

    q = db.query(ExportPriceIndex).filter(
        ExportPriceIndex.herb_id == herb_id,
        ExportPriceIndex.recorded_date >= cutoff,
    )
    if region:
        q = q.filter(ExportPriceIndex.market_region == region)
    rows = q.order_by(ExportPriceIndex.recorded_date.asc()).all()

    history: list[HerbPriceHistoryPoint] = [
        HerbPriceHistoryPoint(
            date=row.recorded_date,
            price_usd=float(row.price_per_kg_usd),
            region=row.market_region,
            currency=row.currency,
            source=row.source,
        )
        for row in rows
    ]

    regions_available = sorted({row.market_region.value for row in rows})

    ai_forecast: dict[str, Any] | None = None
    if forecast:
        if not region:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Specify ?region= when requesting a forecast.",
            )
        region_rows = [r for r in rows if r.market_region == region]
        if not region_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data for herb_id={herb_id} in region={region.value}.",
            )
        historical = [
            {"date": r.recorded_date.isoformat(), "price_usd": float(r.price_per_kg_usd)}
            for r in region_rows
        ]
        ai_forecast = forecast_herb_price(
            herb_name=herb.name_english,
            market_region=region.value,
            historical_prices=historical,
        )

    return HerbPriceResponse(
        herb_id=herb_id,
        herb_name=herb.name_english,
        scientific_name=herb.scientific_name,
        regions_available=regions_available,
        price_history=history,
        total_data_points=len(history),
        forecast=ai_forecast,
    )
