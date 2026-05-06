"""
NEPC (Nigerian Export Promotion Council) Service — NaijaMed AI

NOTE: This is a MOCK implementation.
Replace mock responses with real NEPC API calls when portal access is obtained
from the NEPC e-portal: https://e-registration.nepc.gov.ng

Real NEPC API integration requires:
  1. Register at https://www.nepc.gov.ng/exporter-registration
  2. Obtain API credentials from NEPC IT department
  3. Use OAuth2 bearer token against base URL: https://api.nepc.gov.ng/v1
     (endpoint details TBD upon credential issuance)

Maintainer contact: exports-tech@naijamed.ai
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Registration status checker
# ---------------------------------------------------------------------------

_VALID_RC_PATTERN = re.compile(r"^RC\d{6,8}$", re.IGNORECASE)
_VALID_TIN_PATTERN = re.compile(r"^\d{10}$")


def check_nepc_registration_status(
    company_rc_number: str,
    tin: str | None = None,
) -> dict[str, Any]:
    """
    Mock: Check whether a company is registered as an NEPC exporter.

    Real implementation: GET /v1/exporters/{rc_number}/status
    with Authorization: Bearer <nepc_token>

    Returns a structured dict that mirrors the expected NEPC API response shape.
    """
    rc_clean = company_rc_number.strip().upper()
    is_valid_rc = bool(_VALID_RC_PATTERN.match(rc_clean))

    # Mock decision: companies whose RC number sums to even digits are "registered"
    digit_sum = sum(int(c) for c in rc_clean if c.isdigit())
    is_registered = is_valid_rc and (digit_sum % 2 == 0)

    # Deterministic expiry: 1 year from mock "registration" date
    mock_reg_date = date(2023, 1, 1) + timedelta(days=digit_sum * 7)
    mock_expiry_date = mock_reg_date + timedelta(days=365)

    return {
        "rc_number": rc_clean,
        "status": "registered" if is_registered else (
            "pending_verification" if is_valid_rc else "not_found"
        ),
        "company_name": f"[Mock] Company {rc_clean}",   # real API returns actual name
        "registration_date": str(mock_reg_date) if is_registered else None,
        "expiry_date": str(mock_expiry_date) if is_registered else None,
        "certificate_number": (
            f"NEPC/{rc_clean}/{mock_reg_date.year}/{digit_sum:04d}"
            if is_registered else None
        ),
        "export_categories": ["Non-Oil Commodities", "Agricultural Products"] if is_registered else [],
        "can_export_herbs": is_registered,
        "source": "MOCK — replace with real NEPC API call",
    }


# ---------------------------------------------------------------------------
# Non-oil export certificate template
# ---------------------------------------------------------------------------

def generate_nepc_certificate_template(
    exporter_name: str,
    company_rc_number: str,
    product_name: str,
    hs_code: str,
    quantity_kg: float,
    value_usd: float,
    destination_country: str,
    consignee_name: str,
) -> dict[str, Any]:
    """
    Generate a NEPC Non-Oil Export Certificate (NOEC) draft template.

    Real implementation: POST /v1/certificates/non-oil-export
    Certificate number issued by NEPC portal after submission.

    NOTE: This is a draft template. Actual certificate must be
    obtained from the NEPC portal at https://e-registration.nepc.gov.ng
    and bears the NEPC official seal + authorized signature.
    """
    cert_hash = hashlib.md5(
        f"{exporter_name}{company_rc_number}{product_name}{date.today()}".encode()
    ).hexdigest()[:8].upper()

    return {
        "certificate_type": "Non-Oil Export Certificate (NOEC)",
        "draft_number": f"NOEC-DRAFT-{cert_hash}",
        "status": "DRAFT — Pending NEPC Portal Submission",
        "issue_date": str(date.today()),
        "valid_until": str(date.today() + timedelta(days=90)),
        "issuing_authority": {
            "name": "Nigerian Export Promotion Council (NEPC)",
            "address": "41A Blantyre Street, Wuse 2, Abuja, FCT, Nigeria",
            "website": "https://www.nepc.gov.ng",
            "portal": "https://e-registration.nepc.gov.ng",
        },
        "exporter": {
            "name": exporter_name,
            "rc_number": company_rc_number.upper(),
            "country": "Nigeria",
        },
        "consignee": {
            "name": consignee_name,
            "destination_country": destination_country,
        },
        "commodity": {
            "description": product_name,
            "hs_code": hs_code,
            "quantity_kg": quantity_kg,
            "value_usd": round(value_usd, 2),
            "unit": "Kilogram (KG)",
            "origin": "Made in Nigeria",
        },
        "declaration": (
            "The exporter of the products covered by this document declares that, "
            "except where otherwise clearly indicated, these products are of Nigerian origin."
        ),
        "submission_steps": [
            "1. Log in to https://e-registration.nepc.gov.ng",
            "2. Navigate to 'Export Certificates' → 'Apply for NOEC'",
            "3. Upload this draft along with your NAFDAC certificate, invoice, and packing list",
            "4. Pay NEPC processing fee (₦15,000 per certificate)",
            "5. Await approval (usually 2–3 working days)",
            "6. Download official certificate with NEPC seal",
        ],
        "note": (
            "MOCK DRAFT — This template was generated by NaijaMed AI. "
            "The actual NEPC certificate can only be issued by NEPC staff "
            "through the official e-portal. Replace this mock with the real "
            "NEPC API integration when portal credentials are available."
        ),
    }


# ---------------------------------------------------------------------------
# Step-by-step NEPC registration guide
# ---------------------------------------------------------------------------

NEPC_REGISTRATION_GUIDE: dict[str, Any] = {
    "title": "NEPC Exporter Registration Guide",
    "overview": (
        "The Nigerian Export Promotion Council (NEPC) requires all Nigerian exporters "
        "to register before engaging in non-oil commodity exports. Registration is valid "
        "for one year and is renewable. Herbal medicine and agricultural product exporters "
        "fall under Category B (Non-Oil Commodities)."
    ),
    "registration_steps": [
        {
            "step": 1,
            "title": "Pre-Registration Requirements",
            "timeline": "1–2 weeks",
            "requirements": [
                "Valid CAC Certificate of Incorporation (RC Number)",
                "FIRS Tax Identification Number (TIN)",
                "Valid means of ID for all directors (NIN, International Passport, or Driver's License)",
                "Company bank account with a CBN-licensed bank",
                "NAFDAC product registration certificate (for herbal products)",
                "Standard Organisation of Nigeria (SON) certification where applicable",
            ],
            "tips": "Ensure all CAC documents are up to date before applying. Outdated docs cause delays.",
        },
        {
            "step": 2,
            "title": "Online Application via NEPC e-Portal",
            "timeline": "1 day",
            "requirements": [
                "Visit https://e-registration.nepc.gov.ng",
                "Click 'Register as an Exporter'",
                "Fill in company details, directors, and product categories",
                "Upload all required documents (PDF, max 2MB each)",
                "Select 'Non-Oil Agricultural Products' as export category",
                "Submit application and note your Application Reference Number",
            ],
            "tips": "Use Chrome or Firefox. The portal may be slow — submit during off-peak hours (early morning).",
        },
        {
            "step": 3,
            "title": "Processing & Document Verification",
            "timeline": "5–10 working days",
            "requirements": [
                "NEPC officers review submitted documents",
                "You may receive a request for additional documents via email",
                "Physical inspection of premises may be required for large exporters",
            ],
            "tips": "Check your email and the portal daily. Respond promptly to any additional document requests.",
        },
        {
            "step": 4,
            "title": "Fee Payment",
            "timeline": "Same day",
            "requirements": [
                "Annual registration fee: ₦50,000 (SME) / ₦150,000 (large enterprise)",
                "Pay via the NEPC e-portal using Remita or bank transfer",
                "Upload payment receipt to the portal",
            ],
            "tips": "Keep payment receipt — required for future certificate applications.",
        },
        {
            "step": 5,
            "title": "Certificate Collection",
            "timeline": "2–3 working days after payment",
            "requirements": [
                "Download NEPC Exporter Certificate from the portal",
                "Certificate is valid for 12 months from issue date",
                "Present certificate at port of export alongside other shipping documents",
            ],
            "tips": "Download and store a backup PDF. Keep physical copies for your shipping agent.",
        },
        {
            "step": 6,
            "title": "Annual Renewal",
            "timeline": "30 days before expiry",
            "requirements": [
                "Log into the portal and click 'Renew Registration'",
                "Submit updated documents if any have changed",
                "Pay annual renewal fee",
                "Submit export performance report for the previous year",
            ],
            "tips": "Set a calendar reminder 60 days before expiry. Late renewal causes export suspension.",
        },
    ],
    "fees": {
        "new_registration_sme": "₦50,000 (companies with annual turnover < ₦100M)",
        "new_registration_large": "₦150,000 (companies with annual turnover ≥ ₦100M)",
        "annual_renewal": "Same as new registration fee",
        "non_oil_export_certificate": "₦15,000 per certificate",
        "duplicate_certificate": "₦5,000",
    },
    "contact": {
        "head_office": "41A Blantyre Street, Wuse 2, Abuja",
        "phone": "+234 9 290 0256",
        "email": "info@nepc.gov.ng",
        "portal": "https://e-registration.nepc.gov.ng",
        "whatsapp_helpdesk": "+234 800 NEPC NGR (mock)",
    },
    "key_tips": [
        "NEPC registration is separate from NAFDAC registration — you need both for herbal exports.",
        "Your NEPC certificate must be presented at the port alongside your packing list and invoice.",
        "Exporters who miss their annual export performance filing are suspended from the registry.",
        "The Form NXP (forex repatriation) must be linked to your NEPC exporter code.",
        "NEPC offers free market linkage services — use their buyer database to find international buyers.",
    ],
    "source": "NEPC Official Guides (2024) — https://www.nepc.gov.ng/publications",
}


def get_nepc_registration_guide() -> dict[str, Any]:
    """Return the structured NEPC registration guide."""
    return NEPC_REGISTRATION_GUIDE
