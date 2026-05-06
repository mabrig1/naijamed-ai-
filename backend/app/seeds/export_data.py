"""
Seed — Export Engine demonstration data for NaijaMed AI.

Creates:
  • 2 seed seller users + 5 seed buyer users (if users table < 3 non-admin rows)
  • 10 export listings (across different herbs, grades, origins)
  • 5 GlobalBuyer profiles linked to buyer users
  • 3 completed ExportOrders with Shipments + ShipmentEvents
  • 20-herb × 5-region × 3-month additional price index rows

Idempotent: skips each section if its table already has rows.

Run standalone:
    cd backend
    python -m app.seeds.export_data
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_export_data(db) -> None:
    """Master seed: call from lifespan handler after seed_herbs + seed_price_index."""
    _seed_seed_users(db)
    _seed_export_listings(db)
    _seed_global_buyers(db)
    _seed_completed_orders(db)
    _seed_extra_price_rows(db)


# ---------------------------------------------------------------------------
# 1. Seed users (sellers + buyers)
# ---------------------------------------------------------------------------

_SELLER_EMAILS = [
    "emeka.nwosu@example.ng",
    "amara.obi@example.ng",
]
_BUYER_EMAILS = [
    "healthfoods@london-uk.com",
    "biomax.herbs@berlin.de",
    "globalherb@dubai.ae",
    "naturewise@toronto.ca",
    "ayurherb@mumbai.in",
]


def _seed_seed_users(db) -> None:
    from app.models.user import User, UserRole
    from passlib.context import CryptContext

    if db.query(User).count() >= 3:
        print("Users already exist — skipping user seed.")
        return

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_pw = pwd_ctx.hash("NaijaMed@2024!")

    for email in _SELLER_EMAILS:
        name = email.split("@")[0].replace(".", " ").title()
        db.add(User(
            email=email,
            full_name=name,
            hashed_password=hashed_pw,
            role=UserRole.user,
            is_active=True,
        ))

    for email in _BUYER_EMAILS:
        name = email.split("@")[0].replace(".", " ").replace("-", " ").title()
        db.add(User(
            email=email,
            full_name=name,
            hashed_password=hashed_pw,
            role=UserRole.user,
            is_active=True,
        ))

    db.commit()
    print(f"Seeded {len(_SELLER_EMAILS)} seller users and {len(_BUYER_EMAILS)} buyer users.")


# ---------------------------------------------------------------------------
# 2. Export Listings (10)
# ---------------------------------------------------------------------------

_LISTING_SEEDS = [
    # (herb_name, quantity_kg, price_usd_per_kg, grade, packaging, state, organic, nepc_cert)
    ("Moringa",        2_000, Decimal("4.50"),  "premium",  "vacuum_sealed", "Nasarawa",  True,  "NEPC/RC12345/2024/0001"),
    ("Turmeric",       5_000, Decimal("3.20"),  "A",        "bulk_bag",      "Kaduna",    False, "NEPC/RC12345/2024/0002"),
    ("Ginger",         8_000, Decimal("2.80"),  "A",        "bulk_bag",      "Kaduna",    False, "NEPC/RC67890/2024/0003"),
    ("Shea Butter",    3_500, Decimal("6.00"),  "premium",  "drum",          "Kwara",     True,  "NEPC/RC67890/2024/0004"),
    ("Hibiscus",       4_200, Decimal("5.50"),  "A",        "carton",        "Kano",      True,  "NEPC/RC12345/2024/0005"),
    ("Neem",           6_000, Decimal("2.10"),  "B",        "bulk_bag",      "Ogun",      False, None),
    ("Bitter Leaf",    1_800, Decimal("7.20"),  "premium",  "vacuum_sealed", "Enugu",     True,  "NEPC/RC12345/2024/0007"),
    ("Garlic",         3_000, Decimal("3.80"),  "A",        "carton",        "Jos Plateau",False,"NEPC/RC67890/2024/0008"),
    ("Black Seed",     2_500, Decimal("9.50"),  "premium",  "vacuum_sealed", "Sokoto",    True,  "NEPC/RC12345/2024/0009"),
    ("Aloe Vera",      4_000, Decimal("3.50"),  "A",        "bulk_bag",      "Lagos",     False, None),
]

# GPS coords for Nigerian states (approximate farm centroids)
_STATE_GPS: dict[str, tuple[float, float]] = {
    "Nasarawa":    (8.5376, 8.3247),
    "Kaduna":      (10.5232, 7.4376),
    "Kwara":       (8.9669, 4.5874),
    "Kano":        (12.0022, 8.5920),
    "Ogun":        (6.9980, 3.4737),
    "Enugu":       (6.4584, 7.5464),
    "Jos Plateau": (9.8965, 8.8583),
    "Sokoto":      (13.0059, 5.2476),
    "Lagos":       (6.5244, 3.3792),
}


def _seed_export_listings(db) -> None:
    from app.models.export_listing import ExportListing
    from app.models.export_enums import HerbGrade, PackagingType
    from app.models.herb import Herb
    from app.models.user import User, UserRole

    if db.query(ExportListing).count() > 0:
        print("ExportListings already seeded — skipping.")
        return

    # Get seller users
    sellers = db.query(User).filter(User.email.in_(_SELLER_EMAILS)).all()
    if not sellers:
        # Fallback to any non-admin user
        sellers = db.query(User).filter(User.role != UserRole.admin).limit(2).all()
    if not sellers:
        print("No seller users found — skipping listing seed.")
        return

    for i, (herb_name, qty, price, grade_str, pkg_str, state, organic, nepc_cert) in enumerate(_LISTING_SEEDS):
        herb = db.query(Herb).filter(Herb.name_english.ilike(f"%{herb_name}%")).first()
        if not herb:
            print(f"  Herb '{herb_name}' not found in DB — skipping listing.")
            continue

        seller = sellers[i % len(sellers)]
        gps = _STATE_GPS.get(state, (9.0, 7.5))

        listing = ExportListing(
            herb_id=herb.id,
            seller_id=seller.id,
            quantity_kg=Decimal(str(qty)),
            price_per_kg_usd=price,
            minimum_order_kg=Decimal("50"),
            herb_grade=HerbGrade(grade_str),
            packaging_type=PackagingType(pkg_str),
            available_from_date=date.today() + timedelta(days=7),
            certificate_nafdac=f"NAFDAC/HERB/{1000 + i:04d}/2024",
            certificate_nepc=nepc_cert,
            certificate_naqs=f"NAQS/CERT/{2000 + i:04d}/2024",
            is_organic=organic,
            origin_state=state,
            origin_lga=f"{state} LGA {i + 1}",
            farm_gps_lat=Decimal(str(gps[0])),
            farm_gps_lng=Decimal(str(gps[1])),
            export_ready=True,
        )
        db.add(listing)

    db.commit()
    print(f"Seeded {len(_LISTING_SEEDS)} export listings.")


# ---------------------------------------------------------------------------
# 3. Global Buyer Profiles (5)
# ---------------------------------------------------------------------------

_BUYER_PROFILES = [
    {
        "email":          "healthfoods@london-uk.com",
        "company":        "HealthFoods London Ltd",
        "country":        "United Kingdom",
        "city":           "London",
        "buyer_type":     "herbal_retailer",
        "preferred_herbs": ["Moringa", "Hibiscus", "Bitter Leaf"],
        "volume_kg":      500,
        "incoterms":      "CIF",
        "verified":       True,
    },
    {
        "email":          "biomax.herbs@berlin.de",
        "company":        "BioMax Herbs GmbH",
        "country":        "Germany",
        "city":           "Berlin",
        "buyer_type":     "pharma_company",
        "preferred_herbs": ["Turmeric", "Ginger", "Black Seed"],
        "volume_kg":      2_000,
        "incoterms":      "FOB",
        "verified":       True,
    },
    {
        "email":          "globalherb@dubai.ae",
        "company":        "Global Herb Trading LLC",
        "country":        "United Arab Emirates",
        "city":           "Dubai",
        "buyer_type":     "distributor",
        "preferred_herbs": ["Shea Butter", "Neem", "Aloe Vera"],
        "volume_kg":      3_000,
        "incoterms":      "CIF",
        "verified":       True,
    },
    {
        "email":          "naturewise@toronto.ca",
        "company":        "NatureWise Organics Inc.",
        "country":        "Canada",
        "city":           "Toronto",
        "buyer_type":     "cosmetics_brand",
        "preferred_herbs": ["Shea Butter", "Moringa", "Hibiscus"],
        "volume_kg":      800,
        "incoterms":      "DDP",
        "verified":       False,
    },
    {
        "email":          "ayurherb@mumbai.in",
        "company":        "AyurHerb Exports Pvt Ltd",
        "country":        "India",
        "city":           "Mumbai",
        "buyer_type":     "pharma_company",
        "preferred_herbs": ["Garlic", "Ginger", "Turmeric"],
        "volume_kg":      5_000,
        "incoterms":      "FOB",
        "verified":       True,
    },
]


def _seed_global_buyers(db) -> None:
    from app.models.global_buyer import GlobalBuyer
    from app.models.export_enums import BuyerType, Incoterms
    from app.models.user import User

    if db.query(GlobalBuyer).count() > 0:
        print("GlobalBuyers already seeded — skipping.")
        return

    for profile in _BUYER_PROFILES:
        user = db.query(User).filter(User.email == profile["email"]).first()
        if not user:
            print(f"  Buyer user '{profile['email']}' not found — skipping buyer profile.")
            continue

        buyer = GlobalBuyer(
            user_id=user.id,
            company_name=profile["company"],
            country=profile["country"],
            city=profile["city"],
            buyer_type=BuyerType(profile["buyer_type"]),
            preferred_herbs=profile["preferred_herbs"],
            preferred_volume_kg_per_month=Decimal(str(profile["volume_kg"])),
            preferred_incoterms=Incoterms(profile["incoterms"]),
            verified=profile["verified"],
        )
        db.add(buyer)

    db.commit()
    print(f"Seeded {len(_BUYER_PROFILES)} global buyer profiles.")


# ---------------------------------------------------------------------------
# 4. Completed Orders with Shipments + Events (3)
# ---------------------------------------------------------------------------

_now = datetime.now(timezone.utc)


def _seed_completed_orders(db) -> None:
    from app.models.export_order import ExportOrder
    from app.models.export_listing import ExportListing
    from app.models.escrow_transaction import EscrowTransaction
    from app.models.shipment import Shipment
    from app.models.shipment_event import ShipmentEvent
    from app.models.export_enums import (
        EscrowStatus, FreightChannel, Incoterms, OrderStatus,
        PaymentMethod, PaymentStatus, ShipmentEventType,
    )
    from app.models.user import User

    if db.query(ExportOrder).count() > 0:
        print("ExportOrders already seeded — skipping.")
        return

    listings = db.query(ExportListing).limit(3).all()
    buyer_users = db.query(User).filter(User.email.in_(_BUYER_EMAILS)).limit(3).all()

    if not listings or not buyer_users:
        print("No listings or buyer users — skipping order seed.")
        return

    orders_data = [
        {
            "listing": listings[0],
            "buyer":   buyer_users[0],
            "qty":     Decimal("500"),
            "price":   Decimal("4.50"),
            "country": "United Kingdom",
            "port":    "Felixstowe, UK",
            "channel": FreightChannel.sea,
            "incoterm": Incoterms.CIF,
            "tracking": "MSC-NGA-UK-202401",
            "carrier":  "MSC Mediterranean",
            "origin_port": "Apapa Port, Lagos",
            "vessel":   "MSC ANNA",
            "depart_days_ago": 45,
            "arrive_days_ago": 10,
        },
        {
            "listing": listings[1],
            "buyer":   buyer_users[1],
            "qty":     Decimal("2000"),
            "price":   Decimal("3.20"),
            "country": "Germany",
            "port":    "Hamburg, Germany",
            "channel": FreightChannel.sea,
            "incoterm": Incoterms.FOB,
            "tracking": "HAPAG-NGA-DE-202402",
            "carrier":  "Hapag-Lloyd",
            "origin_port": "Tin Can Island, Lagos",
            "vessel":   "BRUSSELS EXPRESS",
            "depart_days_ago": 30,
            "arrive_days_ago": 3,
        },
        {
            "listing": listings[2],
            "buyer":   buyer_users[2],
            "qty":     Decimal("1500"),
            "price":   Decimal("2.80"),
            "country": "United Arab Emirates",
            "port":    "Jebel Ali, Dubai",
            "channel": FreightChannel.air,
            "incoterm": Incoterms.CIF,
            "tracking": "EK-CARGO-NGA-AE-202403",
            "carrier":  "Emirates SkyCargo",
            "origin_port": "Murtala Muhammed Airport, Lagos",
            "vessel":   "EK8001",
            "depart_days_ago": 12,
            "arrive_days_ago": 8,
        },
    ]

    for od in orders_data:
        listing = od["listing"]
        total_usd = od["qty"] * od["price"]
        depart_date = (_now - timedelta(days=od["depart_days_ago"])).date()
        arrive_date = (_now - timedelta(days=od["arrive_days_ago"])).date()

        order = ExportOrder(
            listing_id=listing.id,
            buyer_id=od["buyer"].id,
            quantity_kg=od["qty"],
            agreed_price_usd=od["price"],
            freight_channel=od["channel"],
            destination_country=od["country"],
            destination_port=od["port"],
            incoterms=od["incoterm"],
            payment_method=PaymentMethod.stripe,
            payment_status=PaymentStatus.released,
            order_status=OrderStatus.delivered,
            estimated_delivery_date=arrive_date,
        )
        db.add(order)
        db.flush()

        # Escrow transaction — released
        escrow = EscrowTransaction(
            order_id=order.id,
            amount_usd=total_usd,
            status=EscrowStatus.released,
            held_at=_now - timedelta(days=od["depart_days_ago"] + 2),
            delivery_confirmed_at=_now - timedelta(days=od["arrive_days_ago"] - 1),
            auto_release_at=_now - timedelta(days=od["depart_days_ago"] - 7),
            released_at=_now - timedelta(days=od["arrive_days_ago"] - 1),
            release_condition="Buyer confirmed delivery",
            gateway="stripe",
            gateway_tx_id=f"pi_seed_{order.id:04d}",
        )
        db.add(escrow)
        db.flush()

        # Shipment
        shipment = Shipment(
            order_id=order.id,
            tracking_number=od["tracking"],
            carrier_name=od["carrier"],
            freight_channel=od["channel"],
            origin_port=od["origin_port"],
            destination_port=od["port"],
            vessel_or_flight=od["vessel"],
            departure_date=depart_date,
            estimated_arrival=arrive_date,
            actual_arrival=arrive_date,
            current_status="Delivered",
            current_location=od["port"],
            temperature_celsius=Decimal("18.5"),
            customs_cleared=True,
        )
        db.add(shipment)
        db.flush()

        # Shipment events timeline
        events = [
            (ShipmentEventType.departure,       od["origin_port"],  "Goods departed from Nigeria",           od["depart_days_ago"]),
            (ShipmentEventType.arrival,          "Mid-ocean",        "Vessel en route — Atlantic Ocean",      od["depart_days_ago"] - 5),
            (ShipmentEventType.customs_cleared,  od["port"],         "Customs clearance completed",           od["arrive_days_ago"] + 1),
            (ShipmentEventType.delivered,        od["port"],         "Delivered to consignee warehouse",      od["arrive_days_ago"]),
        ]
        for evt_type, loc, desc, days_ago in events:
            db.add(ShipmentEvent(
                shipment_id=shipment.id,
                event_type=evt_type,
                location=loc,
                description=desc,
                event_timestamp=_now - timedelta(days=days_ago),
            ))

    db.commit()
    print("Seeded 3 completed export orders with shipments, events, and escrow transactions.")


# ---------------------------------------------------------------------------
# 5. Extra price index rows (20 herbs × 5 regions × 3 months)
# ---------------------------------------------------------------------------

_EXTRA_HERB_PRICES: dict[str, dict[str, float]] = {
    # herb_name: {region: base_price_usd_per_kg}
    "Moringa":       {"europe": 4.80, "north_america": 5.20, "asia": 3.90, "middle_east": 4.50, "africa": 2.80},
    "Turmeric":      {"europe": 3.50, "north_america": 3.80, "asia": 2.50, "middle_east": 3.20, "africa": 2.10},
    "Ginger":        {"europe": 3.00, "north_america": 3.30, "asia": 2.20, "middle_east": 2.80, "africa": 1.90},
    "Hibiscus":      {"europe": 6.00, "north_america": 6.50, "asia": 4.50, "middle_east": 5.50, "africa": 3.50},
    "Shea Butter":   {"europe": 6.50, "north_america": 7.00, "asia": 5.00, "middle_east": 6.00, "africa": 4.00},
    "Bitter Leaf":   {"europe": 7.50, "north_america": 8.00, "asia": 5.50, "middle_east": 6.50, "africa": 3.80},
    "Neem":          {"europe": 2.20, "north_america": 2.50, "asia": 1.80, "middle_east": 2.10, "africa": 1.50},
    "Garlic":        {"europe": 4.00, "north_america": 4.20, "asia": 2.80, "middle_east": 3.50, "africa": 2.20},
    "Black Seed":    {"europe": 9.80, "north_america": 10.50, "asia": 7.50, "middle_east": 9.00, "africa": 6.00},
    "Aloe Vera":     {"europe": 3.80, "north_america": 4.10, "asia": 2.90, "middle_east": 3.60, "africa": 2.40},
    "Cinnamon":      {"europe": 8.50, "north_america": 9.00, "asia": 6.50, "middle_east": 8.00, "africa": 5.50},
    "Cloves":        {"europe": 12.0, "north_america": 13.0, "asia": 9.00, "middle_east": 11.0, "africa": 7.50},
    "Uziza Leaf":    {"europe": 5.50, "north_america": 5.80, "asia": 4.00, "middle_east": 5.00, "africa": 3.20},
    "Scent Leaf":    {"europe": 4.50, "north_america": 4.80, "asia": 3.50, "middle_east": 4.20, "africa": 2.80},
    "Tumeric":       {"europe": 3.40, "north_america": 3.70, "asia": 2.40, "middle_east": 3.10, "africa": 2.00},
    "Ashwagandha":   {"europe": 11.0, "north_america": 12.5, "asia": 7.00, "middle_east": 10.0, "africa": 6.50},
    "Centella":      {"europe": 8.00, "north_america": 8.50, "asia": 6.00, "middle_east": 7.50, "africa": 5.00},
    "Senna":         {"europe": 3.20, "north_america": 3.50, "asia": 2.30, "middle_east": 3.00, "africa": 2.00},
    "Rosemary":      {"europe": 5.00, "north_america": 5.50, "asia": 3.80, "middle_east": 4.80, "africa": 3.00},
    "Lemongrass":    {"europe": 3.50, "north_america": 3.80, "asia": 2.60, "middle_east": 3.20, "africa": 2.10},
}

_EXTRA_MONTHS = 3   # Add 3 months of more recent data


def _seed_extra_price_rows(db) -> None:
    from app.models.export_price_index import ExportPriceIndex
    from app.models.export_enums import MarketRegion
    from app.models.herb import Herb

    # Use a unique source tag to detect if already seeded
    sentinel_count = (
        db.query(ExportPriceIndex)
        .filter(ExportPriceIndex.source == "NaijaMed Seed v2")
        .count()
    )
    if sentinel_count > 0:
        print("Extra price rows already seeded — skipping.")
        return

    today = date.today()
    inserted = 0

    for herb_name, region_prices in _EXTRA_HERB_PRICES.items():
        herb = db.query(Herb).filter(Herb.name_english.ilike(f"%{herb_name}%")).first()
        if not herb:
            continue

        for region_str, base_price in region_prices.items():
            region = MarketRegion(region_str)
            for m in range(_EXTRA_MONTHS, 0, -1):
                record_date = date(today.year, today.month, 15) - timedelta(days=m * 30)
                # Slight upward trend each month (+1.5%)
                adj_price = base_price * (1 + 0.015 * (_EXTRA_MONTHS - m))

                db.add(ExportPriceIndex(
                    herb_id=herb.id,
                    market_region=region,
                    price_per_kg_usd=Decimal(str(round(adj_price, 4))),
                    currency="USD",
                    recorded_date=record_date,
                    source="NaijaMed Seed v2",
                ))
                inserted += 1

    db.commit()
    print(f"Seeded {inserted} extra price index rows ({len(_EXTRA_HERB_PRICES)} herbs × 5 regions × {_EXTRA_MONTHS} months).")


# ---------------------------------------------------------------------------
# Standalone entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        seed_export_data(db)
    finally:
        db.close()
