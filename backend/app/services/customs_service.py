"""
Customs Intelligence Engine — HS codes, duty calculations, country requirements,
and AI-powered customs Q&A for Nigerian herb exporters.

Four AI functions (Claude-powered):
  get_hs_code                    → HS code + duty rates for any herb/form
  calculate_import_duties        → full landed-cost breakdown for a destination
  get_country_import_requirements → certifications, MRLs, quarantine rules per country
  customs_chat                   → expert Nigerian export customs Q&A

Static regulatory data (no AI needed):
  FORM_M_GUIDANCE       → CBN/NCS Form M step-by-step
  NEPC_EXPORT_GUIDE     → NEPC registration guide
  CBN_REPATRIATION_DATA → CBN FX repatriation rules
  HS_CODE_TABLE         → 50-herb in-memory seed (Chapter 09, 12, 13, 33)
  HERB_RESTRICTIONS     → globally restricted herbs
"""
import json
import re
from typing import Any

from fastapi import HTTPException, status

from ..core.config import settings

_DISCLAIMER = (
    "Always confirm with a licensed customs agent (CAC-registered). "
    "This guidance is for informational purposes only and does not constitute "
    "legal, tax, or regulatory advice."
)

_AGENCIES_NOTE = (
    "Relevant Nigerian agencies: Nigerian Customs Service (NCS), NAFDAC, "
    "Nigerian Export Promotion Council (NEPC), Nigerian Agricultural Quarantine Service (NAQS), "
    "Central Bank of Nigeria (CBN)."
)


# ---------------------------------------------------------------------------
# HS Code seed table — 50 Nigerian export herbs
# Codes follow the WCO Harmonized System 2022 (aligned with Nigerian Customs Tariff)
# ---------------------------------------------------------------------------

HS_CODE_TABLE: list[dict[str, Any]] = [
    # ── Chapter 09 — Spices ─────────────────────────────────────────────────
    {
        "herb_name": "Ginger",
        "scientific_name": "Zingiber officinale",
        "common_forms": ["fresh root", "dried root", "ground ginger", "ginger powder"],
        "hs_code": "0910.11.00",
        "hs_code_processed": "0910.12.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Ginger, whether or not crushed or ground (fresh: 0910.11; dried/ground: 0910.12)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 10.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "One of Nigeria's top herb exports. EU/US duty-free under GSP/AGOA. NAQS phytosanitary cert required.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate of Origin", "NCS Customs Export Declaration"],
    },
    {
        "herb_name": "Turmeric",
        "scientific_name": "Curcuma longa",
        "common_forms": ["dried rhizome", "turmeric powder", "curcumin extract"],
        "hs_code": "0910.30.00",
        "hs_code_processed": "0910.30.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Turmeric (curcuma), dried or ground",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 8.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "High global demand for curcumin. EU duty-free under EBA/GSP. Extracts may reclassify under 1302.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit (for extracts)"],
    },
    {
        "herb_name": "Cloves",
        "scientific_name": "Syzygium aromaticum",
        "common_forms": ["dried flower buds", "clove oil", "clove powder"],
        "hs_code": "0907.10.00",
        "hs_code_processed": "0907.10.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Cloves (whole fruit, cloves and stems)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Strong EU market. Clove essential oil reclassifies under 3301.29. NAQS cert mandatory.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate of Origin"],
    },
    {
        "herb_name": "Cinnamon",
        "scientific_name": "Cinnamomum verum / Cinnamomum cassia",
        "common_forms": ["bark sticks", "ground cinnamon", "cinnamon oil"],
        "hs_code": "0906.11.00",
        "hs_code_processed": "0906.19.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Cinnamon and cinnamon-tree flowers, neither crushed nor ground (0906.11); ground (0906.19)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "EU distinguishes true cinnamon (verum) from cassia — labeling must be accurate.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "African Nutmeg",
        "scientific_name": "Monodora myristica",
        "common_forms": ["dried seeds", "ground spice"],
        "hs_code": "0908.11.00",
        "hs_code_processed": "0908.12.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Nutmeg, whether or not shelled or peeled (0908.11 unshelled; 0908.12 shelled)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Unique West African spice. Use precise botanical name on export documentation to avoid classification disputes.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Black Pepper / Uziza",
        "scientific_name": "Piper guineense / Piper nigrum",
        "common_forms": ["dried berries", "ground pepper", "pepper oil"],
        "hs_code": "0904.12.00",
        "hs_code_processed": "0904.22.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Pepper of the genus Piper — dried, neither crushed nor ground (0904.12); crushed or ground (0904.22)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 8.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Piper guineense (Uziza) and Piper nigrum classified similarly. Specify species on docs.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Grains of Selim / Uda",
        "scientific_name": "Xylopia aethiopica",
        "common_forms": ["dried pods", "dried seeds", "ground spice"],
        "hs_code": "0904.21.00",
        "hs_code_processed": "0904.22.00",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Pepper of the genus Capsicum or of the genus Pimenta — classified with other spices",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 10.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Unique West African spice. Limited global classification precedents — consult NCS tariff unit for binding ruling.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Thyme",
        "scientific_name": "Thymus vulgaris",
        "common_forms": ["dried herb", "thyme oil", "ground thyme"],
        "hs_code": "0910.91.10",
        "hs_code_processed": "0910.91.10",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Thyme, dried — classified under other spices/herbs of heading 0910",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 6.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "EU is largest importer. Thyme oil (3301.29) commands higher value per kg.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Bay Leaf",
        "scientific_name": "Laurus nobilis",
        "common_forms": ["dried leaves", "bay leaf oil"],
        "hs_code": "0910.91.90",
        "hs_code_processed": "0910.91.90",
        "hs_chapter": "Chapter 09 — Coffee, Tea, Maté and Spices",
        "description": "Bay leaves (Laurus), dried — other herbs and spices of heading 0910",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Standard culinary/medicinal herb. Straightforward classification.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate"],
    },
    # ── Chapter 12 — Medicinal Plants (the main chapter for Nigerian herbs) ──
    {
        "herb_name": "Moringa",
        "scientific_name": "Moringa oleifera",
        "common_forms": ["dried leaf", "leaf powder", "seed powder", "moringa oil", "capsules"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy, whether or not cut, crushed or powdered — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Nigeria's fastest-growing herb export. Moringa oil (1515.90) commands premium. EU/US duty-free under GSP/AGOA.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Bitter Leaf",
        "scientific_name": "Vernonia amygdalina",
        "common_forms": ["dried leaf", "leaf powder", "bitter leaf extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Strong diaspora market in EU and US. Limited MRL data — buyers may require residue testing.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Neem",
        "scientific_name": "Azadirachta indica",
        "common_forms": ["dried leaf", "neem bark", "neem seed cake", "neem oil"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other (leaf/bark); neem oil: 1515.90",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Neem oil classified under 1515.90. Some countries restrict raw neem seed exports — verify destination rules.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Scent Leaf / African Basil",
        "scientific_name": "Ocimum gratissimum",
        "common_forms": ["fresh leaf", "dried leaf", "essential oil"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other; essential oil: 3301.29",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Essential oil (3301.29) more commercially valuable. Ensure correct classification for oil vs. dried herb.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Lemongrass",
        "scientific_name": "Cymbopogon citratus",
        "common_forms": ["dried herb", "fresh stalks", "lemongrass essential oil"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other; essential oil: 3301.29",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Lemongrass oil (3301.29) is a major value-add. India and China are key markets alongside EU.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Hibiscus / Zobo",
        "scientific_name": "Hibiscus sabdariffa",
        "common_forms": ["dried calyces", "hibiscus powder", "hibiscus extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Hibiscus dried calyces used in pharmacy and food colouring — other plants",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Nigeria is a global top-3 producer. EU food-grade buyers require pesticide residue analysis (EC 396/2005).",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "Laboratory Residue Test Report"],
    },
    {
        "herb_name": "Senna",
        "scientific_name": "Cassia senna / Senna alexandrina",
        "common_forms": ["dried leaves", "senna pods", "senna extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Senna leaves and pods used in pharmacy — other plants and plant parts",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Active pharmaceutical ingredient (sennosides) — pharma buyers require USP/BP grade CoA. Higher value as standardised extract.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NAQS Phytosanitary Certificate", "CoA from accredited lab"],
    },
    {
        "herb_name": "Soursop Leaf",
        "scientific_name": "Annona muricata",
        "common_forms": ["dried leaf", "leaf powder", "soursop extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Growing diaspora demand in UK, US. Therapeutic claims require NAFDAC export permit. Avoid unsubstantiated cancer cure claims on packaging.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Pawpaw Leaf",
        "scientific_name": "Carica papaya",
        "common_forms": ["dried leaf", "leaf powder", "papaya extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Papain enzyme (from latex) classified differently under 3507. Dried leaf remains 1211.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Bitter Kola",
        "scientific_name": "Garcinia kola",
        "common_forms": ["dried seeds/nuts", "bitter kola extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other (seeds as medicinal plant)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Strong research interest (kolaviron). Distinguish from Cola nitida (kola nut under 0802.60). Botanical name on all docs.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Prekese",
        "scientific_name": "Tetrapleura tetraptera",
        "common_forms": ["dried pods", "prekese powder", "prekese extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Limited international trade precedent. Request binding tariff ruling from NCS Tariff Unit before large consignments.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Rosemary",
        "scientific_name": "Salvia rosmarinus (syn. Rosmarinus officinalis)",
        "common_forms": ["dried herb", "rosemary extract", "rosemary essential oil"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Rosemary, dried — plants and parts used in pharmacy and perfumery; oil: 3301.29",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Rosemary essential oil (3301.29) and antioxidant extract (1302.19) are higher-value upgrade paths.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Peppermint",
        "scientific_name": "Mentha × piperita",
        "common_forms": ["dried herb", "peppermint leaf", "peppermint essential oil"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Mint plants, dried — other plants used in pharmacy; peppermint oil: 3301.24",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Peppermint oil (3301.24.00) is a major commodity — commands USD 20–60/kg. Dried herb is lower value.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Eucalyptus",
        "scientific_name": "Eucalyptus globulus / Eucalyptus citriodora",
        "common_forms": ["dried leaf", "eucalyptus essential oil"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Eucalyptus leaves dried — other plants used in pharmacy; oil: 3301.29",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Eucalyptus oil (3301.29) is a key export — pharmaceutical grade requires 70%+ cineole content.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Ashwagandha",
        "scientific_name": "Withania somnifera",
        "common_forms": ["dried root", "root powder", "ashwagandha extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other (adaptogen/tonic root)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Booming global adaptogens market. Standardised extract (withanolides 5%+) commands premium pricing.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Noni",
        "scientific_name": "Morinda citrifolia",
        "common_forms": ["dried fruit", "dried leaf", "noni juice", "noni powder"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other; juice: 2009.89",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Noni juice is a Novel Food in the EU (Regulation 2015/2283) — requires pre-market authorisation for EU export.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "EU Novel Food Authorisation (for juice)"],
    },
    {
        "herb_name": "Periwinkle",
        "scientific_name": "Catharanthus roseus",
        "common_forms": ["dried herb", "dried leaf", "alkaloid extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — source of vinca alkaloids",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Pharmaceutical-grade extracts (vinblastine, vincristine) are highly regulated — require NDLEA and NAFDAC clearance. Raw dried herb less restricted.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "African Mistletoe",
        "scientific_name": "Viscum album / Loranthus micranthus",
        "common_forms": ["dried herb", "mistletoe extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "European market uses mistletoe for complementary cancer therapy (Iscador). High-value niche — requires sterile processing for medical grade.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Guava Leaf",
        "scientific_name": "Psidium guajava",
        "common_forms": ["dried leaf", "guava leaf powder", "guava leaf extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Rising demand in Asia (Japan, China) for antidiabetic applications. Quercetin-standardised extracts command premium.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "African Wild Mango Seed",
        "scientific_name": "Irvingia gabonensis",
        "common_forms": ["dried seed kernel", "ogbono kernel", "IGOB131 extract"],
        "hs_code": "1207.99.90",
        "hs_code_processed": "1207.99.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Other oil seeds and oleaginous fruits — other (Irvingia kernel)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Weight-loss supplement ingredient (IGOB131). Standardised extract 1302.19. Strong US/EU nutraceutical demand.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit for extract"],
    },
    {
        "herb_name": "Black Seed / Nigella",
        "scientific_name": "Nigella sativa",
        "common_forms": ["seeds", "black seed oil", "thymoquinone extract"],
        "hs_code": "1207.99.90",
        "hs_code_processed": "1207.99.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Other oil seeds and oleaginous fruits — other; black seed oil: 1515.90",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Strong Middle East and Muslim diaspora market globally. Black seed oil 1515.90. GCC countries have zero duty for Nigerian exports.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "Halal Certificate for GCC markets"],
    },
    {
        "herb_name": "Fenugreek",
        "scientific_name": "Trigonella foenum-graecum",
        "common_forms": ["seeds", "fenugreek powder", "fenugreek extract"],
        "hs_code": "1207.50.00",
        "hs_code_processed": "1207.50.00",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Fenugreek seeds — other oil seeds (heading 1207.50)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Classified as oil seeds (1207), not medicinal plants (1211). Confirm form — fenugreek extract moves to 1302.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Castor Bean",
        "scientific_name": "Ricinus communis",
        "common_forms": ["seeds", "castor oil", "castor cake"],
        "hs_code": "1207.30.00",
        "hs_code_processed": "1207.30.00",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Castor oil seeds (1207.30); castor oil: 1515.30",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Raw seeds contain ricin — handle with extreme care. Some countries ban raw seed imports; export refined oil instead. Verify destination restrictions.",
        "export_restrictions": True,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "Dangerous Goods Declaration (for seeds)"],
    },
    {
        "herb_name": "Sesame",
        "scientific_name": "Sesamum indicum",
        "common_forms": ["seeds", "sesame oil", "dehulled seeds"],
        "hs_code": "1207.40.00",
        "hs_code_processed": "1207.40.00",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Sesame seeds, whether or not broken (1207.40)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Nigeria is a major sesame exporter. EU requires salmonella testing. Japan mandates strict allergen labeling.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "Salmonella Test Certificate for EU"],
    },
    {
        "herb_name": "Jatropha",
        "scientific_name": "Jatropha curcas",
        "common_forms": ["seeds", "jatropha oil", "detoxified seed cake"],
        "hs_code": "1207.99.90",
        "hs_code_processed": "1207.99.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Other oil seeds and oleaginous fruits — other (biofuel feedstock)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Primarily a biofuel crop. Raw seeds toxic — export as refined oil. Sustainable certification (ISCC) required for EU biofuel markets.",
        "export_restrictions": True,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "ISCC Sustainability Certificate for biofuel"],
    },
    {
        "herb_name": "Locust Bean",
        "scientific_name": "Parkia biglobosa",
        "common_forms": ["dried seeds", "locust bean powder", "dawadawa (fermented)"],
        "hs_code": "1212.99.00",
        "hs_code_processed": "1212.99.00",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Other vegetable products used primarily for human food — other (1212.99)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 10.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Locust bean is also used in pharmaceutical excipients. Fermented dawadawa: food product (2001–2103); seeds: 1212.99.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit for food use"],
    },
    {
        "herb_name": "Tiger Nut",
        "scientific_name": "Cyperus esculentus",
        "common_forms": ["dried tubers", "tiger nut flour", "tiger nut oil"],
        "hs_code": "1212.99.00",
        "hs_code_processed": "1212.99.00",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Other vegetable products used primarily for human food — other (chufa/earth almond)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 10.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Spain is the largest importer (for horchata). Tiger nut oil (1515.90) is a premium cosmetic ingredient.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
    {
        "herb_name": "Kola Nut",
        "scientific_name": "Cola nitida / Cola acuminata",
        "common_forms": ["fresh nuts", "dried nuts", "kola extract"],
        "hs_code": "0802.60.00",
        "hs_code_processed": "0802.60.00",
        "hs_chapter": "Chapter 08 — Edible fruit and nuts",
        "description": "Kola nuts (Cola spp.), fresh or dried, shelled or unshelled",
        "duty_rate_eu_percent": 2.4,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 10.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "EU applies 2.4% MFN rate; Nigerian exporters qualify for 0% under GSP. High religious/cultural significance. Fresh nuts require cold-chain.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NCS Export Declaration"],
    },
    # ── Chapter 13 — Plant Extracts and Gums ────────────────────────────────
    {
        "herb_name": "Aloe Vera",
        "scientific_name": "Aloe barbadensis miller",
        "common_forms": ["aloe gel", "dried aloe powder", "aloe latex", "aloe extract"],
        "hs_code": "1302.19.00",
        "hs_code_processed": "1302.19.00",
        "hs_chapter": "Chapter 13 — Lac, gums, resins and other vegetable saps",
        "description": "Vegetable saps and extracts — other (aloe vera gel and extracts)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Aloin-containing latex is restricted in cosmetics (EU Reg 1223/2009 — max 0.1 ppm). Specify aloin level on all EU export docs.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit", "Aloin content certificate for EU"],
    },
    {
        "herb_name": "African Locust Bean Extract / Dawadawa Extract",
        "scientific_name": "Parkia biglobosa",
        "common_forms": ["standardised extract", "tannin extract"],
        "hs_code": "1302.19.00",
        "hs_code_processed": "1302.19.00",
        "hs_chapter": "Chapter 13 — Lac, gums, resins and other vegetable saps",
        "description": "Vegetable saps and extracts — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Extracts move from Chapter 12 to Chapter 13. Higher value pathway for processed products.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    {
        "herb_name": "Neem Extract",
        "scientific_name": "Azadirachta indica",
        "common_forms": ["azadirachtin extract", "neem bark extract", "neem leaf extract"],
        "hs_code": "1302.19.00",
        "hs_code_processed": "1302.19.00",
        "hs_chapter": "Chapter 13 — Lac, gums, resins and other vegetable saps",
        "description": "Vegetable saps and extracts — other (azadirachtin biopesticide extract)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Azadirachtin extract classified as biopesticide in EU (Reg 540/2011). Food-grade vs. pesticide-grade classifications differ.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit"],
    },
    # ── Chapter 15 — Vegetable Fats and Oils ────────────────────────────────
    {
        "herb_name": "Shea Butter",
        "scientific_name": "Vitellaria paradoxa",
        "common_forms": ["raw shea butter", "refined shea butter", "shea olein", "shea stearin"],
        "hs_code": "1515.90.90",
        "hs_code_processed": "1515.90.90",
        "hs_chapter": "Chapter 15 — Animal or vegetable fats and oils",
        "description": "Other fixed vegetable fats and oils and their fractions — other (shea butter)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Nigeria is world's largest producer. EU food-grade: free fatty acid <1%, moisture <0.1%. Cosmetic grade: lower spec. GI protection opportunities.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "NAQS Certificate", "CoA from accredited lab"],
    },
    {
        "herb_name": "Baobab Oil",
        "scientific_name": "Adansonia digitata",
        "common_forms": ["cold-pressed baobab oil", "refined baobab oil"],
        "hs_code": "1515.90.90",
        "hs_code_processed": "1515.90.90",
        "hs_chapter": "Chapter 15 — Animal or vegetable fats and oils",
        "description": "Other fixed vegetable fats and oils — other (baobab seed oil)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Premium cosmetic ingredient. EU Novel Food status for baobab powder (not oil). Cold-pressed oil well-accepted.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "CoA from accredited lab"],
    },
    {
        "herb_name": "Neem Oil",
        "scientific_name": "Azadirachta indica",
        "common_forms": ["cold-pressed neem oil", "refined neem oil"],
        "hs_code": "1515.90.90",
        "hs_code_processed": "1515.90.90",
        "hs_chapter": "Chapter 15 — Animal or vegetable fats and oils",
        "description": "Other fixed vegetable fats and oils — other (neem seed oil)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Food-grade neem oil not permitted in EU. Cosmetic/agricultural use accepted. Label clearly as non-food grade for EU.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "CoA from accredited lab"],
    },
    {
        "herb_name": "Castor Oil",
        "scientific_name": "Ricinus communis",
        "common_forms": ["refined castor oil", "cold-pressed castor oil", "Jamaican black castor oil"],
        "hs_code": "1515.30.00",
        "hs_code_processed": "1515.30.00",
        "hs_chapter": "Chapter 15 — Animal or vegetable fats and oils",
        "description": "Castor oil and its fractions (1515.30)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "One of Nigeria's top agricultural oil exports. Industrial grade (sebacic acid feedstock) vs. pharmaceutical grade (BP/USP) — major price difference.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "CoA from accredited lab"],
    },
    {
        "herb_name": "Moringa Oil",
        "scientific_name": "Moringa oleifera",
        "common_forms": ["cold-pressed moringa oil", "refined moringa oil"],
        "hs_code": "1515.90.90",
        "hs_code_processed": "1515.90.90",
        "hs_chapter": "Chapter 15 — Animal or vegetable fats and oils",
        "description": "Other fixed vegetable fats and oils — other (moringa seed oil / Ben oil)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 9.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Ben oil (moringa seed oil) is a premium cosmetic and watch-making lubricant. Very high value per litre. EU imports growing.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "CoA from accredited lab"],
    },
    # ── Chapter 33 — Essential Oils ─────────────────────────────────────────
    {
        "herb_name": "Peppermint Essential Oil",
        "scientific_name": "Mentha × piperita",
        "common_forms": ["peppermint oil", "deterpenated peppermint oil"],
        "hs_code": "3301.24.00",
        "hs_code_processed": "3301.24.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Peppermint oil (Mentha piperita) (3301.24)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Pharmaceutical and food-flavouring grade. ISO 856 specifies menthol content. GC/MS purity certificates required by buyers.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate", "ISO Certificate"],
    },
    {
        "herb_name": "Spearmint Essential Oil",
        "scientific_name": "Mentha spicata",
        "common_forms": ["spearmint oil"],
        "hs_code": "3301.25.00",
        "hs_code_processed": "3301.25.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other mint oils (3301.25) — spearmint, cornmint",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Carvone-rich. Used in oral care, food flavouring. GC/MS purity certificate essential.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate"],
    },
    {
        "herb_name": "Lemongrass Essential Oil",
        "scientific_name": "Cymbopogon citratus / Cymbopogon flexuosus",
        "common_forms": ["lemongrass oil", "citral-rich lemongrass oil"],
        "hs_code": "3301.29.00",
        "hs_code_processed": "3301.29.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other essential oils, not elsewhere specified (3301.29)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "High-citral content (70%+) preferred by flavour industry. Nigeria can produce competitively. GC/MS cert required.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate"],
    },
    {
        "herb_name": "Eucalyptus Essential Oil",
        "scientific_name": "Eucalyptus globulus / Eucalyptus citriodora",
        "common_forms": ["eucalyptus oil", "cineole-type eucalyptus oil", "citronellal-type"],
        "hs_code": "3301.29.00",
        "hs_code_processed": "3301.29.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other essential oils, not elsewhere specified — eucalyptus oil (3301.29)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Pharmaceutical grade: minimum 70% 1,8-cineole (ISO 770). Eucalyptus citriodora oil: citronellal type (3301.29), primarily for fragrances.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate", "ISO Certificate"],
    },
    {
        "herb_name": "Rosemary Essential Oil",
        "scientific_name": "Salvia rosmarinus",
        "common_forms": ["rosemary oil", "camphor-type rosemary oil"],
        "hs_code": "3301.29.00",
        "hs_code_processed": "3301.29.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other essential oils, not elsewhere specified (3301.29)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Used in cosmetics, food flavouring, pharma. Camphor content limits apply in some markets. GC/MS cert mandatory.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate"],
    },
    {
        "herb_name": "Scent Leaf / African Basil Essential Oil",
        "scientific_name": "Ocimum gratissimum",
        "common_forms": ["basil oil", "African basil oil", "eugenol-type basil oil"],
        "hs_code": "3301.29.00",
        "hs_code_processed": "3301.29.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other essential oils, not elsewhere specified — African basil (eugenol-rich type)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "O. gratissimum oil is eugenol-rich (30–90%) — different chemotype from sweet basil (methyl chavicol type). Label chemotype precisely.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate"],
    },
    {
        "herb_name": "Clove Essential Oil",
        "scientific_name": "Syzygium aromaticum",
        "common_forms": ["clove bud oil", "clove leaf oil", "clove stem oil"],
        "hs_code": "3301.29.00",
        "hs_code_processed": "3301.29.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other essential oils — clove oil (eugenol 70–90%)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Clove bud oil (most valued) vs. leaf oil vs. stem oil — price differential is significant. Specify part of plant used on documentation.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate"],
    },
    {
        "herb_name": "Hibiscus Essential Oil",
        "scientific_name": "Hibiscus sabdariffa",
        "common_forms": ["hibiscus absolute", "hibiscus extract"],
        "hs_code": "3301.29.00",
        "hs_code_processed": "3301.29.00",
        "hs_chapter": "Chapter 33 — Essential oils and resinoids; cosmetic preparations",
        "description": "Other essential oils, not elsewhere specified — hibiscus absolute (3301.29)",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 3.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Hibiscus absolute is a luxury fragrance ingredient — very high value per gram. Solvent-extraction yield very low (~0.1%). Niche but premium market.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "GC/MS Analysis Certificate"],
    },
    {
        "herb_name": "Baobab Powder",
        "scientific_name": "Adansonia digitata",
        "common_forms": ["baobab fruit pulp powder", "baobab leaf powder"],
        "hs_code": "2008.99.90",
        "hs_code_processed": "2008.99.90",
        "hs_chapter": "Chapter 20 — Preparations of vegetables, fruit, nuts",
        "description": "Other fruit prepared or preserved — baobab pulp powder (food preparation)",
        "duty_rate_eu_percent": 20.8,
        "duty_rate_us_percent": 14.9,
        "duty_rate_china_percent": 30.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "EU Novel Food authorised (2019) — specifically Adansonia digitata fruit pulp. EU duty 20.8% MFN, but GSP preferential rate lower. Leaf powder (1211.90) is different.",
        "export_restrictions": False,
        "certifications_required": ["NAFDAC Export Permit", "NEPC Certificate", "EU Novel Food Compliance Certificate"],
    },
    {
        "herb_name": "Andrographis",
        "scientific_name": "Andrographis paniculata",
        "common_forms": ["dried herb", "andrographolide extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Very high demand post-COVID for immune support. Standardised extract (andrographolide 10–98%) requires NAFDAC export permit.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate", "NAFDAC Export Permit for extracts"],
    },
    {
        "herb_name": "Mango Leaf",
        "scientific_name": "Mangifera indica",
        "common_forms": ["dried leaf", "mango leaf powder", "mangiferin extract"],
        "hs_code": "1211.90.90",
        "hs_code_processed": "1211.90.90",
        "hs_chapter": "Chapter 12 — Oil seeds; industrial or medicinal plants",
        "description": "Plants and parts of plants used in pharmacy — other",
        "duty_rate_eu_percent": 0.0,
        "duty_rate_us_percent": 0.0,
        "duty_rate_china_percent": 5.0,
        "gsp_eligible": True,
        "agoa_eligible": True,
        "notes": "Mangiferin extract (antidiabetic, antioxidant) increasingly sought. Dried leaf is low-value; extract is premium.",
        "export_restrictions": False,
        "certifications_required": ["NAQS Phytosanitary Certificate", "NEPC Certificate"],
    },
]

# Build a fast-lookup index: lowercase herb name → entry
_HS_INDEX: dict[str, dict] = {
    entry["herb_name"].lower(): entry for entry in HS_CODE_TABLE
}
# Also index by scientific name (first word, genus)
for _entry in HS_CODE_TABLE:
    _sci = _entry["scientific_name"].lower().split()[0]
    if _sci not in _HS_INDEX:
        _HS_INDEX[_sci] = _entry


# ---------------------------------------------------------------------------
# Globally restricted herbs
# ---------------------------------------------------------------------------

HERB_RESTRICTIONS: list[dict[str, Any]] = [
    {
        "herb_name": "Cannabis / Hemp",
        "scientific_name": "Cannabis sativa",
        "restriction_type": "heavily_controlled",
        "countries_affected": ["United States", "United Kingdom", "European Union", "China", "UAE", "Saudi Arabia", "Most countries"],
        "reason": "Psychoactive plant under international drug conventions (UN 1961 Convention). Hemp (low-THC) is increasingly legal for fibre/CBD but requires specific permits.",
        "reference": "UN Single Convention on Narcotic Drugs 1961; NDLEA Act (Nigeria); country-specific narcotic laws",
        "export_guidance": "Requires NDLEA export licence in Nigeria. CBD extracts vary by country — verify THC limit (<0.2% EU, <0.3% US) before export.",
    },
    {
        "herb_name": "Khat",
        "scientific_name": "Catha edulis",
        "restriction_type": "banned_in_most_markets",
        "countries_affected": ["United States", "United Kingdom", "Canada", "Germany", "Netherlands", "Australia", "Most Western countries"],
        "reason": "Contains cathinone (Schedule I in US/UK). Legal only in limited countries (Kenya, Ethiopia, Yemen for domestic use).",
        "reference": "UN Convention on Psychotropic Substances 1971; Misuse of Drugs Act 2014 (UK); DEA Schedule I (US)",
        "export_guidance": "Do not export to countries where cathinone is scheduled. Nigeria: NDLEA oversight required.",
    },
    {
        "herb_name": "Hoodia",
        "scientific_name": "Hoodia gordonii",
        "restriction_type": "cites_appendix_ii",
        "countries_affected": ["All signatory CITES countries"],
        "reason": "CITES Appendix II — trade requires export permit from country of origin to protect wild populations from over-harvesting.",
        "reference": "CITES Appendix II; Convention on International Trade in Endangered Species",
        "export_guidance": "Obtain CITES export permit from the CITES Management Authority. Proof of sustainably cultivated (not wild-harvested) stock helps obtain permits.",
    },
    {
        "herb_name": "Opium Poppy (medicinal parts)",
        "scientific_name": "Papaver somniferum",
        "restriction_type": "strictly_controlled",
        "countries_affected": ["All countries"],
        "reason": "Source of morphine, codeine, heroin. Strictly controlled under UN 1961 Convention and national drug laws worldwide.",
        "reference": "UN Single Convention on Narcotic Drugs 1961; NDLEA Act (Nigeria)",
        "export_guidance": "Requires UN Narcotic Drug Export Authorisation. Essentially prohibited except for licensed pharmaceutical manufacturers.",
    },
    {
        "herb_name": "Kratom",
        "scientific_name": "Mitragyna speciosa",
        "restriction_type": "banned_in_some_markets",
        "countries_affected": ["Australia", "Denmark", "Finland", "Germany", "Latvia", "Lithuania", "Poland", "Romania", "Sweden", "Malaysia", "Thailand (historically)", "Several US states"],
        "reason": "Contains mitragynine — stimulant/opioid-like effects. Banned in several countries; legal but regulated in others.",
        "reference": "Country-specific narcotics/controlled substance laws",
        "export_guidance": "Verify legal status in destination country before export. US FDA has import alert on kratom products.",
    },
    {
        "herb_name": "Castor Bean (raw seeds)",
        "scientific_name": "Ricinus communis",
        "restriction_type": "restricted_for_safety",
        "countries_affected": ["United States", "European Union", "Most countries"],
        "reason": "Raw seeds contain ricin, one of the most toxic naturally occurring substances. Many countries restrict import of raw seeds.",
        "reference": "USDA import regulations; EU biosafety regulations",
        "export_guidance": "Export refined castor oil (1515.30) rather than raw seeds. Declare dangerous goods status on all documentation.",
    },
    {
        "herb_name": "Ephedra / Ma Huang",
        "scientific_name": "Ephedra sinica",
        "restriction_type": "restricted_heavily",
        "countries_affected": ["United States", "Canada", "European Union", "Australia", "United Kingdom"],
        "reason": "Contains ephedrine — used as precursor in amphetamine synthesis. Banned as dietary supplement in US/EU; restricted as pharmaceutical.",
        "reference": "US FDA 2004 ban on ephedra dietary supplements; EU Directive 2004/24/EC",
        "export_guidance": "Essentially banned for food/supplement export to US/EU/Canada. Pharmaceutical-grade ephedrine requires controlled substance export permit.",
    },
    {
        "herb_name": "Yohimbe Bark",
        "scientific_name": "Pausinystalia yohimbe",
        "restriction_type": "restricted_in_some_markets",
        "countries_affected": ["Canada", "Australia", "United Kingdom", "Germany", "France", "Several EU countries"],
        "reason": "Contains yohimbine — cardiovascular risks at high doses. Banned or prescription-only as dietary supplement in several markets.",
        "reference": "Health Canada NPN restrictions; EFSA opinion on yohimbe; BfR Germany opinion",
        "export_guidance": "Verify supplement legality in destination country. UK/Canada require prescription-only status. US FDA has safety concerns but hasn't banned outright.",
    },
]


# ---------------------------------------------------------------------------
# Static regulatory data (no AI needed)
# ---------------------------------------------------------------------------

FORM_M_GUIDANCE: dict[str, Any] = {
    "title": "Nigeria Form M — Import Documentation Guide for Herb Exporters",
    "overview": (
        "Form M is a mandatory import finance document in Nigeria, processed through the "
        "Trade Monitoring System (TMS) of the Central Bank of Nigeria (CBN). "
        "It is the primary document for approving foreign exchange for import transactions. "
        "Herb exporters dealing with Nigerian buyers must understand Form M to facilitate smooth payment."
    ),
    "who_needs_it": "Any Nigerian importer paying for goods worth USD 500 or above must open a Form M before shipment.",
    "steps": [
        {
            "step": 1,
            "title": "Pre-shipment: Buyer Opens Form M",
            "description": "The Nigerian importer (your buyer) must open a Form M through their bank (an authorised dealer bank) BEFORE goods are shipped.",
            "requirements": ["Proforma invoice from seller", "Import duty classification (HS code)", "Insurance certificate", "Standard Organisation of Nigeria (SON) Form D (for regulated goods)"],
            "responsible_party": "Nigerian importer / buyer",
            "timeline": "5–10 working days",
        },
        {
            "step": 2,
            "title": "Bank Accreditation",
            "description": "The buyer's bank reviews and accredits the Form M, assigning a unique Form M number. The bank sets aside the foreign exchange.",
            "requirements": ["Valid Form M application", "Sufficient account balance or credit facility", "NAFDAC Import Permit (for herbal products)"],
            "responsible_party": "Buyer's authorised dealer bank",
            "timeline": "2–5 working days",
        },
        {
            "step": 3,
            "title": "Pre-shipment Inspection (CISS)",
            "description": "For goods above USD 3,000, Nigeria mandates a Combined Inspection, Scanning and Scanning (CISS) certificate from an approved inspection company (SGS, Bureau Veritas, Cotecna, OMIC, or Intertek).",
            "requirements": ["Combined Certificate of Value and Origin (CCVO)", "Clean Report of Findings (CRF)", "Risk Assessment Report (RAR)"],
            "responsible_party": "Seller (exporter) in origin country",
            "timeline": "3–7 working days",
        },
        {
            "step": 4,
            "title": "Shipment and Document Preparation",
            "description": "Ship goods and prepare all original shipping documents: commercial invoice, packing list, bill of lading/airway bill, certificate of origin, phytosanitary certificate, and CISS CRF.",
            "requirements": ["Commercial invoice (showing Form M number)", "Bill of Lading / Airway Bill", "Packing List", "Certificate of Origin", "Phytosanitary Certificate (NAQS)", "CISS Clean Report of Findings"],
            "responsible_party": "Seller (exporter)",
            "timeline": "At time of shipment",
        },
        {
            "step": 5,
            "title": "Document Presentation to Buyer's Bank",
            "description": "Present all original shipping documents to the buyer's bank within the documentary credit timeline. The bank verifies documents against Form M requirements.",
            "requirements": ["All original shipping documents", "Letter of credit / payment instruction", "Insurance certificate"],
            "responsible_party": "Seller's bank / seller",
            "timeline": "Within LC validity period (usually 21 days from B/L date)",
        },
        {
            "step": 6,
            "title": "Customs Clearance at Nigerian Port",
            "description": "Buyer's customs agent files Single Goods Declaration (SGD) on Nigeria Customs Service eTICS system. Form M number referenced on SGD.",
            "requirements": ["Form M number on SGD", "Original CRF from inspection company", "All shipping documents", "NAFDAC Import Permit (for herbal/pharmaceutical products)"],
            "responsible_party": "Nigerian importer and their customs agent",
            "timeline": "5–15 working days at port",
        },
        {
            "step": 7,
            "title": "Foreign Exchange Repatriation",
            "description": "After customs clearance, buyer's bank releases foreign exchange to seller's bank. Form M is retired.",
            "requirements": ["Proof of customs clearance", "Final commercial invoice", "Bank-to-bank SWIFT payment"],
            "responsible_party": "Buyer's bank",
            "timeline": "3–10 working days after document acceptance",
        },
    ],
    "required_documents": [
        "Proforma Invoice with HS code",
        "Combined Certificate of Value and Origin (CCVO)",
        "Clean Report of Findings (CRF) from approved inspection company",
        "Commercial Invoice (showing Form M number)",
        "Bill of Lading or Airway Bill",
        "Packing List",
        "Certificate of Origin (preferably Form A for GSP)",
        "NAQS Phytosanitary Certificate",
        "NAFDAC Import Permit (for herbal products)",
        "Insurance Certificate",
        "Standard Organisation of Nigeria (SON) Form D (where applicable)",
    ],
    "fees": [
        {"fee_name": "CISS Inspection Fee", "amount": "Approximately 1% of FOB value", "paid_by": "Importer (built into price)"},
        {"fee_name": "Bank Processing Fee (Form M)", "amount": "0.5–1% of transaction value", "paid_by": "Nigerian importer"},
        {"fee_name": "Import Duty", "amount": "Varies by HS code (Nigerian Customs Tariff)", "paid_by": "Nigerian importer"},
        {"fee_name": "VAT on Import", "amount": "7.5% of CIF value + duty", "paid_by": "Nigerian importer"},
        {"fee_name": "NAFDAC Import Permit", "amount": "₦10,000–₦50,000 depending on product", "paid_by": "Nigerian importer"},
    ],
    "processing_time": "Total Form M cycle: 3–6 weeks from opening to FX release (can be longer at congested ports)",
    "tips": [
        "Always include the Form M number on your commercial invoice — failure to do so will delay payment.",
        "Use the same HS code on all documents (proforma, commercial invoice, packing list, CISS CRF). Any discrepancy triggers queries.",
        "For first-time Nigerian buyers, request 30–50% advance payment via TT before opening Form M to reduce payment risk.",
        "NAFDAC Import Permit must be obtained BEFORE Form M is opened — buyers often delay this step.",
        "Work with a licensed Nigerian freight forwarder who understands CISS and e-customs requirements.",
    ],
    "key_agencies": ["Central Bank of Nigeria (CBN)", "Nigerian Customs Service (NCS)", "NAFDAC", "Standard Organisation of Nigeria (SON)", "Nigerian Ports Authority (NPA)"],
    "useful_links": ["cbn.gov.ng", "customs.gov.ng", "nafdac.gov.ng"],
}

NEPC_EXPORT_GUIDE: dict[str, Any] = {
    "title": "NEPC Export Registration Guide for Nigerian Herb Exporters",
    "overview": (
        "The Nigerian Export Promotion Council (NEPC) is the government agency that promotes, "
        "develops, and diversifies Nigeria's non-oil exports. All herb exporters must register "
        "with NEPC to obtain the Export Permit/Certificate required for Customs export declaration."
    ),
    "why_register": [
        "Mandatory for obtaining NXP (Nigerian Export Proceeds) form from your bank",
        "Required for all export documentation and certificates of origin",
        "Access to NEPC export development grants and market linkage programmes",
        "NEPC registration is required for SON and NAFDAC export processes",
    ],
    "steps": [
        {
            "step": 1,
            "title": "Obtain CAC Certificate of Incorporation",
            "description": "Register your business with the Corporate Affairs Commission (CAC). You need a valid RC number before NEPC registration.",
            "documents": ["CAC Certificate", "Memorandum and Articles of Association", "Tax Identification Number (TIN) from FIRS"],
            "fees": "CAC registration: ₦25,000–₦85,000 depending on company type",
            "duration": "3–10 working days (online via CAC portal)",
        },
        {
            "step": 2,
            "title": "Register on NEPC Portal (nepc.gov.ng)",
            "description": "Create an exporter account on the NEPC e-portal. Fill in company details, bank details, and export product category.",
            "documents": ["CAC Certificate", "TIN", "Bank account details in exporter's company name", "Company stamp and letterhead"],
            "fees": "Registration fee: ₦10,000 (initial); Annual renewal: ₦5,000",
            "duration": "1–3 working days",
        },
        {
            "step": 3,
            "title": "Obtain Export Certificate",
            "description": "After registration, apply for an Export Certificate for each shipment or obtain a blanket certificate for the product category. This serves as proof of legitimate Nigerian exporter status.",
            "documents": ["NEPC Exporter registration certificate", "Completed export application form", "Invoice and product details"],
            "fees": "₦5,000–₦15,000 per certificate (volume-based)",
            "duration": "1–2 working days",
        },
        {
            "step": 4,
            "title": "Obtain Nigerian Export Proceeds (NXP) Form",
            "description": "After NEPC registration, take your NEPC certificate to your authorised dealer bank to complete the NXP form. This CBN form tracks export proceeds repatriation.",
            "documents": ["NEPC Export Certificate", "Commercial Invoice", "Proforma Invoice", "Contract or Purchase Order from buyer"],
            "fees": "Bank processing fee: 0.25–0.5% of export value",
            "duration": "1–3 working days at the bank",
        },
        {
            "step": 5,
            "title": "Obtain NAQDAC Export Permit (for herbal/medicinal products)",
            "description": "Herbal products require NAFDAC Export Permit in addition to NEPC. Apply at the NAFDAC Export/Import division with product sample and safety data.",
            "documents": ["NEPC Certificate", "NAFDAC product registration certificate (if product is registered)", "Safety data sheet", "Product label/artwork", "CoA from accredited lab", "Company profile"],
            "fees": "₦20,000–₦100,000 depending on product type",
            "duration": "2–4 weeks",
        },
        {
            "step": 6,
            "title": "Obtain NAQS Phytosanitary Certificate",
            "description": "All plant-based exports must have a Phytosanitary Certificate from the Nigerian Agricultural Quarantine Service (NAQS) confirming the product is free from pests and diseases.",
            "documents": ["NEPC Certificate", "NAQS application form", "Product sample for inspection", "Packing list and invoice"],
            "fees": "₦5,000–₦25,000 per shipment (weight-based)",
            "duration": "3–7 working days (requires physical inspection)",
        },
        {
            "step": 7,
            "title": "NCS Customs Export Declaration (Form NXP/SGD)",
            "description": "File Single Goods Declaration (SGD) with Nigerian Customs Service via the eTICS system, attaching all documents. Pay export levy if applicable.",
            "documents": ["All of the above certificates", "Commercial invoice", "Bill of Lading / Airway Bill", "Packing List", "Completed SGD form"],
            "fees": "Export levy: 0.5% of FOB value for processed goods; 1% for raw materials (to discourage raw material export)",
            "duration": "1–3 working days",
        },
        {
            "step": 8,
            "title": "Repatriate Export Proceeds",
            "description": "After receiving payment, repatriate 100% of foreign exchange proceeds within 90 days. Report to your bank via NXP retirement. Failure attracts CBN penalties.",
            "documents": ["Bank SWIFT confirmation", "NXP form", "Commercial invoice"],
            "fees": "No fee — mandatory obligation",
            "duration": "Within 90 days of shipment date",
        },
    ],
    "contact": {
        "headquarters": "NEPC Head Office, Wuse Zone 5, Abuja, Nigeria",
        "phone": "+234-9-290-0168",
        "email": "info@nepc.gov.ng",
        "website": "nepc.gov.ng",
        "state_offices": "Lagos, Kano, Port Harcourt, Onitsha, Ibadan — check nepc.gov.ng for addresses",
    },
    "notes": [
        "NEPC offers free export training and capacity building for registered exporters — take advantage.",
        "The NEPC Export Grant (NEXIM Bank backed) provides up to ₦50M for qualifying SME exporters.",
        "Processed/value-added exports attract lower export levy (0.5%) vs raw herbs (1%) — add value to maximise returns.",
        "Maintain clean NXP retirement records — CBN audits exporters, and failure to repatriate leads to bank blacklisting.",
        "NEPC can assist with Certificates of Origin for GSP/AGOA duty preferences — ensure you use this.",
    ],
}

CBN_REPATRIATION_DATA: dict[str, Any] = {
    "title": "CBN Foreign Exchange Repatriation Requirements for Nigerian Herb Exporters",
    "overview": (
        "The Central Bank of Nigeria (CBN) mandates that all export proceeds in foreign currency "
        "be repatriated to Nigeria within a prescribed timeframe. This is enforced through the "
        "Nigerian Export Proceeds (NXP) form system and monitored by the CBN Trade and Exchange Department. "
        "Non-compliance results in severe penalties including bank account restrictions and export bans."
    ),
    "requirements": [
        {
            "requirement": "100% Repatriation",
            "detail": "All foreign currency earned from herb exports must be repatriated in full. Partial repatriation is not permitted.",
            "regulatory_basis": "CBN Foreign Exchange Manual (Revised Edition 2018), Section 3",
        },
        {
            "requirement": "90-Day Repatriation Window",
            "detail": "Export proceeds must be repatriated within 90 days of the shipment date as evidenced on the bill of lading or airway bill.",
            "regulatory_basis": "CBN Circular TED/FEM/GEN/01/008 — 90-day repatriation rule",
        },
        {
            "requirement": "NXP Form Completion",
            "detail": "Complete the Nigerian Export Proceeds (NXP) form with your Authorised Dealer Bank BEFORE export. The NXP number must appear on all shipping and customs documents.",
            "regulatory_basis": "CBN Foreign Exchange Manual; NEPC Act",
        },
        {
            "requirement": "NXP Form Retirement",
            "detail": "Upon receiving payment, present proof of payment (SWIFT MT103 or bank credit advice) to your bank to 'retire' the NXP. This is your compliance record.",
            "regulatory_basis": "CBN Foreign Exchange Manual",
        },
        {
            "requirement": "Approved Currency Accounts",
            "detail": "Proceeds must be credited to your Domiciliary Account (DOM account) with an authorised dealer bank in Nigeria. USD, GBP, EUR, and CNY accounts are accepted.",
            "regulatory_basis": "CBN Guidelines on Domiciliary Accounts",
        },
        {
            "requirement": "REER / FX Conversion",
            "detail": "You may retain 100% of proceeds in your domiciliary account or convert to naira at FMDQ/I&E window rate. CBN no longer forces conversion (as of 2023 reforms).",
            "regulatory_basis": "CBN Circular on FX Market Operations (June 2023 reforms)",
        },
        {
            "requirement": "Letter of Credit (LC) Preferred",
            "detail": "CBN strongly recommends LC transactions for large export deals. LC backed by a confirmed irrevocable LC from a first-class bank protects both parties and simplifies NXP retirement.",
            "regulatory_basis": "CBN Foreign Exchange Manual; UCP 600",
        },
    ],
    "timeline": "Repatriation must occur within 90 calendar days from shipment date. Extensions may be granted by CBN (write formally before deadline).",
    "penalties": [
        "Restriction on access to foreign exchange from the official market for defaulting exporters",
        "Blacklisting from future export transactions through the NXP system",
        "Fines of up to 2× the unremitted export proceeds",
        "Criminal prosecution under the Foreign Exchange (Monitoring and Miscellaneous Provisions) Act",
        "Suspension of export licence and NEPC certificate",
    ],
    "forex_accounts": [
        "USD Domiciliary Account — most commonly used for herb exports",
        "EUR Domiciliary Account — for EU buyers paying in EUR",
        "GBP Domiciliary Account — for UK buyers",
        "CNY (Renminbi) Account — for Chinese buyers under China–Nigeria bilateral framework",
    ],
    "payment_instruments": [
        "Irrevocable Documentary Letter of Credit (LC) — MOST SECURE",
        "Confirmed LC from first-class international bank",
        "Telegraphic Transfer (TT) / Wire Transfer — common for trusted buyers",
        "Documentary Collection (D/P, D/A) — moderate security",
        "Open Account — HIGHEST RISK; avoid unless long-established relationship",
    ],
    "tips": [
        "Always insist on advance payment (30–50%) or a confirmed LC for first-time buyers.",
        "File your NXP form BEFORE shipment — shipping without NXP number can delay customs clearance.",
        "Keep all payment SWIFT receipts (MT103) — these are your primary evidence for NXP retirement.",
        "If payment is delayed beyond 60 days, write to CBN Trade & Exchange Dept for a formal extension BEFORE the 90-day deadline.",
        "CBN 2023 reforms now allow exporters to retain USD in DOM accounts indefinitely — you are not forced to convert to naira at unfavourable rates.",
        "Work with a forex-savvy commercial bank relationship manager who understands trade finance — FCMB, Zenith, GTB, and FirstBank have strong trade desks.",
        "For high-value shipments (USD 100,000+), consider NEXIM Bank's export credit insurance to protect against buyer default.",
    ],
    "key_contacts": {
        "CBN Trade and Exchange Dept": "trade.exchange@cbn.gov.ng | cbn.gov.ng",
        "NEXIM Bank (export credit)": "info@nexim.gov.ng | nexim.gov.ng",
        "NEPC (NXP coordination)": "info@nepc.gov.ng | nepc.gov.ng",
    },
}


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_HS_CODE_PROMPT = """
You are a certified Nigerian customs tariff classifier and international trade specialist
with deep knowledge of the WCO Harmonized System (2022 edition) and the Nigerian Customs Tariff.

Classify this Nigerian herb product:
- Herb name: {herb_name}
- Form / presentation: {form}

Determine the correct 10-digit HS code under the Nigerian Customs Tariff.
Primary chapters to check: Chapter 09 (spices), Chapter 12 (medicinal plants, oil seeds),
Chapter 13 (plant extracts, gums), Chapter 15 (fixed vegetable oils), Chapter 33 (essential oils).

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "herb_name": "{herb_name}",
  "form": "{form}",
  "hs_code": "<correct 10-digit HS code e.g. 1211.90.90>",
  "hs_chapter": "<chapter number and title>",
  "description": "<official HS description of this heading/subheading>",
  "classification_notes": "<why this code applies — mention any exclusion notes or General Rules of Interpretation used>",
  "duty_rate_eu_percent": <EU MFN duty rate as number — 0 if duty-free>,
  "duty_rate_us_percent": <US MFN (Column 1 general) duty rate as number — 0 if duty-free>,
  "duty_rate_china_percent": <China MFN duty rate as number>,
  "duty_rate_uk_percent": <UK Global Tariff rate as number>,
  "gsp_eligible": <true if Nigeria qualifies for duty preference — most agricultural products are true>,
  "agoa_eligible": <true for US AGOA (most Nigerian agricultural/botanical products)>,
  "epa_eligible": <true if eligible under EU-ECOWAS Economic Partnership Agreement preferences>,
  "notes": "<practical export guidance including any anti-dumping, quota, or certification requirements>",
  "alternative_codes": ["<alternative HS code if form changes e.g. extract vs dried herb>"],
  "certifications_required": ["<cert 1>", "<cert 2>"]
}}
"""

_DUTIES_CALC_PROMPT = """
You are an expert international customs duties calculator specialising in agricultural and
botanical product imports worldwide.

Calculate the complete import cost breakdown for:
- HS Code: {hs_code}
- Destination country: {destination_country}
- FOB value: USD {value_usd}
- Product type: Nigerian herb/botanical export

Provide a detailed duty and landed-cost calculation.

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "hs_code": "{hs_code}",
  "destination_country": "{destination_country}",
  "fob_value_usd": {value_usd},
  "estimated_freight_usd": <realistic sea freight estimate for this product/destination>,
  "estimated_insurance_usd": <0.5-1.5% of CIF value>,
  "cif_value_usd": <FOB + freight + insurance>,
  "import_duty_percent": <applicable MFN or preferential rate for Nigeria>,
  "import_duty_usd": <calculated duty amount>,
  "preference_applied": "<GSP / AGOA / EPA / MFN — which rate applied and why>",
  "vat_on_import_percent": <destination country VAT/GST on imports>,
  "vat_on_import_usd": <calculated VAT amount>,
  "customs_processing_fee_usd": <customs handling/processing fee for that country>,
  "port_handling_fee_usd": <typical port charges>,
  "anti_dumping_duty_usd": <0 unless applicable for this product/country combination>,
  "anti_dumping_notes": "<null or explanation if applicable>",
  "other_levies": [
    {{"name": "<levy name>", "rate": "<rate or fixed>", "amount_usd": <amount>}}
  ],
  "total_landed_cost_usd": <full sum of all charges>,
  "effective_duty_rate_percent": <total duties+levies as % of FOB value>,
  "notes": "<practical advice e.g. customs valuation method, documentary requirements for duty preference>",
  "regulatory_requirements": ["<import requirement 1 for this country>", "<requirement 2>"]
}}
"""

_COUNTRY_REQUIREMENTS_PROMPT = """
You are an international trade regulatory specialist with expertise in import regulations
for botanical products, herbs, and nutraceuticals across global markets.

Provide comprehensive import requirements for:
- Destination country: {country}
- Herb/product: {herb}

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "country": "{country}",
  "herb": "{herb}",
  "regulatory_bodies": ["<primary regulatory body>", "<secondary body>"],
  "required_certifications": [
    {{"cert_name": "<certificate name>", "issuing_body": "<who issues it>", "mandatory": <true/false>, "notes": "<details>"}}
  ],
  "labeling_rules": [
    "<labeling requirement 1 — language, font size, mandatory statements>",
    "<labeling requirement 2>"
  ],
  "maximum_residue_limits": [
    {{"substance": "<pesticide/contaminant>", "limit_mg_per_kg": <number or null if unspecified>, "regulation": "<regulation reference>"}}
  ],
  "banned_substances": [
    {{"substance": "<substance name>", "reason": "<why banned>", "regulation": "<legal reference>"}}
  ],
  "port_of_entry_requirements": [
    "<requirement 1 — e.g. all herbal imports must enter via Rotterdam, Hamburg, or Antwerp in EU>",
    "<requirement 2>"
  ],
  "quarantine_rules": [
    "<quarantine requirement 1 — mandatory holding periods, treatment requirements>",
    "<requirement 2>"
  ],
  "import_licence_required": <true/false>,
  "import_licence_body": "<which body issues import licence if required>",
  "recommended_freight_agents": [
    "<generic freight agent type or well-known specialist e.g. 'Specialist botanical freight forwarder'>",
    "<port agent recommendation>"
  ],
  "special_requirements": "<any unique requirement for this country e.g. Novel Food in EU, Bioterrorism Act in US>",
  "processing_time_days": <typical customs clearance time in days>,
  "useful_contacts": ["<trade body>", "<government agency website>"]
}}
"""

_CHAT_PROMPT = """
You are NigerFlora BioSciences's Nigerian export customs expert — a seasoned specialist with 20+ years
of experience in Nigerian export procedures, international trade law, and herbal product trade.

You have deep, practical knowledge of:
- Nigerian Customs Service (NCS) export procedures and eTICS e-customs system
- NAFDAC export certification for herbal and pharmaceutical products
- Nigerian Export Promotion Council (NEPC) registration and NXP forms
- Nigerian Agricultural Quarantine Service (NAQS) phytosanitary requirements
- Central Bank of Nigeria (CBN) foreign exchange and repatriation rules
- HS classification for Nigerian herbs (Chapters 09, 12, 13, 15, 33)
- AGOA, EU GSP/EPA, and bilateral trade preferences for Nigeria
- Destination-country import regulations (EU, US, UK, China, Middle East, Asia)

User context:
{context_block}

User question: "{question}"

Provide a clear, practical, and accurate answer. Be specific to Nigeria — reference actual
agencies, forms, regulations, and procedures. Where fees or timelines are mentioned, give
realistic figures based on current Nigerian practice.

After your answer, suggest 2–3 focused follow-up questions the user would find useful.

Always cite the relevant Nigerian agencies involved in your answer (NCS, NAFDAC, NEPC, NAQS, or CBN).

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "answer": "<comprehensive answer — multiple paragraphs if needed>",
  "cited_agencies": ["<agency 1>", "<agency 2>"],
  "suggested_next_questions": [
    "<follow-up question 1>",
    "<follow-up question 2>",
    "<follow-up question 3>"
  ]
}}
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


def _call_claude_json(prompt: str, max_tokens: int = 2000) -> Any:
    client = _get_client()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Claude API error: {exc}",
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


def _lookup_seed(herb_name: str) -> dict[str, Any] | None:
    """Case-insensitive lookup in the in-memory HS code seed table."""
    key = herb_name.strip().lower()
    if key in _HS_INDEX:
        return _HS_INDEX[key]
    # Partial match — find first entry whose name contains the query
    for k, v in _HS_INDEX.items():
        if key in k or k in key:
            return v
    return None


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def get_hs_code(herb_name: str, form: str) -> dict[str, Any]:
    """
    Return HS code and duty information for a herb.
    Checks the seed table first (instant, free). Falls back to Claude if not found.
    """
    seed = _lookup_seed(herb_name)
    if seed:
        # Return a normalised response from seed data
        return {
            "herb_name": seed["herb_name"],
            "form": form or seed["common_forms"][0],
            "hs_code": seed.get("hs_code_processed", seed["hs_code"]) if form and any(
                kw in form.lower() for kw in ["extract", "oil", "processed", "powder", "ground"]
            ) else seed["hs_code"],
            "hs_chapter": seed["hs_chapter"],
            "description": seed["description"],
            "classification_notes": f"Matched from NigerFlora BioSciences HS Code seed table. Form: {form}.",
            "duty_rate_eu_percent": seed.get("duty_rate_eu_percent", 0),
            "duty_rate_us_percent": seed.get("duty_rate_us_percent", 0),
            "duty_rate_china_percent": seed.get("duty_rate_china_percent", 5),
            "duty_rate_uk_percent": seed.get("duty_rate_eu_percent", 0),  # UK follows EU post-Brexit closely
            "gsp_eligible": seed.get("gsp_eligible", True),
            "agoa_eligible": seed.get("agoa_eligible", True),
            "epa_eligible": True,  # Nigeria is ECOWAS EPA member
            "notes": seed.get("notes", ""),
            "alternative_codes": [seed.get("hs_code_processed", seed["hs_code"])],
            "certifications_required": seed.get("certifications_required", []),
            "source": "seed_table",
        }

    # Fallback: ask Claude
    result = _call_claude_json(
        _HS_CODE_PROMPT.format(herb_name=herb_name, form=form),
        max_tokens=1200,
    )
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for HS code lookup.",
        )
    result.setdefault("source", "ai_generated")
    return result


def calculate_import_duties(
    hs_code: str,
    destination_country: str,
    value_usd: float,
) -> dict[str, Any]:
    """
    AI calculates full import duty breakdown: duty, VAT, fees, anti-dumping, total landed cost.
    """
    prompt = _DUTIES_CALC_PROMPT.format(
        hs_code=hs_code,
        destination_country=destination_country,
        value_usd=value_usd,
    )
    result = _call_claude_json(prompt, max_tokens=1500)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for duty calculation.",
        )
    # Ensure required keys
    result.setdefault("hs_code", hs_code)
    result.setdefault("destination_country", destination_country)
    result.setdefault("fob_value_usd", value_usd)
    result.setdefault("other_levies", [])
    result.setdefault("anti_dumping_duty_usd", 0)
    return result


def get_country_import_requirements(country: str, herb: str) -> dict[str, Any]:
    """
    AI returns detailed import requirements for a specific country and herb.
    """
    prompt = _COUNTRY_REQUIREMENTS_PROMPT.format(
        country=country,
        herb=herb,
    )
    result = _call_claude_json(prompt, max_tokens=2000)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for country requirements.",
        )
    result.setdefault("country", country)
    result.setdefault("herb", herb)
    result.setdefault("required_certifications", [])
    result.setdefault("labeling_rules", [])
    result.setdefault("maximum_residue_limits", [])
    result.setdefault("banned_substances", [])
    result.setdefault("quarantine_rules", [])
    result.setdefault("recommended_freight_agents", [])
    return result


def customs_chat(question: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Claude acts as a Nigerian export customs expert.
    Returns dict with answer, cited_agencies, and suggested_next_questions.
    The router appends the standard disclaimer.
    """
    if context:
        lines = [f"- {k}: {v}" for k, v in context.items() if v]
        context_block = "\n".join(lines) if lines else "No additional context."
    else:
        context_block = "No additional context."

    prompt = _CHAT_PROMPT.format(
        question=question.strip(),
        context_block=context_block,
    )
    result = _call_claude_json(prompt, max_tokens=1500)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned unexpected structure for customs chat.",
        )
    result.setdefault("answer", "")
    result.setdefault("cited_agencies", [])
    result.setdefault("suggested_next_questions", [])
    return result
