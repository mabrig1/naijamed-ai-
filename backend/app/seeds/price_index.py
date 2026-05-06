"""
Seed — Realistic 2024–2026 price history for 15 Nigerian export herbs.

Each herb gets monthly price entries across 3 market regions spanning
January 2024 → April 2026 (28 data points per region).

Prices are generated with a deterministic formula:
  price(t) = base × trend_factor(t) × seasonal_factor(t) × micro_variation(t)

No random module — results are identical on every run.

Run standalone:
    cd backend
    python -m app.seeds.price_index

Or call seed_price_index(db) from application code (e.g. lifespan handler).
"""
import math
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# Helper: deterministic monthly price generator
# ---------------------------------------------------------------------------

_SEED_START_DATE = date(2024, 1, 15)  # first data point
_SEED_MONTHS = 28                      # Jan 2024 → Apr 2026


def _gen_prices(
    base: float,
    amplitude: float,
    trend_pct: float,
    months: int = _SEED_MONTHS,
) -> list[float]:
    """
    Generate `months` monthly prices (deterministic, no random module).

    base       : average USD/kg price for the period
    amplitude  : seasonal swing as fraction of base (e.g. 0.18 = ±18%)
    trend_pct  : total % change from first to last month (0.20 = +20% rise)
    """
    prices = []
    for t in range(months):
        # Linear upward/downward trend
        trend = 1.0 + (trend_pct * t / max(months - 1, 1))
        # Seasonal: sine wave peaking at ~month 4 (May) then troughing at ~month 10 (Nov)
        # Nigerian herb prices tend to peak in May–June (pre-harvest scarcity)
        # and dip in Oct–Dec (post-harvest surplus)
        seasonal = 1.0 + amplitude * math.sin(2.0 * math.pi * (t - 1) / 12.0)
        # Deterministic micro-variation: small intra-year noise
        micro = 1.0 + 0.018 * math.sin(7.3 * t + 1.1)
        prices.append(round(base * trend * seasonal * micro, 4))
    return prices


def _dates(months: int = _SEED_MONTHS) -> list[date]:
    """Return list of monthly recording dates starting from _SEED_START_DATE."""
    return [_SEED_START_DATE + timedelta(days=30 * i) for i in range(months)]


# ---------------------------------------------------------------------------
# Price seed specification — 15 herbs × 3 regions each
# ---------------------------------------------------------------------------
# Format per entry:
#   herb_name   : must match Herb.name_english exactly (case-insensitive lookup)
#   region      : MarketRegion enum value string
#   base_usd    : average USD/kg price
#   amplitude   : seasonal swing fraction
#   trend_pct   : total price change over the 28-month window
#   currency    : display currency (prices stored as USD)
#   source      : data provenance note
# ---------------------------------------------------------------------------

PRICE_SPEC: list[dict] = [

    # 1. MORINGA — "miracle tree", high EU/US wellness demand
    {"herb_name": "Moringa",         "region": "europe",        "base_usd": 4.60, "amplitude": 0.18, "trend_pct": 0.22, "currency": "EUR", "source": "EU wholesale (€3.80–5.50/kg equivalent)"},
    {"herb_name": "Moringa",         "region": "north_america", "base_usd": 4.85, "amplitude": 0.16, "trend_pct": 0.18, "currency": "USD", "source": "US bulk wholesale ($4.00–6.00/kg)"},
    {"herb_name": "Moringa",         "region": "asia",          "base_usd": 3.05, "amplitude": 0.14, "trend_pct": 0.10, "currency": "USD", "source": "China import CIF ($2.50–3.80/kg)"},

    # 2. BITTER LEAF — diaspora-driven UK/US demand, low domestic Africa price
    {"herb_name": "Bitter Leaf",     "region": "europe",        "base_usd": 2.95, "amplitude": 0.22, "trend_pct": 0.14, "currency": "GBP", "source": "UK diaspora market (£2.00–3.50/kg equivalent)"},
    {"herb_name": "Bitter Leaf",     "region": "north_america", "base_usd": 3.65, "amplitude": 0.20, "trend_pct": 0.16, "currency": "USD", "source": "US specialty market ($3.00–4.50/kg)"},
    {"herb_name": "Bitter Leaf",     "region": "africa",        "base_usd": 0.85, "amplitude": 0.28, "trend_pct": 0.08, "currency": "USD", "source": "West Africa intraregional (ECOWAS)"},

    # 3. TURMERIC — large-volume commodity; China/India price pressure
    {"herb_name": "Turmeric",        "region": "europe",        "base_usd": 2.95, "amplitude": 0.20, "trend_pct": 0.12, "currency": "EUR", "source": "EU wholesale (€2.20–3.80/kg equivalent)"},
    {"herb_name": "Turmeric",        "region": "asia",          "base_usd": 2.10, "amplitude": 0.15, "trend_pct": 0.06, "currency": "USD", "source": "Asia bulk ($1.80–2.50/kg)"},
    {"herb_name": "Turmeric",        "region": "north_america", "base_usd": 3.25, "amplitude": 0.16, "trend_pct": 0.14, "currency": "USD", "source": "US/Canada functional food market"},

    # 4. NEEM — India is main competitor; US biopesticide demand growing
    {"herb_name": "Neem (Dogoyaro)", "region": "asia",          "base_usd": 1.60, "amplitude": 0.22, "trend_pct": 0.05, "currency": "USD", "source": "India CIF ($1.20–2.00/kg)"},
    {"herb_name": "Neem (Dogoyaro)", "region": "north_america", "base_usd": 3.15, "amplitude": 0.18, "trend_pct": 0.12, "currency": "USD", "source": "US organic market ($2.50–4.00/kg)"},
    {"herb_name": "Neem (Dogoyaro)", "region": "europe",        "base_usd": 2.55, "amplitude": 0.20, "trend_pct": 0.08, "currency": "EUR", "source": "EU biopesticide/cosmetics market"},

    # 5. AFRICAN BASIL (SCENT LEAF) — premium organic, high EU/ME specialty price
    {"herb_name": "African Basil (Scent Leaf)", "region": "europe",        "base_usd": 6.50, "amplitude": 0.24, "trend_pct": 0.25, "currency": "EUR", "source": "EU premium organic (€5.00–8.00/kg equivalent)"},
    {"herb_name": "African Basil (Scent Leaf)", "region": "middle_east",   "base_usd": 5.90, "amplitude": 0.20, "trend_pct": 0.18, "currency": "USD", "source": "UAE/Saudi aromatics market"},
    {"herb_name": "African Basil (Scent Leaf)", "region": "north_america", "base_usd": 5.60, "amplitude": 0.22, "trend_pct": 0.20, "currency": "USD", "source": "US specialty herb market"},

    # 6. GINGER — major Nigerian commodity export; strong seasonal swing
    {"herb_name": "Ginger",          "region": "europe",        "base_usd": 2.45, "amplitude": 0.22, "trend_pct": 0.10, "currency": "EUR", "source": "EU food/pharma wholesale"},
    {"herb_name": "Ginger",          "region": "north_america", "base_usd": 2.65, "amplitude": 0.20, "trend_pct": 0.12, "currency": "USD", "source": "US food ingredient market"},
    {"herb_name": "Ginger",          "region": "asia",          "base_usd": 1.25, "amplitude": 0.28, "trend_pct": 0.06, "currency": "USD", "source": "Asian commodity market (incl. China)"},

    # 7. HIBISCUS (ZOBO) — growing EU herbal tea market; ME traditional use
    {"herb_name": "Hibiscus (Zobo)", "region": "europe",        "base_usd": 3.85, "amplitude": 0.20, "trend_pct": 0.15, "currency": "EUR", "source": "EU herbal tea industry"},
    {"herb_name": "Hibiscus (Zobo)", "region": "north_america", "base_usd": 4.25, "amplitude": 0.18, "trend_pct": 0.14, "currency": "USD", "source": "US beverage/supplement market"},
    {"herb_name": "Hibiscus (Zobo)", "region": "middle_east",   "base_usd": 3.55, "amplitude": 0.22, "trend_pct": 0.10, "currency": "USD", "source": "GCC traditional beverage market (Karkadeh)"},

    # 8. ALOE VERA — commodity; cosmetics/pharma; high global supply competition
    {"herb_name": "Aloe Vera",       "region": "europe",        "base_usd": 1.85, "amplitude": 0.15, "trend_pct": 0.08, "currency": "EUR", "source": "EU cosmetics/pharma grade"},
    {"herb_name": "Aloe Vera",       "region": "north_america", "base_usd": 2.25, "amplitude": 0.15, "trend_pct": 0.10, "currency": "USD", "source": "US supplement/personal care"},
    {"herb_name": "Aloe Vera",       "region": "middle_east",   "base_usd": 2.05, "amplitude": 0.18, "trend_pct": 0.08, "currency": "USD", "source": "UAE/Saudi cosmetics market"},

    # 9. LEMONGRASS — essential oil precursor; strong Asia/EU demand
    {"herb_name": "Lemongrass",      "region": "europe",        "base_usd": 3.25, "amplitude": 0.20, "trend_pct": 0.12, "currency": "EUR", "source": "EU food/essential oil market"},
    {"herb_name": "Lemongrass",      "region": "asia",          "base_usd": 1.85, "amplitude": 0.18, "trend_pct": 0.06, "currency": "USD", "source": "Asia processing/extraction market"},
    {"herb_name": "Lemongrass",      "region": "north_america", "base_usd": 3.55, "amplitude": 0.18, "trend_pct": 0.14, "currency": "USD", "source": "US culinary/wellness market"},

    # 10. GARLIC — commodity; large volumes; Nigeria competes on freshness
    {"herb_name": "Garlic",          "region": "europe",        "base_usd": 2.85, "amplitude": 0.25, "trend_pct": 0.10, "currency": "EUR", "source": "EU food wholesale"},
    {"herb_name": "Garlic",          "region": "north_america", "base_usd": 3.05, "amplitude": 0.22, "trend_pct": 0.12, "currency": "USD", "source": "US bulk food market"},
    {"herb_name": "Garlic",          "region": "asia",          "base_usd": 1.65, "amplitude": 0.22, "trend_pct": 0.05, "currency": "USD", "source": "Asia commodity (China dominant supplier)"},

    # 11. SOURSOP (GRAVIOLA) — premium cancer-research demand; high EU/US price
    {"herb_name": "Soursop (Graviola)", "region": "europe",     "base_usd": 8.60, "amplitude": 0.20, "trend_pct": 0.20, "currency": "EUR", "source": "EU nutraceuticals market"},
    {"herb_name": "Soursop (Graviola)", "region": "north_america", "base_usd": 9.30, "amplitude": 0.18, "trend_pct": 0.18, "currency": "USD", "source": "US supplement market"},
    {"herb_name": "Soursop (Graviola)", "region": "middle_east", "base_usd": 7.85, "amplitude": 0.22, "trend_pct": 0.14, "currency": "USD", "source": "UAE wellness/supplement market"},

    # 12. PAWPAW LEAF (PAPAYA) — dengue/malaria interest; growing Asia export
    {"herb_name": "Pawpaw Leaf (Papaya)", "region": "europe",       "base_usd": 4.25, "amplitude": 0.20, "trend_pct": 0.10, "currency": "EUR", "source": "EU herbal supplement market"},
    {"herb_name": "Pawpaw Leaf (Papaya)", "region": "asia",         "base_usd": 2.85, "amplitude": 0.18, "trend_pct": 0.08, "currency": "USD", "source": "Asia pharma/supplement (dengue leaf extract demand)"},
    {"herb_name": "Pawpaw Leaf (Papaya)", "region": "north_america", "base_usd": 4.85, "amplitude": 0.18, "trend_pct": 0.12, "currency": "USD", "source": "US natural health market"},

    # 13. UDA (NEGRO PEPPER) — premium Igbo spice; rare in global market = high price
    {"herb_name": "Uda (Negro Pepper)", "region": "europe",        "base_usd": 12.60, "amplitude": 0.26, "trend_pct": 0.18, "currency": "EUR", "source": "EU specialty African spice market"},
    {"herb_name": "Uda (Negro Pepper)", "region": "north_america", "base_usd": 14.10, "amplitude": 0.24, "trend_pct": 0.16, "currency": "USD", "source": "US diaspora + specialty food"},
    {"herb_name": "Uda (Negro Pepper)", "region": "africa",        "base_usd": 3.55, "amplitude": 0.32, "trend_pct": 0.10, "currency": "USD", "source": "West Africa regional (ECOWAS)"},

    # 14. EHURU (AFRICAN NUTMEG) — aromatic spice; ME/EU exotic ingredient demand
    {"herb_name": "Ehuru (African Nutmeg)", "region": "europe",       "base_usd": 7.55, "amplitude": 0.24, "trend_pct": 0.15, "currency": "EUR", "source": "EU specialty spice/fragrance"},
    {"herb_name": "Ehuru (African Nutmeg)", "region": "middle_east",  "base_usd": 6.85, "amplitude": 0.20, "trend_pct": 0.12, "currency": "USD", "source": "GCC spice market"},
    {"herb_name": "Ehuru (African Nutmeg)", "region": "north_america", "base_usd": 8.25, "amplitude": 0.22, "trend_pct": 0.18, "currency": "USD", "source": "US ethnic/specialty market"},

    # 15. DAWADAWA (AFRICAN LOCUST BEAN) — fermented food additive; high EU/US diaspora price
    {"herb_name": "Dawadawa (African Locust Bean)", "region": "europe",        "base_usd": 9.10, "amplitude": 0.22, "trend_pct": 0.14, "currency": "EUR", "source": "EU West African diaspora food market"},
    {"herb_name": "Dawadawa (African Locust Bean)", "region": "north_america", "base_usd": 10.60, "amplitude": 0.20, "trend_pct": 0.16, "currency": "USD", "source": "US specialty/ethnic food"},
    {"herb_name": "Dawadawa (African Locust Bean)", "region": "africa",        "base_usd": 2.25, "amplitude": 0.28, "trend_pct": 0.10, "currency": "USD", "source": "West Africa wholesale"},
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_price_index(db) -> int:
    """
    Insert monthly price history for 15 herbs × 3 regions × 28 months.
    Returns number of rows inserted (0 if already seeded).
    Depends on seed_herbs() having already run so herb IDs exist.
    """
    from app.models.export_price_index import ExportPriceIndex
    from app.models.herb import Herb

    if db.query(ExportPriceIndex).count() > 0:
        print("ExportPriceIndex already contains data — skipping price seed.")
        return 0

    # Build a case-insensitive lookup: herb name → id
    all_herbs: list[Herb] = db.query(Herb).all()
    name_to_id: dict[str, int] = {h.name_english.lower(): h.id for h in all_herbs}

    recording_dates = _dates(_SEED_MONTHS)
    records = []
    skipped: list[str] = []

    for spec in PRICE_SPEC:
        herb_key = spec["herb_name"].lower()
        herb_id = name_to_id.get(herb_key)
        if herb_id is None:
            skipped.append(spec["herb_name"])
            continue

        prices = _gen_prices(
            base=spec["base_usd"],
            amplitude=spec["amplitude"],
            trend_pct=spec["trend_pct"],
            months=_SEED_MONTHS,
        )

        for i, (rec_date, price) in enumerate(zip(recording_dates, prices)):
            records.append(
                ExportPriceIndex(
                    herb_id=herb_id,
                    market_region=spec["region"],
                    price_per_kg_usd=Decimal(str(price)),
                    currency=spec["currency"],
                    recorded_date=rec_date,
                    source=spec["source"],
                )
            )

    if records:
        db.add_all(records)
        db.commit()

    if skipped:
        print(f"  ⚠ Skipped herbs not found in DB: {', '.join(set(skipped))}")
        print("    Run seed_herbs() first to ensure herb records exist.")

    print(f"Seeded {len(records)} price index records ({len(records) // _SEED_MONTHS} herb×region pairs).")
    return len(records)


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        seed_price_index(db)
    finally:
        db.close()
