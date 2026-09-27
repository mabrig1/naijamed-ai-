from __future__ import annotations

import json
import re
from typing import Any

from .core.config import settings


OFFICIAL_SOURCES: list[dict[str, Any]] = [
    {
        "id": "ich-e6-r3",
        "organization": "ICH",
        "title": "ICH E6(R3): Good Clinical Practice",
        "status": "final",
        "issued": "2026",
        "url": "https://www.ich.org/",
        "topic": "clinical_trials",
        "summary": (
            "International ethical, scientific and quality standard for trials involving human participants. "
            "Use it to structure quality-by-design, participant protection, investigator/sponsor responsibilities, "
            "data governance and risk-proportionate trial conduct. Verify the relevant annex and regional implementation."
        ),
    },
    {
        "id": "ich-m4-ctd",
        "organization": "ICH",
        "title": "M4: Common Technical Document (CTD)",
        "status": "final",
        "issued": "2000; maintained",
        "url": "https://www.ich.org/page/ctd",
        "topic": "regulatory_submission",
        "summary": (
            "Defines the harmonized CTD organization. Module 1 is region-specific; Modules 2-5 are common across ICH regions. "
            "Use for dossier architecture, not as a substitute for study-specific scientific requirements."
        ),
    },
    {
        "id": "ich-ectd-v4",
        "organization": "ICH",
        "title": "ICH eCTD v4.0 Implementation Guide v1.7",
        "status": "final",
        "issued": "2026-06",
        "url": "https://www.ich.org/page/ich-electronic-common-technical-document-ectd-v40",
        "topic": "regulatory_submission",
        "summary": (
            "Current ICH eCTD v4.0 implementation package endorsed in June 2026. "
            "Use with regional Module 1 implementation documents and controlled vocabulary requirements."
        ),
    },
    {
        "id": "fda-food-effect-2026",
        "organization": "FDA",
        "title": "Assessing the Effects of Food on Drugs in INDs and NDAs – Clinical Pharmacology Considerations",
        "status": "final",
        "issued": "2026-05",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/assessing-effects-food-drugs-inds-and-ndas-clinical-pharmacology-considerations",
        "topic": "clinical_pharmacology",
        "summary": (
            "Final FDA guidance for planning food-effect studies for orally administered drug products under INDs "
            "supporting NDAs and NDA supplements. Use the guidance scope carefully; ANDA fed-BE recommendations are handled elsewhere."
        ),
    },
    {
        "id": "fda-hepatic-pk-2026",
        "organization": "FDA",
        "title": "Pharmacokinetics in Patients with Impaired Hepatic Function: Study Design, Data Analysis, and Impact on Dosing and Labeling",
        "status": "draft",
        "issued": "2026-09",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/pharmacokinetics-patients-impaired-hepatic-function-study-design-data-analysis-and-impact-dosing-and",
        "topic": "clinical_pharmacology",
        "summary": (
            "September 2026 FDA draft guidance on assessing hepatic impairment effects on PK and, where appropriate, PD. "
            "It is distributed for comment and is not for implementation; label it as draft in any regulatory analysis."
        ),
    },
    {
        "id": "nih-application-guide-forms-i",
        "organization": "NIH",
        "title": "How to Apply – Application Guide, Forms-I",
        "status": "current_instructions",
        "issued": "2025-12",
        "url": "https://grants.nih.gov/grants-process/write-application/how-to-apply-application-guide",
        "topic": "grant",
        "summary": (
            "Current NIH/PHS application instructions for due dates on or after January 25, 2025. "
            "Use together with the specific Notice of Funding Opportunity (NOFO), which controls when instructions differ."
        ),
    },
    {
        "id": "nih-specific-aims",
        "organization": "NIH",
        "title": "NIH Advice on Application Sections – Specific Aims",
        "status": "current_guidance",
        "issued": "2026",
        "url": "https://grants.nih.gov/grants-process/write-application/advice-on-application-sections",
        "topic": "grant",
        "summary": (
            "NIH advises drafting Specific Aims early, focusing on hypothesis-based goals, expected outcomes and overall impact. "
            "The Specific Aims attachment is generally limited to one page; always check the NOFO."
        ),
    },
    {
        "id": "nih-page-limits",
        "organization": "NIH",
        "title": "NIH Page Limits",
        "status": "current_instructions",
        "issued": "2026-06-22",
        "url": "https://www.grants.nih.gov/grants-process/write-application/how-to-apply-application-guide/page-limits",
        "topic": "grant",
        "summary": (
            "Current NIH page-limit table. Specific Aims is one page. R21 Research Strategy is generally six pages, "
            "but combined activity codes or a specific NOFO may set different limits; the NOFO always supersedes the table."
        ),
    },
]


def official_sources() -> list[dict[str, Any]]:
    return [dict(row) for row in OFFICIAL_SOURCES]


def official_source_map() -> dict[str, dict[str, Any]]:
    return {row["id"]: dict(row) for row in OFFICIAL_SOURCES}


def validate_source_ids(source_ids: list[str]) -> list[dict[str, Any]]:
    by_id = official_source_map()
    rows: list[dict[str, Any]] = []
    for source_id in source_ids:
        source = by_id.get(source_id)
        if source:
            rows.append(source)
    return rows


def build_evidence_source(entry: dict[str, Any]) -> dict[str, Any]:
    extraction = entry.get("extraction") or {}
    findings = extraction.get("key_findings") or []
    return {
        "id": f"evidence:{entry['_id']}",
        "organization": "Research literature",
        "title": entry.get("title") or "Untitled evidence source",
        "status": "user_library",
        "issued": entry.get("published"),
        "url": f"https://doi.org/{entry.get('doi')}" if entry.get("doi") else None,
        "topic": "research_evidence",
        "summary": " ".join(str(item) for item in findings[:5]) or (
            f"Structured Formulary extraction. Study design: {extraction.get('study_design') or 'not extracted'}; "
            f"sample size: {extraction.get('sample_size') if extraction.get('sample_size') is not None else 'not extracted'}."
        ),
    }


def deterministic_gap_check(
    *,
    purpose: str,
    official_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    nofo_url: str | None,
) -> list[dict[str, str]]:
    source_ids = {row["id"] for row in official_rows}
    checks: list[dict[str, str]] = []

    def add(area: str, status: str, note: str) -> None:
        checks.append({"area": area, "status": status, "note": note})

    if purpose in {"specific_aims", "research_strategy", "grant_plan"}:
        add(
            "Funding opportunity instructions",
            "needs_input" if not nofo_url else "present",
            "Add the exact NOFO URL and confirm activity-code-specific requirements. The NOFO supersedes generic NIH guidance."
            if not nofo_url
            else "NOFO URL supplied; manually verify eligibility, due date, required attachments and special instructions.",
        )
        add(
            "Specific Aims format",
            "covered" if "nih-specific-aims" in source_ids or "nih-page-limits" in source_ids else "needs_source",
            "Specific Aims is generally one page; select current NIH instructions and verify the NOFO.",
        )
        if purpose == "research_strategy":
            add(
                "Research Strategy structure",
                "covered" if "nih-application-guide-forms-i" in source_ids else "needs_source",
                "NIH typically organizes Research Strategy around Significance, Innovation and Approach; verify activity-code instructions.",
            )
        add(
            "Literature support",
            "covered" if evidence_rows else "needs_input",
            "At least one user-library evidence source is available." if evidence_rows else "Link a Formulary literature review so scientific claims can be grounded in your own evidence base.",
        )

    if purpose in {"regulatory_brief", "ctd_plan", "protocol_outline", "compliance_gap"}:
        add(
            "Jurisdiction-specific requirements",
            "needs_input",
            "Confirm target regulator and regional requirements. ICH harmonization does not replace regional Module 1 or agency-specific requirements.",
        )
        add(
            "CTD architecture",
            "covered" if "ich-m4-ctd" in source_ids else "optional",
            "ICH M4 is selected." if "ich-m4-ctd" in source_ids else "Select ICH M4 when building a CTD/eCTD dossier architecture.",
        )
        add(
            "Guidance status",
            "warning" if any(row.get("status") == "draft" for row in official_rows) else "covered",
            "One or more selected sources are draft guidance and must not be presented as final requirements."
            if any(row.get("status") == "draft" for row in official_rows)
            else "No selected source is labeled draft.",
        )
        add(
            "Supporting evidence",
            "covered" if evidence_rows else "needs_input",
            "Formulary evidence is linked." if evidence_rows else "Link study evidence or a Formulary review before making product-specific scientific claims.",
        )

    return checks


def _fallback_draft(
    *,
    purpose: str,
    title: str,
    objective: str,
    notes: str | None,
    sources: list[dict[str, Any]],
    gaps: list[dict[str, str]],
) -> str:
    lines = [
        f"# {title}",
        "",
        f"**Purpose:** {purpose.replace('_', ' ')}",
        "",
        "## Objective",
        objective.strip(),
        "",
        "## Evidence-grounded working outline",
    ]
    if purpose == "specific_aims":
        lines.extend([
            "1. **Problem and significance.** Define the unmet scientific problem using selected evidence.",
            "2. **Central hypothesis / premise.** State a testable premise without overstating preliminary evidence.",
            "3. **Aim 1.** Define a bounded objective, approach and expected outcome.",
            "4. **Aim 2.** Define a complementary objective, approach and expected outcome.",
            "5. **Impact.** State what becomes possible if the aims succeed.",
        ])
    elif purpose == "research_strategy":
        lines.extend(["1. **Significance**", "2. **Innovation**", "3. **Approach**", "4. **Expected outcomes, risks and alternatives**"])
    elif purpose in {"ctd_plan", "regulatory_brief"}:
        lines.extend(["1. **Regulatory objective and jurisdiction**", "2. **Applicable guidance**", "3. **Evidence package**", "4. **Known gaps**", "5. **Submission / interaction plan**"])
    elif purpose == "protocol_outline":
        lines.extend(["1. **Objectives and endpoints**", "2. **Population and eligibility**", "3. **Design and interventions**", "4. **Safety and data quality**", "5. **Statistical analysis**", "6. **Ethics and oversight**"])
    else:
        lines.extend(["1. **Current state**", "2. **Applicable sources**", "3. **Gaps**", "4. **Actions and owners**"])

    if notes:
        lines.extend(["", "## Researcher notes", notes.strip()])

    lines.extend(["", "## Source notes"])
    for source in sources:
        lines.append(f"- [SRC:{source['id']}] {source['organization']} — {source['title']} ({source['status']}). {source.get('summary') or ''}")

    lines.extend(["", "## Gap flags"])
    for gap in gaps:
        lines.append(f"- **{gap['area']} — {gap['status']}:** {gap['note']}")

    lines.extend([
        "",
        "> Working draft only. Verify every requirement against the current official source, regional implementation documents and the specific NOFO or regulator before submission.",
    ])
    return "\n".join(lines)


def generate_grounded_draft(
    *,
    purpose: str,
    title: str,
    objective: str,
    notes: str | None,
    nofo_url: str | None,
    official_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    gaps: list[dict[str, str]],
) -> tuple[str, str, list[str]]:
    sources = official_rows + evidence_rows
    allowed_ids = {row["id"] for row in sources}
    fallback = _fallback_draft(
        purpose=purpose,
        title=title,
        objective=objective,
        notes=notes,
        sources=sources,
        gaps=gaps,
    )
    if not settings.effective_gemini_key or not sources:
        return fallback, "deterministic_template", sorted(allowed_ids)

    source_text = "\n\n".join(
        f"[SRC:{row['id']}]\nOrganization: {row['organization']}\nTitle: {row['title']}\n"
        f"Status: {row['status']}\nIssued: {row.get('issued')}\nURL: {row.get('url')}\n"
        f"Grounding summary: {row.get('summary') or ''}"
        for row in sources
    )
    gap_text = "\n".join(f"- {row['area']} [{row['status']}]: {row['note']}" for row in gaps)
    prompt = f"""
You are Formulary Regulatory & Grant Copilot for postgraduate pharmaceutical researchers.
Create a rigorous WORKING DRAFT, not a final regulatory or grant submission.

PURPOSE: {purpose}
TITLE: {title}
OBJECTIVE: {objective}
NOFO URL IF PROVIDED: {nofo_url or 'not provided'}
RESEARCHER NOTES: {notes or 'none'}

ALLOWED SOURCES:
{source_text}

PRECOMPUTED GAP FLAGS:
{gap_text}

Rules:
1. Use only claims supported by the allowed sources or explicitly supplied researcher notes.
2. Cite every source-dependent claim inline using the exact token [SRC:source-id].
3. Never invent or cite a source ID not listed above.
4. Preserve source status. If a source is draft guidance, say it is draft and not final.
5. For NIH work, state that the exact NOFO supersedes generic instructions.
6. For regulatory work, distinguish ICH harmonization from region-specific requirements.
7. Do not invent efficacy, safety, preliminary data, regulatory acceptance, eligibility or reviewer expectations.
8. Do not write patient-specific dosing advice.
9. Include a final section called "Verification before submission" listing unresolved checks.
10. Be concise enough to edit. This is a researcher-owned draft.

Return Markdown only.
"""
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.effective_gemini_key)
        model_name = settings.FORMULARY_LLM_MODEL or settings.CLINICAL_LLM_MODEL
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        raw = (getattr(response, "text", "") or "").strip()
        cited = set(re.findall(r"\[SRC:([^\]]+)\]", raw))
        if not raw or not cited or any(source_id not in allowed_ids for source_id in cited):
            return fallback, "deterministic_fallback", sorted(allowed_ids)
        return raw, f"gemini:{model_name}", sorted(cited)
    except Exception:
        return fallback, "deterministic_fallback", sorted(allowed_ids)
