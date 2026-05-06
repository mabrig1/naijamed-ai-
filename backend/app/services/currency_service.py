"""
Currency Conversion Service — NaijaMed AI

Provides USD ↔ NGN (and other currencies) conversion for export listing prices.

Primary source: exchangerate-api.com (EXCHANGERATE_API_KEY in .env)
Fallback:       CBN official rate hard-coded as a conservative fallback

Docs: https://www.exchangerate-api.com/docs/standard-requests
"""
from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

import httpx

from ..core.config import settings

logger = logging.getLogger("currency_service")

# ---------------------------------------------------------------------------
# Simple in-process rate cache (reloads every 6 hours)
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 6 * 3600   # 6 hours
_cache: dict[str, Any] = {}
_cache_lock = Lock()

# CBN conservative fallback rate (USD → NGN) — update occasionally if API is unavailable
_CBN_FALLBACK_USD_NGN = 1_550.0


def _fetch_rates_from_api() -> dict[str, float] | None:
    """
    Fetch latest rates from exchangerate-api.com.
    Returns a dict keyed by currency code (e.g. {"NGN": 1550.0, "EUR": 0.93, ...})
    relative to USD (1 USD = X <currency>).

    Returns None if API call fails.
    """
    api_key = getattr(settings, "EXCHANGERATE_API_KEY", "")
    if not api_key:
        logger.warning("EXCHANGERATE_API_KEY not set — using CBN fallback rate")
        return None

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") == "success":
            return data["conversion_rates"]
        logger.error("exchangerate-api returned non-success: %s", data.get("error-type"))
        return None
    except Exception as exc:
        logger.error("exchangerate-api fetch error: %s", exc)
        return None


def _get_cached_rates() -> dict[str, float]:
    """Return cached rates dict, refreshing if stale."""
    with _cache_lock:
        now = time.time()
        if "rates" in _cache and (now - _cache.get("fetched_at", 0)) < _CACHE_TTL_SECONDS:
            return _cache["rates"]

        rates = _fetch_rates_from_api()
        if rates:
            _cache["rates"] = rates
            _cache["fetched_at"] = now
            return rates

        # Use cached stale rates if available
        if "rates" in _cache:
            logger.warning("Using stale exchange rates — API unavailable")
            return _cache["rates"]

        # Final fallback: minimal rates dict
        logger.warning("No exchange rates available — using CBN fallback USD/NGN")
        return {"NGN": _CBN_FALLBACK_USD_NGN, "USD": 1.0}


# ---------------------------------------------------------------------------
# Public conversion functions
# ---------------------------------------------------------------------------

def usd_to_ngn(amount_usd: float) -> float:
    """Convert USD amount to NGN using live CBN/exchangerate rate."""
    rates = _get_cached_rates()
    rate = rates.get("NGN", _CBN_FALLBACK_USD_NGN)
    return round(amount_usd * rate, 2)


def ngn_to_usd(amount_ngn: float) -> float:
    """Convert NGN amount to USD."""
    rates = _get_cached_rates()
    rate = rates.get("NGN", _CBN_FALLBACK_USD_NGN)
    if rate == 0:
        return 0.0
    return round(amount_ngn / rate, 4)


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    """
    Convert between any two supported currencies.
    All rates are relative to USD (triangulate: amount → USD → target).

    Example: convert(100, "EUR", "NGN")
    """
    from_currency = from_currency.upper()
    to_currency   = to_currency.upper()

    if from_currency == to_currency:
        return round(amount, 4)

    rates = _get_cached_rates()

    # Rates are USD-based (1 USD = X currency)
    # Convert from_currency → USD first
    rate_from = rates.get(from_currency, 1.0 if from_currency == "USD" else None)
    rate_to   = rates.get(to_currency,   1.0 if to_currency   == "USD" else None)

    if rate_from is None:
        logger.warning("Unknown currency %s — returning original amount", from_currency)
        return round(amount, 4)
    if rate_to is None:
        logger.warning("Unknown currency %s — returning original amount", to_currency)
        return round(amount, 4)

    amount_usd = amount / rate_from        # to USD
    amount_target = amount_usd * rate_to   # to target
    return round(amount_target, 4)


def get_current_rate(from_currency: str = "USD", to_currency: str = "NGN") -> dict[str, Any]:
    """
    Return the current exchange rate between two currencies with metadata.

    Response shape mirrors what the frontend expects for price display.
    """
    from_currency = from_currency.upper()
    to_currency   = to_currency.upper()
    rates = _get_cached_rates()

    rate = convert(1.0, from_currency, to_currency)
    fetched_at = _cache.get("fetched_at")

    return {
        "from_currency": from_currency,
        "to_currency":   to_currency,
        "rate":          rate,
        "source":        "exchangerate-api.com" if getattr(settings, "EXCHANGERATE_API_KEY", "") else "CBN fallback",
        "fetched_at":    fetched_at,
        "ngn_per_usd":   rates.get("NGN", _CBN_FALLBACK_USD_NGN),
        "note": (
            "Rate is refreshed every 6 hours. For official transactions, "
            "always use the CBN I&E window rate from your Authorised Dealer Bank."
        ),
    }


def enrich_listing_with_ngn(price_per_kg_usd: float, quantity_kg: float) -> dict[str, Any]:
    """
    Return a price block with both USD and NGN values.

    Used when creating/displaying export listings so Nigerian sellers see
    domestic currency equivalents alongside the USD listing price.
    """
    ngn_rate   = _get_cached_rates().get("NGN", _CBN_FALLBACK_USD_NGN)
    unit_ngn   = round(price_per_kg_usd * ngn_rate, 2)
    total_usd  = round(price_per_kg_usd * quantity_kg, 2)
    total_ngn  = round(unit_ngn * quantity_kg, 2)

    return {
        "price_per_kg_usd": price_per_kg_usd,
        "price_per_kg_ngn": unit_ngn,
        "total_value_usd":  total_usd,
        "total_value_ngn":  total_ngn,
        "exchange_rate_ngn_per_usd": ngn_rate,
        "currency_note": "NGN values are indicative only. Use CBN I&E window rate for official settlements.",
    }
