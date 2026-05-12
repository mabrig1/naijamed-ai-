"""
NCS (Nigeria Customs Service) & NCSW Integration — NigerFlora BioSciences

NOTE: This is a MOCK implementation.
Integrate with the Nigeria Customs Single Window (NCSW) portal when live
credentials are available from NCS:
  - NCSW Portal: https://www.ncsw.gov.ng
  - NCS Tariff API: https://tariff.customs.gov.ng (apply for developer key)
  - Contact: ict@customs.gov.ng

NCSW API Base URL (when live): https://api.ncsw.gov.ng/v1
Auth: OAuth2 Client Credentials (client_id + client_secret from NCS developer portal)

Maintainer contact: exports-tech@nigerflora.mabrigkorie.org
"""
from __future__ import annotations

from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# HS Code database — Nigerian herb exports (Chapter 12: Oil seeds, misc grain,
# straw, fodder; Chapter 13: Lac, gums, resins; Chapter 14: Vegetable plaiting)
# ---------------------------------------------------------------------------

# Key: herb name (lowercase, stripped)  →  {hs_code, description, duty_rate, ...}
_HS_CODE_DB: dict[str, dict[str, Any]] = {
    "moringa":                   {"hs_code": "1212.99.00", "description": "Dried moringa leaves / powder, other dried vegetables and roots", "duty_rate_pct": 5.0,  "vat": True},
    "moringa powder":            {"hs_code": "1212.99.00", "description": "Dried moringa leaves / powder, other dried vegetables and roots", "duty_rate_pct": 5.0,  "vat": True},
    "moringa (drumstick tree)":  {"hs_code": "1212.99.00", "description": "Dried moringa leaves / powder, other dried vegetables and roots", "duty_rate_pct": 5.0,  "vat": True},
    "bitter leaf":               {"hs_code": "1212.21.00", "description": "Dried Vernonia amygdalina (bitter leaf), seaweed and other algae", "duty_rate_pct": 5.0,  "vat": True},
    "bitter leaf (dried)":       {"hs_code": "1212.21.00", "description": "Dried Vernonia amygdalina (bitter leaf)", "duty_rate_pct": 5.0,  "vat": True},
    "turmeric":                  {"hs_code": "0910.30.00", "description": "Turmeric (curcuma) — spices", "duty_rate_pct": 5.0,  "vat": True},
    "turmeric root":             {"hs_code": "0910.30.00", "description": "Turmeric (curcuma) — spices", "duty_rate_pct": 5.0,  "vat": True},
    "neem":                      {"hs_code": "1515.90.10", "description": "Neem (Azadirachta indica) oil and derivatives", "duty_rate_pct": 5.0,  "vat": True},
    "neem (dogoyaro)":           {"hs_code": "1515.90.10", "description": "Neem (Azadirachta indica) oil; dried neem leaf extracts", "duty_rate_pct": 5.0,  "vat": True},
    "african basil":             {"hs_code": "1211.90.90", "description": "Plants and parts of plants (Ocimum gratissimum), dried", "duty_rate_pct": 5.0,  "vat": True},
    "african basil (scent leaf)":{"hs_code": "1211.90.90", "description": "Plants and parts of plants (Ocimum gratissimum), dried", "duty_rate_pct": 5.0,  "vat": True},
    "ginger":                    {"hs_code": "0910.11.00", "description": "Ginger, neither crushed nor ground", "duty_rate_pct": 5.0,  "vat": True},
    "ginger root":               {"hs_code": "0910.11.00", "description": "Ginger, neither crushed nor ground", "duty_rate_pct": 5.0,  "vat": True},
    "garlic":                    {"hs_code": "0703.20.00", "description": "Garlic, fresh or chilled", "duty_rate_pct": 10.0, "vat": True},
    "hibiscus":                  {"hs_code": "0605.10.00", "description": "Hibiscus sabdariffa (zobo) dried flowers", "duty_rate_pct": 5.0,  "vat": True},
    "hibiscus (zobo)":           {"hs_code": "0605.10.00", "description": "Hibiscus sabdariffa (zobo) dried calyces", "duty_rate_pct": 5.0,  "vat": True},
    "aloe vera":                 {"hs_code": "1302.19.90", "description": "Vegetable saps and extracts (Aloe vera)", "duty_rate_pct": 5.0,  "vat": True},
    "tiger nut":                 {"hs_code": "1212.99.00", "description": "Tiger nuts (Cyperus esculentus), dried", "duty_rate_pct": 5.0,  "vat": True},
    "baobab":                    {"hs_code": "0813.40.00", "description": "Baobab fruit powder, dried", "duty_rate_pct": 5.0,  "vat": True},
    "baobab powder":             {"hs_code": "0813.40.00", "description": "Baobab fruit powder, dried", "duty_rate_pct": 5.0,  "vat": True},
    "black seed":                {"hs_code": "1207.40.00", "description": "Nigella sativa (black seed / black cumin) seeds", "duty_rate_pct": 5.0,  "vat": True},
    "shea butter":               {"hs_code": "1515.90.20", "description": "Shea (karite) butter (crude)", "duty_rate_pct": 5.0,  "vat": False},
    "shea":                      {"hs_code": "1515.90.20", "description": "Shea (karite) butter / oil", "duty_rate_pct": 5.0,  "vat": False},
    "soursop leaf":              {"hs_code": "1211.90.90", "description": "Annona muricata (soursop) dried leaf", "duty_rate_pct": 5.0,  "vat": True},
    "soursop":                   {"hs_code": "0810.90.00", "description": "Annona muricata (soursop) fresh fruit", "duty_rate_pct": 5.0,  "vat": True},
    "clove":                     {"hs_code": "0907.10.00", "description": "Cloves (whole fruit, cloves and stems), fresh or dried", "duty_rate_pct": 5.0,  "vat": True},
    "cloves":                    {"hs_code": "0907.10.00", "description": "Cloves (whole fruit, cloves and stems), fresh or dried", "duty_rate_pct": 5.0,  "vat": True},
    "african pepper":            {"hs_code": "0904.21.00", "description": "Pepper (Piper nigrum) dried, neither crushed nor ground", "duty_rate_pct": 5.0,  "vat": True},
    "uziza leaf":                {"hs_code": "1211.90.90", "description": "Piper guineense (uziza/Ashanti pepper) dried leaf", "duty_rate_pct": 5.0,  "vat": True},
    "lemongrass":                {"hs_code": "1211.90.90", "description": "Cymbopogon citratus (lemongrass) dried", "duty_rate_pct": 5.0,  "vat": True},
    "cat's claw":                {"hs_code": "1302.19.90", "description": "Uncaria tomentosa (cat's claw) extract", "duty_rate_pct": 5.0,  "vat": True},
}

_FALLBACK_HS = {
    "hs_code": "1211.90.90",
    "description": "Plants and parts of plants (including seeds and fruits), fresh, chilled, frozen or dried — other",
    "duty_rate_pct": 5.0,
    "vat": True,
}


def lookup_hs_code(herb_name: str) -> dict[str, Any]:
    """
    Look up HS code for a Nigerian herb from the seeded database.

    NOTE: Real implementation should query NCS Tariff API:
    GET https://tariff.customs.gov.ng/api/v1/search?q={herb_name}
    with Authorization: Bearer <ncs_tariff_api_key>
    """
    key = herb_name.strip().lower()
    entry = _HS_CODE_DB.get(key, _FALLBACK_HS)
    return {
        "herb_name": herb_name,
        "hs_code": entry["hs_code"],
        "description": entry["description"],
        "duty_rate_pct": entry.get("duty_rate_pct", 5.0),
        "vat_applicable": entry.get("vat", True),
        "required_permits": _required_permits(herb_name),
        "prohibited_countries": [],
        "notes": (
            "HS code sourced from NigerFlora BioSciences internal tariff database. "
            "Verify with NCS Tariff Portal: https://tariff.customs.gov.ng "
            "before formal customs declaration."
        ),
        "source": "MOCK — replace with live NCS Tariff API when credentials are available",
    }


def _required_permits(herb_name: str) -> list[str]:
    """Return required export permits based on herb category."""
    name = herb_name.lower()
    permits = ["NAFDAC Export Certificate", "NEPC Non-Oil Export Certificate"]
    if any(kw in name for kw in ["seed", "aloe", "neem oil", "shea"]):
        permits.append("SON Product Conformity Assessment")
    if any(kw in name for kw in ["leaf", "bark", "root", "flower"]):
        permits.append("NAQS Phytosanitary Certificate")
    permits.append("Form NXP (CBN Forex Repatriation)")
    return permits


# ---------------------------------------------------------------------------
# Customs duty calculator
# ---------------------------------------------------------------------------

def calculate_customs_duty(
    hs_code: str,
    value_usd: float,
    quantity_kg: float,
    destination_country: str,
) -> dict[str, Any]:
    """
    Calculate estimated customs duty and levies for a Nigerian herb export.

    NOTE: Real implementation:
    POST https://api.ncsw.gov.ng/v1/duty-calculator
    Body: {hs_code, customs_value_usd, quantity_kg, origin, destination}

    Nigerian export levies structure (2024):
    - Export Supervision Levy: 0.5% of FOB value
    - NALDA Export Levy: 1% of FOB value (agricultural products)
    - Total effective levy: ~1.5% for most herbs
    (No export customs duty on raw agricultural commodities)
    """
    # Look up entry from DB or fall back
    hs_entry = next(
        (v for v in _HS_CODE_DB.values() if v["hs_code"] == hs_code),
        _FALLBACK_HS,
    )

    export_supervision_levy_pct = 0.5
    nalda_levy_pct = 1.0          # agricultural exports
    total_levy_pct = export_supervision_levy_pct + nalda_levy_pct

    export_supervision_levy = round(value_usd * export_supervision_levy_pct / 100, 2)
    nalda_levy = round(value_usd * nalda_levy_pct / 100, 2)
    total_levies = round(export_supervision_levy + nalda_levy, 2)

    # Destination import duty (simplified — ECOWAS CET for African, standard for rest)
    is_ecowas = destination_country.lower() in {
        "ghana", "senegal", "mali", "côte d'ivoire", "benin", "togo", "niger",
        "burkina faso", "guinea", "sierra leone", "liberia", "cape verde", "gambia",
    }
    dest_import_duty_pct = 0.0 if is_ecowas else hs_entry.get("duty_rate_pct", 5.0)
    dest_import_duty = round(value_usd * dest_import_duty_pct / 100, 2)

    vat_on_destination = round(value_usd * 0.2, 2) if destination_country.lower() == "united kingdom" else 0.0

    return {
        "hs_code": hs_code,
        "fob_value_usd": round(value_usd, 2),
        "quantity_kg": quantity_kg,
        "destination_country": destination_country,
        "nigerian_export_levies": {
            "export_supervision_levy_usd": export_supervision_levy,
            "nalda_levy_usd": nalda_levy,
            "total_usd": total_levies,
            "note": "Payable to Nigeria Customs Service at port of export",
        },
        "destination_import_duty": {
            "duty_rate_pct": dest_import_duty_pct,
            "duty_usd": dest_import_duty,
            "vat_usd": vat_on_destination,
            "is_ecowas_zero_rated": is_ecowas,
            "note": "Estimated. Actual duty assessed by destination country customs.",
        },
        "total_estimated_levies_usd": round(total_levies + dest_import_duty + vat_on_destination, 2),
        "price_per_kg_levy_usd": round(total_levies / quantity_kg, 4) if quantity_kg > 0 else 0,
        "source": (
            "MOCK — calculations based on NCS 2024 tariff schedule. "
            "Replace with live NCSW API: https://api.ncsw.gov.ng/v1/duty-calculator"
        ),
    }


# ---------------------------------------------------------------------------
# NCSW Form draft generator
# ---------------------------------------------------------------------------

def generate_ncsw_form_draft(
    exporter_name: str,
    exporter_tin: str,
    exporter_nepc_number: str,
    product_name: str,
    hs_code: str,
    quantity_kg: float,
    fob_value_usd: float,
    destination_country: str,
    port_of_exit: str,
    consignee_name: str,
    consignee_address: str,
    bill_of_lading_number: str | None = None,
    vessel_name: str | None = None,
) -> dict[str, Any]:
    """
    Generate a Nigeria Customs Single Window (NCSW) export declaration form draft.

    Real implementation: POST https://api.ncsw.gov.ng/v1/declarations/export
    This draft mirrors the Single Administrative Document (SAD) format
    used by Nigerian Customs.

    NOTE: The NCSW portal requires direct submission by a licensed
    customs agent (CHA — Customs House Agent). This function generates
    a pre-filled draft for your agent to review and submit.
    """
    today = date.today()
    ref_number = f"NCS-DRAFT-{today.strftime('%Y%m%d')}-{exporter_tin[-4:]}-{hs_code.replace('.','')[:6]}"

    hs_info = lookup_hs_code(product_name)
    duty_info = calculate_customs_duty(hs_code, fob_value_usd, quantity_kg, destination_country)

    return {
        "form_type": "Nigeria Customs Single Window — Export Declaration (SAD)",
        "reference_number": ref_number,
        "status": "DRAFT — For review by licensed Customs House Agent (CHA)",
        "generated_date": str(today),
        "submission_portal": "https://www.ncsw.gov.ng",
        "box_1_declaration_type": "EX1 — Export",
        "box_2_exporter": {
            "name": exporter_name,
            "tin": exporter_tin,
            "nepc_registration": exporter_nepc_number,
            "country": "Nigeria",
        },
        "box_8_consignee": {
            "name": consignee_name,
            "address": consignee_address,
            "destination_country": destination_country,
        },
        "box_14_customs_representative": "PENDING — Assign licensed Customs House Agent (CHA)",
        "box_15_country_of_export": "NG",
        "box_17_country_of_destination": destination_country,
        "box_25_transport_mode": "Sea" if vessel_name else "Air",
        "box_26_inland_mode": "Road",
        "box_29_office_of_exit": port_of_exit,
        "box_30_goods_location": port_of_exit,
        "box_31_packages": {
            "quantity_kg": quantity_kg,
            "packaging_type": "Sacks / Bags",
            "container_number": "TBD",
            "marks_and_numbers": f"NIGERFLORA-{today.year}-{hs_code[:4]}",
        },
        "box_33_commodity_code": hs_code,
        "box_34_country_of_origin": "NG",
        "box_35_gross_mass_kg": round(quantity_kg * 1.05, 2),   # +5% for packaging
        "box_38_net_mass_kg": quantity_kg,
        "box_42_item_price": {
            "fob_value_usd": fob_value_usd,
            "currency": "USD",
        },
        "box_44_additional_info": {
            "nafdac_cert": "ATTACH — NAFDAC Export Certificate",
            "phytosanitary_cert": "ATTACH — NAQS Phytosanitary Certificate",
            "nepc_cert": "ATTACH — NEPC Non-Oil Export Certificate",
            "packing_list": "ATTACH",
            "commercial_invoice": "ATTACH",
            "form_nxp": "ATTACH — CBN Form NXP (Forex Repatriation)",
        },
        "box_47_duties": {
            "export_supervision_levy_usd": duty_info["nigerian_export_levies"]["export_supervision_levy_usd"],
            "nalda_levy_usd": duty_info["nigerian_export_levies"]["nalda_levy_usd"],
            "total_payable_usd": duty_info["nigerian_export_levies"]["total_usd"],
        },
        "transport": {
            "vessel_flight": vessel_name or "TBD",
            "bill_of_lading": bill_of_lading_number or "TBD",
        },
        "submission_steps": [
            "1. Engage a licensed Customs House Agent (CHA) registered with NCS",
            "2. Provide this draft + all documents listed in Box 44",
            "3. CHA submits through NCSW portal at https://www.ncsw.gov.ng",
            "4. Pay customs levies via e-payment on the NCSW portal",
            "5. Receive Customs Exit Note (CEN) for port release",
            "6. File Form NXP with your bank within 5 days of export",
        ],
        "note": (
            "MOCK DRAFT — This form was generated by NigerFlora BioSciences. "
            "It must be reviewed and submitted by a licensed CHA through "
            "the NCSW portal. Replace this mock with live NCSW API "
            "integration when credentials are available from NCS."
        ),
    }
