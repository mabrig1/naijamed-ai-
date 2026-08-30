from datetime import datetime, timezone
from typing import Any


def build_fhir_bundle(case_id: str, patient_id: int, intake: dict[str, Any], urgency: str) -> dict[str, Any]:
    """Build a FHIR R4-compatible Bundle for future EHR interchange.

    This creates interoperable resource-shaped JSON; production EHR exchange should
    still be validated against the receiving institution's profiles and terminology server.
    """
    now = datetime.now(timezone.utc).isoformat()
    patient_ref = f"Patient/user-{patient_id}"
    encounter_ref = f"Encounter/{case_id}"

    entries: list[dict[str, Any]] = [
        {
            "fullUrl": patient_ref,
            "resource": {
                "resourceType": "Patient",
                "id": f"user-{patient_id}",
                "identifier": [{"system": "https://healthos.mabrigkorie.org/patient", "value": str(patient_id)}],
            },
        },
        {
            "fullUrl": encounter_ref,
            "resource": {
                "resourceType": "Encounter",
                "id": case_id,
                "status": "in-progress",
                "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "VR", "display": "virtual"},
                "subject": {"reference": patient_ref},
                "period": {"start": now},
                "priority": {"text": urgency},
            },
        },
    ]

    for index, symptom in enumerate(intake.get("symptoms") or []):
        label = symptom.get("name") if isinstance(symptom, dict) else str(symptom)
        entries.append(
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": f"{case_id}-symptom-{index + 1}",
                    "clinicalStatus": {"text": "active"},
                    "subject": {"reference": patient_ref},
                    "encounter": {"reference": encounter_ref},
                    "code": {"text": label},
                }
            }
        )

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": now,
        "identifier": {"system": "https://healthos.mabrigkorie.org/case", "value": case_id},
        "entry": entries,
    }
