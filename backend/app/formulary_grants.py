from __future__ import annotations

from typing import Any


PROJECT_TEMPLATES: dict[str, dict[str, Any]] = {
    "flagship_research": {
        "label": "Flagship international research programme",
        "recommended_sections": [
            "problem_statement", "scientific_aim", "specific_objectives", "work_packages",
            "consortium", "capacity_building", "impact", "sustainability", "risk_management",
        ],
    },
    "consortium": {
        "label": "Multi-institution consortium proposal",
        "recommended_sections": [
            "call_fit", "excellence", "methodology", "partners", "work_packages",
            "governance", "impact", "implementation", "budget",
        ],
    },
    "implementation": {
        "label": "Implementation / health systems grant",
        "recommended_sections": [
            "implementation_problem", "context", "intervention", "outcomes",
            "implementation_strategy", "equity", "economics", "scale_up",
        ],
    },
    "fellowship": {
        "label": "Research fellowship / investigator award",
        "recommended_sections": [
            "research_vision", "candidate_fit", "scientific_plan", "training_plan",
            "mentorship", "outputs", "career_development",
        ],
    },
    "infrastructure": {
        "label": "Research infrastructure / capacity grant",
        "recommended_sections": [
            "capacity_gap", "infrastructure_case", "users", "governance",
            "maintenance", "training", "sustainability", "value_for_money",
        ],
    },
}


def project_template(kind: str) -> dict[str, Any]:
    return dict(PROJECT_TEMPLATES.get(kind, PROJECT_TEMPLATES["flagship_research"]))


def normalize_percentages(work_packages: list[dict[str, Any]], total_budget: float | int | None) -> list[dict[str, Any]]:
    if not total_budget or total_budget <= 0:
        return [dict(row, budget_percent=None) for row in work_packages]
    output = []
    for row in work_packages:
        value = float(row.get("budget_amount") or 0)
        output.append(dict(row, budget_percent=round((value / float(total_budget)) * 100, 2)))
    return output


def readiness_assessment(
    project: dict[str, Any],
    *,
    partners: list[dict[str, Any]],
    work_packages: list[dict[str, Any]],
    milestones: list[dict[str, Any]],
    ip_assets: list[dict[str, Any]],
    disclosures: list[dict[str, Any]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(key: str, label: str, points: int, ok: bool, note: str) -> None:
        checks.append({
            "key": key,
            "label": label,
            "points": points,
            "earned": points if ok else 0,
            "status": "ready" if ok else "gap",
            "note": note,
        })

    objectives = project.get("objectives") or []
    total_budget = float(project.get("budget_amount") or 0)
    wp_budget = sum(float(row.get("budget_amount") or 0) for row in work_packages)
    committed_partners = [row for row in partners if row.get("status") in {"committed", "confirmed"}]
    international_partners = [row for row in partners if row.get("country") and str(row.get("country")).lower() != str(project.get("country") or "").lower()]
    dated_milestones = [row for row in milestones if row.get("due_on")]
    origin_assets = [row for row in ip_assets if row.get("category") in {"background_ip", "proposal", "software", "method", "dataset", "partner_relationship"}]

    add("summary", "Clear project summary", 8, len(str(project.get("summary") or "").strip()) >= 200,
        "Write a concise funder-facing summary of at least ~200 characters.")
    add("problem", "Problem and significance", 8, len(str(project.get("problem_statement") or "").strip()) >= 250,
        "Define the problem, evidence gap and why the project matters internationally.")
    add("objectives", "Specific objectives", 8, len(objectives) >= 3,
        "Add at least three specific objectives that can map to work packages.")
    add("funder", "Named funding target", 8, bool(project.get("funder_name")) and bool(project.get("call_url") or project.get("call_reference")),
        "Record the target funder plus call URL/reference; exact call rules should drive the final application.")
    add("deadline", "Submission deadline", 5, bool(project.get("deadline")),
        "Record the official deadline and confirm timezone/submission portal requirements.")
    add("workpackages", "Work-package architecture", 12, len(work_packages) >= 3,
        "Build at least three work packages with lead, outputs and budget.")
    add("budget", "Budget architecture", 8, total_budget > 0 and wp_budget > 0,
        "Add a total project budget and allocate meaningful amounts across work packages.")
    add("budget_match", "Budget reconciliation", 4, total_budget > 0 and abs(wp_budget - total_budget) / total_budget <= 0.10,
        "Bring work-package totals within 10% of the project budget before submission.")
    add("partners", "Consortium depth", 8, len(partners) >= 3,
        "Identify at least three delivery partners with differentiated roles.")
    add("international", "International partnership", 6, len(international_partners) >= 1,
        "Add at least one international partner for an international consortium proposal.")
    add("commitment", "Partner commitment", 5, len(committed_partners) >= 1,
        "Move at least one partner from prospect/contacted to committed/confirmed.")
    add("milestones", "Delivery milestones", 7, len(milestones) >= 4 and len(dated_milestones) >= 2,
        "Add delivery milestones and date the critical path.")
    add("background_ip", "Background-IP record", 8, len(origin_assets) >= 1,
        "Record pre-existing proposal, method, software, dataset or relationship assets before wider disclosure.")
    add("disclosure_log", "Controlled-disclosure log", 5, len(disclosures) >= 1,
        "Log each substantial disclosure: recipient, date, material/version, purpose and confidentiality basis.")

    score = sum(row["earned"] for row in checks)
    max_score = sum(row["points"] for row in checks)
    percent = round((score / max_score) * 100) if max_score else 0
    stage = "submission_ready" if percent >= 85 else "consortium_building" if percent >= 65 else "concept_development" if percent >= 40 else "early_concept"

    risks = []
    if not origin_assets:
        risks.append("No background-IP record is stored. Establish dated pre-existing assets before wider institutional/partner disclosure.")
    if disclosures and not any(row.get("confidentiality_basis") for row in disclosures):
        risks.append("Disclosures exist without a recorded confidentiality/non-use basis.")
    if project.get("deadline") and not dated_milestones:
        risks.append("A deadline is recorded but no dated implementation/submission milestones exist.")
    if total_budget and wp_budget > total_budget * 1.10:
        risks.append("Work-package budgets materially exceed the stated total project budget.")
    if len(partners) and not committed_partners:
        risks.append("Consortium contains prospects but no committed partner yet.")

    return {
        "score": percent,
        "stage": stage,
        "earned_points": score,
        "max_points": max_score,
        "checks": checks,
        "risks": risks,
        "budget": {
            "project_total": total_budget,
            "work_package_total": round(wp_budget, 2),
            "unallocated": round(total_budget - wp_budget, 2) if total_budget else None,
        },
    }


def disclosure_watermark(project: dict[str, Any], version: str | None = None) -> str:
    title = str(project.get("title") or "Grant Project").strip()
    owner = str(project.get("originator_name") or "Project originator").strip()
    project_id = str(project.get("_id") or "")
    suffix = f" · Version {version}" if version else ""
    return f"CONFIDENTIAL — CONTROLLED DISCLOSURE · {title} · Originator: {owner} · Project {project_id}{suffix}"


FUNDER_LENSES: dict[str, dict[str, Any]] = {
    "cross_funder": {
        "label": "Cross-funder international research lens",
        "verified_on": "2026-09-27",
        "sources": [
            {
                "organization": "European Commission",
                "label": "Horizon Europe proposal evaluation",
                "url": "https://research-and-innovation.ec.europa.eu/funding/how-projects-are-chosen-funding_en",
                "criteria": ["Excellence", "Impact", "Quality and efficiency of implementation"],
            },
            {
                "organization": "NIH",
                "label": "Simplified Review Framework",
                "url": "https://grants.nih.gov/policy-and-compliance/policy-topics/peer-review/simplifying-review/framework",
                "criteria": ["Importance of the Research", "Rigor and Feasibility", "Expertise and Resources"],
            },
            {
                "organization": "Wellcome",
                "label": "How Wellcome assesses funding applications",
                "url": "https://wellcome.org/research-funding/guidance/how-wellcome-makes-funding-decisions/how-wellcome-assesses-funding-applications",
                "criteria": ["Project", "Skills and experience", "Research environment"],
            },
        ],
        "notice": "This lens is a cross-funder preparation aid, not a substitute for the current call text or a prediction of funding.",
    },
    "horizon_europe": {
        "label": "Horizon Europe lens",
        "verified_on": "2026-09-27",
        "sources": [{
            "organization": "European Commission",
            "label": "Horizon Europe proposal evaluation",
            "url": "https://research-and-innovation.ec.europa.eu/funding/how-projects-are-chosen-funding_en",
            "criteria": ["Excellence", "Impact", "Quality and efficiency of implementation"],
        }],
        "notice": "Verify the exact topic, admissibility, eligibility and award criteria in the live Funding & Tenders call before submission.",
    },
    "nih": {
        "label": "NIH simplified review lens",
        "verified_on": "2026-09-27",
        "sources": [{
            "organization": "NIH",
            "label": "Simplified Review Framework",
            "url": "https://grants.nih.gov/policy-and-compliance/policy-topics/peer-review/simplifying-review/framework",
            "criteria": ["Importance of the Research", "Rigor and Feasibility", "Expertise and Resources"],
        }],
        "notice": "Verify that the target NOFO/activity code uses the simplified framework and follow Section V of the current opportunity.",
    },
    "wellcome": {
        "label": "Wellcome research funding lens",
        "verified_on": "2026-09-27",
        "sources": [{
            "organization": "Wellcome",
            "label": "How Wellcome assesses funding applications",
            "url": "https://wellcome.org/research-funding/guidance/how-wellcome-makes-funding-decisions/how-wellcome-assesses-funding-applications",
            "criteria": ["Project", "Skills and experience", "Research environment"],
        }],
        "notice": "Verify the current scheme page and call-specific criteria before submission.",
    },
}


def funder_lens(name: str | None) -> dict[str, Any]:
    key = name if name in FUNDER_LENSES else "cross_funder"
    return dict(FUNDER_LENSES[key])


def funder_profile_assessment(
    project: dict[str, Any],
    profile: dict[str, Any] | None,
    *,
    partners: list[dict[str, Any]],
    work_packages: list[dict[str, Any]],
    milestones: list[dict[str, Any]],
) -> dict[str, Any]:
    profile = profile or {}
    dimensions: list[dict[str, Any]] = []

    def rich(field: str, minimum: int = 180) -> bool:
        return len(str(profile.get(field) or "").strip()) >= minimum

    def add(key: str, label: str, weight: int, checks: list[bool], guidance: str) -> None:
        completed = sum(1 for value in checks if value)
        ratio = completed / len(checks) if checks else 0
        earned = round(weight * ratio, 2)
        dimensions.append({
            "key": key,
            "label": label,
            "weight": weight,
            "earned": earned,
            "completion": round(ratio * 100),
            "status": "strong" if ratio >= 0.8 else "developing" if ratio >= 0.5 else "gap",
            "guidance": guidance,
        })

    committed = [row for row in partners if row.get("status") in {"committed", "confirmed"}]
    international = [
        row for row in partners
        if row.get("country") and str(row.get("country")).lower() != str(project.get("country") or "").lower()
    ]
    dated = [row for row in milestones if row.get("due_on")]
    wp_with_outputs = [row for row in work_packages if row.get("outputs") and row.get("objective")]

    add(
        "importance_innovation", "Importance, excellence & innovation", 18,
        [
            len(str(project.get("problem_statement") or "")) >= 250,
            rich("innovation_case"),
            rich("global_relevance"),
            len(project.get("objectives") or []) >= 3,
        ],
        "Make the unmet need, knowledge gap, novelty and global significance unmistakable.",
    )
    add(
        "rigor_feasibility", "Rigor & feasibility", 16,
        [
            rich("rigor_feasibility"),
            len(work_packages) >= 3,
            len(wp_with_outputs) >= 2,
            len(milestones) >= 4,
        ],
        "Show that the methods, work packages, dependencies, risks and timeline can actually deliver.",
    )
    add(
        "impact_pathway", "Impact pathway & translation", 16,
        [
            rich("impact_pathway"),
            rich("policy_translation"),
            rich("monitoring_evaluation"),
            bool(profile.get("impact_metrics")),
        ],
        "Connect activities to measurable outputs, outcomes, uptake, policy/clinical/industry pathways and beneficiaries.",
    )
    add(
        "team_environment", "Expertise, consortium & research environment", 14,
        [
            len(partners) >= 3,
            len(committed) >= 1,
            len(international) >= 1,
            rich("institutional_capacity"),
        ],
        "Demonstrate complementary expertise, committed partners, facilities and the environment required for delivery.",
    )
    add(
        "implementation", "Implementation quality & value for money", 12,
        [
            bool(project.get("budget_amount")),
            len(work_packages) >= 3,
            len(dated) >= 2,
            rich("risk_management"),
        ],
        "Show ownership, milestones, decision points, risk mitigation and credible use of funds.",
    )
    add(
        "governance_open_science", "Ethics, governance, data & open science", 10,
        [
            rich("ethics_governance"),
            rich("data_open_science"),
            bool(profile.get("data_management_commitments")),
        ],
        "Make ethics, data stewardship, reproducibility, sharing, biosafety and governance visible before reviewers ask.",
    )
    add(
        "equity_capacity", "Equity, capacity building & research culture", 7,
        [
            rich("equity_capacity_building"),
            bool(profile.get("capacity_outputs")),
        ],
        "Show equitable partnership, researcher development, local leadership and durable African scientific capacity.",
    )
    add(
        "sustainability_scale", "Sustainability, scale & leverage", 7,
        [
            rich("sustainability_scale"),
            rich("cofunding_leverage", 100),
        ],
        "Explain what survives after the grant, how successful outputs scale and what additional investment the award unlocks.",
    )

    earned = round(sum(float(row["earned"]) for row in dimensions), 2)
    max_points = sum(int(row["weight"]) for row in dimensions)
    percent = round((earned / max_points) * 100) if max_points else 0
    gaps = [row["guidance"] for row in dimensions if row["status"] == "gap"]

    return {
        "score": percent,
        "earned_points": earned,
        "max_points": max_points,
        "dimensions": dimensions,
        "priority_gaps": gaps,
        "lens": funder_lens(str(profile.get("funder_lens") or "cross_funder")),
        "notice": "Readiness score measures dossier completeness against this preparation lens; it is not a funding probability or funder endorsement.",
    }


def safe_funder_snapshot(
    project: dict[str, Any],
    profile: dict[str, Any] | None,
    *,
    partners: list[dict[str, Any]],
    work_packages: list[dict[str, Any]],
    milestones: list[dict[str, Any]],
    include_budget: bool = True,
    include_partners: bool = True,
    include_milestones: bool = True,
) -> dict[str, Any]:
    profile = profile or {}
    project_fields = [
        "_id", "title", "acronym", "project_type", "originator_name", "host_institution",
        "country", "location", "duration_months", "budget_amount", "budget_currency",
        "funder_name", "call_reference", "call_url", "deadline", "summary",
        "problem_statement", "objectives", "status",
    ]
    public_project = {key: project.get(key) for key in project_fields}
    if not include_budget:
        public_project.pop("budget_amount", None)
        public_project.pop("budget_currency", None)

    public_profile_fields = [
        "funder_lens", "innovation_case", "global_relevance", "rigor_feasibility",
        "impact_pathway", "institutional_capacity", "ethics_governance",
        "data_open_science", "equity_capacity_building", "sustainability_scale",
        "policy_translation", "monitoring_evaluation", "risk_management",
        "cofunding_leverage", "impact_metrics", "capacity_outputs",
        "data_management_commitments", "sdg_alignment", "keywords",
    ]
    public_profile = {key: profile.get(key) for key in public_profile_fields if profile.get(key)}

    public_partners = []
    if include_partners:
        for row in partners:
            public_partners.append({
                "organization": row.get("organization"),
                "country": row.get("country"),
                "partner_type": row.get("partner_type"),
                "status": row.get("status"),
                "proposed_role": row.get("proposed_role"),
            })

    public_wps = []
    for row in work_packages:
        item = {
            "sequence": row.get("sequence"),
            "title": row.get("title"),
            "lead_partner": row.get("lead_partner"),
            "objective": row.get("objective"),
            "outputs": row.get("outputs", []),
        }
        if include_budget:
            item["budget_amount"] = row.get("budget_amount")
        public_wps.append(item)

    public_milestones = []
    if include_milestones:
        for row in milestones:
            public_milestones.append({
                "title": row.get("title"),
                "milestone_type": row.get("milestone_type"),
                "due_on": row.get("due_on"),
                "status": row.get("status"),
                "owner": row.get("owner"),
            })

    return {
        "project": public_project,
        "profile": public_profile,
        "partners": public_partners,
        "work_packages": public_wps,
        "milestones": public_milestones,
        "readiness": funder_profile_assessment(
            project,
            profile,
            partners=partners,
            work_packages=work_packages,
            milestones=milestones,
        ),
        "privacy_notice": "This funder room intentionally excludes Background IP records, disclosure history, private contact emails and unpublished source files.",
    }
