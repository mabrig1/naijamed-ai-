from typing import Any

import httpx

from app.core.config import settings


def search_nearby_facilities(state: str | None, lga: str | None, emergency: bool, limit: int = 5) -> list[dict[str, Any]]:
    """Find coarse-location facilities without sending a home address to a third party.

    OpenStreetMap listings are discovery results only. They are explicitly marked as
    not accreditation-verified; verified clinicians are sourced from our own provider registry.
    """
    if not state and not lga:
        return []
    category = "emergency hospital" if emergency else "hospital clinic"
    location = " ".join(part for part in [lga, state, "Nigeria"] if part)
    params = {
        "q": f"{category} {location}",
        "format": "jsonv2",
        "limit": min(limit, 8),
        "countrycodes": "ng",
        "addressdetails": 1,
    }
    headers = {"User-Agent": f"{settings.APP_NAME}/1.0 clinical-referral"}
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{settings.NOMINATIM_URL.rstrip('/')}/search", params=params, headers=headers)
        response.raise_for_status()
    except Exception:
        return []

    results = []
    for row in response.json():
        results.append(
            {
                "name": row.get("name") or row.get("display_name", "Healthcare facility").split(",")[0],
                "address": row.get("display_name"),
                "lat": float(row["lat"]) if row.get("lat") else None,
                "lon": float(row["lon"]) if row.get("lon") else None,
                "source": "OpenStreetMap",
                "accreditation_verified": False,
                "note": "Map discovery result; verify accreditation and opening hours before relying on it.",
            }
        )
    return results
