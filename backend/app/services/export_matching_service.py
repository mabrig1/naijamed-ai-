"""
Export Matching Engine — Claude-powered buyer/seller matchmaking for NaijaMed AI.

Three public functions:
  match_buyers_to_herb   → rank best global buyers for a given herb listing
  match_listings_to_buyer → rank best export listings for a given buyer profile
  generate_trade_introduction → write a professional trade intro letter

All functions are synchronous; FastAPI runs them in its thread pool.
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_MATCH_BUYERS_PROMPT = """
You are an expert Nigerian agricultural export broker with deep knowledge of
global herb and botanical markets.

Given this Nigerian herb export listing:
{listing}

And these registered global buyers:
{buyers}

Rank the top 5 best-matched buyers based on:
- Herb preference match (does this herb appear in their preferred_herbs list?)
- Volume compatibility (does quantity_kg meet their preferred_volume_kg_per_month?)
- Country/market suitability (is the destination country a strong market for this herb?)
- Buyer type alignment (e.g. pharma_company needs certified herbs, cosmetics_brand prefers organic)
- Incoterms compatibility

Return ONLY a valid JSON array (no markdown, no explanation) with exactly this structure:
[
  {{
    "buyer_id": <integer — must match one of the provided buyer ids>,
    "match_score": <integer 0-100>,
    "reason": "<2-3 sentence explanation of why this buyer is a strong match>"
  }}
]

Rules:
- Return at most 5 items.
- buyer_id must be an integer that exists in the provided buyers list.
- match_score: 0 = terrible fit, 100 = perfect fit.
- If fewer than 5 buyers match meaningfully, return fewer.
- Return only the JSON array — no surrounding text.
"""

_MATCH_LISTINGS_PROMPT = """
You are an expert Nigerian agricultural export broker.

Given this global buyer profile:
{buyer}

And these available Nigerian herb export listings:
{listings}

Rank the top 5 best-matched listings based on:
- Herb match (does the listing herb match buyer's preferred_herbs?)
- Volume fit (does listing quantity_kg cover their preferred_volume_kg_per_month?)
- Price competitiveness (lower USD/kg is generally better for buyers)
- Certification alignment (certified herbs for pharma/regulated buyers)
- Organic preference match
- Incoterms compatibility

Return ONLY a valid JSON array (no markdown, no explanation) with exactly this structure:
[
  {{
    "listing_id": <integer — must match one of the provided listing ids>,
    "match_score": <integer 0-100>,
    "reason": "<2-3 sentence explanation of why this listing suits this buyer>"
  }}
]

Rules:
- Return at most 5 items.
- listing_id must be an integer that exists in the provided listings list.
- match_score: 0 = terrible fit, 100 = perfect fit.
- If fewer than 5 listings match meaningfully, return fewer.
- Return only the JSON array — no surrounding text.
"""

_TRADE_INTRO_PROMPT = """
You are a professional Nigerian export trade facilitator writing on behalf of NaijaMed AI,
a digital platform connecting Nigerian herbal product sellers with global buyers.

Write a formal trade introduction letter from the Nigerian seller to the global buyer.

Seller information:
{seller}

Buyer information:
{buyer}

Herb / product details:
{herb}

Requirements:
- Professional business letter format (no email headers)
- 3-4 paragraphs
- Paragraph 1: Introduce the seller and NaijaMed AI platform context
- Paragraph 2: Describe the herb, its grade, certifications, and why it is a premium product
- Paragraph 3: Connect the herb's properties/market to the buyer's specific needs/industry
- Paragraph 4: Call to action — invite the buyer to respond via the platform
- Tone: formal, confident, export-professional
- Mention relevant certifications (NAFDAC, NAQS, NEPC) if available
- Do NOT use placeholders like [insert name] — use real values from the data above
- Length: 250-350 words
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client():
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key is not configured. Set ANTHROPIC_API_KEY in .env.",
        )
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_claude_json(prompt: str, max_tokens: int = 1024) -> Any:
    """Call Claude and return a parsed JSON value (dict or list)."""
    client = _get_client()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        )

    # Strip markdown code fences defensively
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI returned non-JSON response: {exc}. Raw: {raw_text[:300]}",
        )


def _call_claude_text(prompt: str, max_tokens: int = 1024) -> str:
    """Call Claude and return raw text (for prose outputs like letters)."""
    client = _get_client()
    try:
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
        )


def _serialize_listing(listing: dict[str, Any]) -> str:
    """Compact JSON representation of a listing for prompt injection."""
    return json.dumps({
        "id": listing.get("id"),
        "herb_name": listing.get("herb_name"),
        "scientific_name": listing.get("scientific_name"),
        "quantity_kg": str(listing.get("quantity_kg", "")),
        "price_per_kg_usd": str(listing.get("price_per_kg_usd", "")),
        "minimum_order_kg": str(listing.get("minimum_order_kg", "")),
        "herb_grade": listing.get("herb_grade"),
        "packaging_type": listing.get("packaging_type"),
        "is_organic": listing.get("is_organic"),
        "origin_state": listing.get("origin_state"),
        "certificate_nafdac": bool(listing.get("certificate_nafdac")),
        "certificate_naqs": bool(listing.get("certificate_naqs")),
        "certificate_nepc": bool(listing.get("certificate_nepc")),
        "export_ready": listing.get("export_ready"),
    }, indent=2)


def _serialize_buyer(buyer: dict[str, Any]) -> str:
    return json.dumps({
        "id": buyer.get("id"),
        "company_name": buyer.get("company_name"),
        "country": buyer.get("country"),
        "city": buyer.get("city"),
        "buyer_type": buyer.get("buyer_type"),
        "preferred_herbs": buyer.get("preferred_herbs", []),
        "preferred_volume_kg_per_month": str(buyer.get("preferred_volume_kg_per_month") or "not specified"),
        "preferred_incoterms": buyer.get("preferred_incoterms"),
        "verified": buyer.get("verified"),
    }, indent=2)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def match_buyers_to_herb(
    listing: dict[str, Any],
    all_buyers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Rank up to 5 global buyers that are the best fit for a given herb listing.

    listing  — dict with keys: id, herb_name, scientific_name, quantity_kg,
               price_per_kg_usd, minimum_order_kg, herb_grade, packaging_type,
               is_organic, origin_state, certificate_nafdac, certificate_naqs,
               certificate_nepc, export_ready.
    all_buyers — list of buyer dicts (same shape as _serialize_buyer).

    Returns a list of dicts: [{buyer_id, match_score, reason}, ...]
    """
    if not all_buyers:
        return []

    buyers_json = json.dumps(
        [json.loads(_serialize_buyer(b)) for b in all_buyers], indent=2
    )

    prompt = _MATCH_BUYERS_PROMPT.format(
        listing=_serialize_listing(listing),
        buyers=buyers_json,
    )
    result = _call_claude_json(prompt, max_tokens=1024)

    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for buyer matching.",
        )

    # Validate shape; drop malformed items
    cleaned: list[dict[str, Any]] = []
    valid_ids = {b["id"] for b in all_buyers if "id" in b}
    for item in result:
        if (
            isinstance(item, dict)
            and isinstance(item.get("buyer_id"), int)
            and item["buyer_id"] in valid_ids
            and isinstance(item.get("match_score"), int)
            and isinstance(item.get("reason"), str)
        ):
            cleaned.append({
                "buyer_id": item["buyer_id"],
                "match_score": max(0, min(100, item["match_score"])),
                "reason": item["reason"],
            })

    return sorted(cleaned, key=lambda x: x["match_score"], reverse=True)[:5]


def match_listings_to_buyer(
    buyer: dict[str, Any],
    all_listings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Rank up to 5 export listings that best match a buyer's profile.

    Returns a list of dicts: [{listing_id, match_score, reason}, ...]
    """
    if not all_listings:
        return []

    listings_json = json.dumps(
        [json.loads(_serialize_listing(l)) for l in all_listings], indent=2
    )

    prompt = _MATCH_LISTINGS_PROMPT.format(
        buyer=_serialize_buyer(buyer),
        listings=listings_json,
    )
    result = _call_claude_json(prompt, max_tokens=1024)

    if not isinstance(result, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for listing matching.",
        )

    cleaned: list[dict[str, Any]] = []
    valid_ids = {l["id"] for l in all_listings if "id" in l}
    for item in result:
        if (
            isinstance(item, dict)
            and isinstance(item.get("listing_id"), int)
            and item["listing_id"] in valid_ids
            and isinstance(item.get("match_score"), int)
            and isinstance(item.get("reason"), str)
        ):
            cleaned.append({
                "listing_id": item["listing_id"],
                "match_score": max(0, min(100, item["match_score"])),
                "reason": item["reason"],
            })

    return sorted(cleaned, key=lambda x: x["match_score"], reverse=True)[:5]


def generate_trade_introduction(
    seller: dict[str, Any],
    buyer: dict[str, Any],
    herb: dict[str, Any],
    listing: dict[str, Any],
) -> str:
    """
    Write a professional trade introduction letter from seller to buyer.

    seller  — {full_name, company_name (optional), origin_state}
    buyer   — {company_name, country, city, buyer_type}
    herb    — {name_english, scientific_name, description}
    listing — {quantity_kg, price_per_kg_usd, herb_grade, is_organic,
               certificate_nafdac, certificate_naqs, certificate_nepc}
    """
    seller_info = json.dumps({
        "name": seller.get("full_name", "the seller"),
        "company": seller.get("company_name") or "Independent Nigerian Herb Exporter",
        "origin_state": listing.get("origin_state") or "Nigeria",
        "export_ready": listing.get("export_ready"),
    }, indent=2)

    buyer_info = json.dumps({
        "company": buyer.get("company_name", "your organisation"),
        "country": buyer.get("country", "your country"),
        "city": buyer.get("city", ""),
        "buyer_type": buyer.get("buyer_type", ""),
        "preferred_herbs": buyer.get("preferred_herbs", []),
    }, indent=2)

    herb_info = json.dumps({
        "name": herb.get("name_english", ""),
        "scientific_name": herb.get("scientific_name", ""),
        "description": (herb.get("description") or "")[:400],
        "grade": listing.get("herb_grade", ""),
        "packaging": listing.get("packaging_type", ""),
        "quantity_available_kg": str(listing.get("quantity_kg", "")),
        "price_per_kg_usd": str(listing.get("price_per_kg_usd", "")),
        "is_organic": listing.get("is_organic"),
        "certificate_nafdac": bool(listing.get("certificate_nafdac")),
        "certificate_naqs": bool(listing.get("certificate_naqs")),
        "certificate_nepc": bool(listing.get("certificate_nepc")),
    }, indent=2)

    prompt = _TRADE_INTRO_PROMPT.format(
        seller=seller_info,
        buyer=buyer_info,
        herb=herb_info,
    )
    return _call_claude_text(prompt, max_tokens=600)
