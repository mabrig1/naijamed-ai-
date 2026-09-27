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
