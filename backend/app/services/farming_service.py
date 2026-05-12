"""
Smart Farming Intelligence — Gemini-powered market demand prediction for NigerFlora BioSciences.

Synchronous functions; FastAPI runs them in its thread pool.
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_DEMAND_PROMPT = """
You are an agricultural market analyst specialising in Nigerian medicinal herbs and the pharmaceutical supply chain.

Current season: {season}

Current marketplace listings (herb name → quantity available in kg → avg price per kg in NGN):
{listings_summary}

Analyse the current supply landscape and predict pharmaceutical demand for Nigerian medicinal herbs.

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{{
  "top_herbs": [
    {{
      "herb_name": "<herb name>",
      "demand_level": "<high | medium | low>",
      "reasoning": "<why this herb is in demand right now>"
    }}
  ],
  "planting_recommendations": [
    {{
      "herb_name": "<herb name>",
      "best_planting_months": ["<month>", "<month>"],
      "regions": ["<Nigerian region or state>"],
      "notes": "<soil, climate, or spacing advice>"
    }}
  ],
  "price_forecasts": [
    {{
      "herb_name": "<herb name>",
      "current_avg_price_per_kg": <number or null>,
      "forecast_price_per_kg": <number or null>,
      "trend": "<up | down | stable>"
    }}
  ],
  "quality_improvement_tips": [
    "<actionable tip 1>",
    "<actionable tip 2>"
  ]
}}

Rules:
- top_herbs: exactly 5 herbs, ordered highest demand first.
- planting_recommendations: at least 4 herbs, matched to Nigerian growing seasons.
- price_forecasts: at least 5 herbs, use current market data where possible.
- quality_improvement_tips: at least 5 practical tips applicable to Nigerian smallholder farmers.
- Use prices in Nigerian Naira (NGN).
- Return only the JSON — no surrounding text.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_model():
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key is not configured. Set GOOGLE_API_KEY in .env.",
        )
    import google.generativeai as genai

    genai.configure(api_key=settings.GOOGLE_API_KEY)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=2048,
        ),
    )


def _call_gemini(prompt: str) -> dict[str, Any]:
    model = _get_model()
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini API error: {exc}",
        )

    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned non-JSON response: {exc}. Raw: {raw_text[:300]}",
        )


def _format_listings(current_listings: list[dict[str, Any]]) -> str:
    if not current_listings:
        return "No current listings — assume a supply shortage across all herbs."
    lines = []
    for item in current_listings:
        herb = item.get("herb_name", "Unknown")
        qty = item.get("total_quantity_kg", 0)
        price = item.get("avg_price_per_kg", "N/A")
        count = item.get("listing_count", 1)
        lines.append(f"- {herb}: {qty:.1f} kg available across {count} listing(s), avg ₦{price}/kg")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------

def predict_herb_demand(season: str, current_listings: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Ask Gemini to analyse marketplace supply and predict pharma demand.

    Args:
        season: Current or upcoming season (e.g. "dry season", "rainy season", "harmattan").
        current_listings: Aggregated listing data dicts with keys:
            herb_name, total_quantity_kg, avg_price_per_kg, listing_count.

    Returns keys: top_herbs, planting_recommendations, price_forecasts,
    quality_improvement_tips.
    """
    prompt = _DEMAND_PROMPT.format(
        season=season.strip(),
        listings_summary=_format_listings(current_listings),
    )
    result = _call_gemini(prompt)

    defaults: dict[str, Any] = {
        "top_herbs": [],
        "planting_recommendations": [],
        "price_forecasts": [],
        "quality_improvement_tips": [],
    }
    return {**defaults, **result}
