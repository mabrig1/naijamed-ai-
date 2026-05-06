"""
Price Intelligence Engine — herb price forecasting and market analysis.

Gemini-powered functions:
  forecast_herb_price     → 90-day price forecast for a herb in a specific region
  best_market_for_herb    → compares all regions and recommends optimal allocation

Pure-logic helper:
  price_alert_trigger     → returns True when price crosses a user-set threshold
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_FORECAST_PROMPT = """
You are a commodity price analyst specialising in African botanical products and
Nigerian herb exports. You have deep knowledge of global herbal supplement markets,
agricultural supply chains, seasonal harvest cycles, and currency dynamics.

Herb: {herb_name}
Target market / region: {market_region}
Historical price data (USD per kg, chronological — oldest first):
{historical_prices}

Using this data, generate a realistic 90-day price forecast.

Consider:
1. Recent price momentum (acceleration or deceleration)
2. Seasonal patterns typical for this herb (harvest season, dry-season supply dips)
3. Nigerian agricultural export context (NAFDAC, NEPC compliance costs, freight)
4. Demand dynamics in the target region (wellness trend, diaspora demand, pharma use)
5. Currency trends (NGN/USD, EUR/USD, GBP/USD) affecting import purchasing power
6. Global competitor suppliers (India, China for most botanicals)

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "herb": "{herb_name}",
  "region": "{market_region}",
  "current_avg_price_usd": <most recent average price from the data as a number>,
  "forecast_30_days_usd": <realistic 30-day price forecast>,
  "forecast_60_days_usd": <realistic 60-day price forecast>,
  "forecast_90_days_usd": <realistic 90-day price forecast>,
  "trend": "<bullish|bearish|neutral|volatile>",
  "confidence": "<high|medium|low>",
  "drivers": [
    "<key demand or supply driver 1>",
    "<key demand or supply driver 2>",
    "<key demand or supply driver 3>"
  ],
  "risks": [
    "<downside risk 1>",
    "<downside risk 2>"
  ],
  "recommendation": "<specific, actionable advice for a Nigerian exporter — when to ship, how much, to which buyer type>"
}}
"""

_BEST_MARKET_PROMPT = """
You are a Nigerian export market intelligence analyst with 15 years of experience
optimising herb shipments across global markets.

Herb to sell: {herb_name}

Current wholesale prices (USD/kg) by region:
{current_prices}

Global regions available: europe, north_america, asia, middle_east, africa

Analyse these prices and market fundamentals to tell the seller:
1. The single best market to sell to right now (highest net return after freight)
2. The second-best market (diversification option)
3. Markets to avoid this cycle (price too low, regulatory issues, logistics cost not justified)
4. Optimal quantity allocation — how to split a 1,000 kg shipment across markets

Freight cost benchmarks (deduct from regional price to get net return):
- Europe: ~$1.20/kg (sea) to ~$8.00/kg (air)
- North America: ~$1.50/kg (sea) to ~$9.00/kg (air)
- Asia: ~$0.80/kg (sea) to ~$7.00/kg (air)
- Middle East: ~$0.90/kg (sea) to ~$6.50/kg (air)
- Africa (ECOWAS): ~$0.40/kg (road)

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "herb": "{herb_name}",
  "best_market": "<region name>",
  "best_market_net_return_usd": <price minus estimated freight per kg>,
  "best_market_reasoning": "<2-3 sentence explanation>",
  "second_best_market": "<region name>",
  "second_best_net_return_usd": <number>,
  "markets_to_avoid": ["<region>"],
  "avoidance_reasons": {{"<region>": "<reason>"}},
  "optimal_quantity_allocation_kg": {{
    "<region 1>": <kg to send>,
    "<region 2>": <kg to send>
  }},
  "allocation_reasoning": "<why this split maximises revenue and manages logistics risk>",
  "best_window_days": <how many days to wait before shipping for best price — 0 if now>,
  "total_expected_revenue_usd": <estimate for 1000 kg at recommended split>
}}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_gemini_model():
    key = settings.effective_gemini_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env.",
        )
    import google.generativeai as genai
    genai.configure(api_key=key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.35,
            max_output_tokens=2048,
        ),
    )


def _call_gemini_json(prompt: str) -> Any:
    model = _get_gemini_model()
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {exc}",
        )
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned non-JSON response: {exc}. Raw: {raw[:300]}",
        )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def forecast_herb_price(
    herb_name: str,
    market_region: str,
    historical_prices: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Gemini generates a 90-day price forecast based on historical price data.

    historical_prices: list of {"date": "YYYY-MM-DD", "price_usd": float, "source": str}
    Returns structured forecast with trend, drivers, risks, and recommendation.
    """
    if not historical_prices:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No historical price data available for {herb_name} in {market_region}.",
        )

    prompt = _FORECAST_PROMPT.format(
        herb_name=herb_name,
        market_region=market_region,
        historical_prices=json.dumps(historical_prices, indent=2),
    )
    result = _call_gemini_json(prompt)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for price forecast.",
        )

    # Safety defaults — ensure all required keys are present
    result.setdefault("herb", herb_name)
    result.setdefault("region", market_region)
    result.setdefault("current_avg_price_usd", historical_prices[-1].get("price_usd") if historical_prices else 0)
    result.setdefault("trend", "neutral")
    result.setdefault("confidence", "low")
    result.setdefault("drivers", [])
    result.setdefault("risks", [])
    result.setdefault("recommendation", "Consult a commodity broker for current market guidance.")
    return result


def best_market_for_herb(
    herb_name: str,
    current_prices: dict[str, float],
) -> dict[str, Any]:
    """
    Gemini compares all available market regions and recommends the optimal
    selling strategy — best market, second best, markets to avoid, and
    quantity allocation for a 1,000 kg benchmark shipment.

    current_prices: {"europe": 4.60, "north_america": 4.80, "asia": 3.00, ...}
    """
    if not current_prices:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No current price data available for {herb_name}.",
        )

    prompt = _BEST_MARKET_PROMPT.format(
        herb_name=herb_name,
        current_prices=json.dumps(current_prices, indent=2),
    )
    result = _call_gemini_json(prompt)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for market recommendation.",
        )

    result.setdefault("herb", herb_name)
    result.setdefault("best_market", max(current_prices, key=current_prices.get) if current_prices else "europe")
    result.setdefault("markets_to_avoid", [])
    result.setdefault("optimal_quantity_allocation_kg", {})
    return result


def price_alert_trigger(
    herb_id: int,       # noqa: ARG001 — passed for logging / future DB use
    threshold_usd: float,
    current_price: float,
    alert_when: str = "above",
) -> bool:
    """
    Returns True if the current price has crossed the user-defined threshold.

    alert_when:
      "above" — alert when current_price >= threshold_usd (price spike)
      "below" — alert when current_price <= threshold_usd (price dip / buying signal)
    """
    if alert_when == "above":
        return current_price >= threshold_usd
    if alert_when == "below":
        return current_price <= threshold_usd
    return False
