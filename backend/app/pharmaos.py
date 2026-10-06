from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class PharmaOSModule:
    key: str
    label: str
    stage: str
    route: str
    engine: str
    evidence_required: bool = True

MODULES = (
    PharmaOSModule("literature","Living Literature Review","evidence","/formulary","formulary"),
    PharmaOSModule("natural_products","NigerFlora Natural Products","discovery","/discovery","nigerflora"),
    PharmaOSModule("network_pharmacology","Network Pharmacology","discovery","/discovery/network","nigerflora"),
    PharmaOSModule("docking","Molecular Docking & Screening","discovery","/discovery/screening","nigerflora"),
    PharmaOSModule("admet","ADMET & Toxicology","discovery","/discovery/admet","nigerflora"),
    PharmaOSModule("pkpd","PK/PD Simulator","translation","/formulary/pkpd","formulary"),
    PharmaOSModule("portfolio","Research Portfolio","research_management","/formulary/portfolio","formulary"),
    PharmaOSModule("copilot","Regulatory & Grant Copilot","translation","/formulary/copilot","formulary"),
    PharmaOSModule("journal","Journal Club","evidence","/formulary/journal","formulary"),
    PharmaOSModule("grants","International Grant Studio","funding","/formulary/grants","formulary"),
)

STAGE_ORDER=("evidence","discovery","translation","research_management","funding")

def module_catalog() -> list[dict[str, Any]]:
    return [asdict(module) for module in MODULES]

def research_pipeline(topic: str, disease: str | None = None) -> dict[str, Any]:
    topic=topic.strip()
    if not topic:
        raise ValueError("topic is required")
    return {
        "topic": topic,
        "disease": (disease or "").strip() or None,
        "status": "planned",
        "stages": [
            {"stage": stage, "modules": [m.key for m in MODULES if m.stage == stage]}
            for stage in STAGE_ORDER
        ],
        "integrity": {
            "computational_results_are_hypotheses": True,
            "experimental_validation_required": True,
            "fabricated_evidence_prohibited": True,
            "provenance_required": True,
        },
    }

def grant_handoff(project: dict[str, Any]) -> dict[str, Any]:
    evidence=project.get("evidence") or []
    return {
        "project_title": project.get("title") or project.get("topic"),
        "preliminary_evidence_count": len(evidence),
        "evidence": evidence,
        "grant_studio_route": "/formulary/grants",
        "claims_boundary": "Computational findings are preliminary evidence, not experimental or clinical proof.",
    }
