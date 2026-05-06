from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.clinical_trial import ClinicalTrial, TrialStatus
from app.models.herb import Herb
from app.models.patient_outcome import PatientOutcome
from app.models.user import User, UserRole
from app.schemas.research import (
    EvidenceScoreResponse,
    OutcomeCreate,
    OutcomeRead,
    TrialCreate,
    TrialRead,
    TrialSummaryResponse,
    TrialUpdate,
)
from app.services.research_service import calculate_evidence_score, summarize_trial

router = APIRouter()

_TRIAL_OPTS = [
    selectinload(ClinicalTrial.herb),
    selectinload(ClinicalTrial.researcher),
]


def _get_trial_or_404(trial_id: int, db: Session) -> ClinicalTrial:
    trial = db.get(ClinicalTrial, trial_id)
    if not trial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    return trial


def _trial_with_herb(trial_id: int, db: Session) -> ClinicalTrial:
    return (
        db.query(ClinicalTrial)
        .options(*_TRIAL_OPTS)
        .filter(ClinicalTrial.id == trial_id)
        .first()
    )


def _trial_to_ai_input(trial: ClinicalTrial) -> dict:
    """Flatten a ClinicalTrial ORM object to a plain dict for the AI service."""
    herb = trial.herb
    return {
        "study_title": trial.study_title,
        "herb_name": herb.name_english if herb else "Unknown",
        "scientific_name": herb.scientific_name if herb else None,
        "study_phase": trial.study_phase,
        "status": trial.status.value,
        "methodology": trial.methodology,
        "patient_count": trial.patient_count,
        "start_date": str(trial.start_date) if trial.start_date else None,
        "end_date": str(trial.end_date) if trial.end_date else None,
        "outcome_summary": trial.outcome_summary,
        "effectiveness_score": float(trial.effectiveness_score) if trial.effectiveness_score else None,
        "findings": trial.findings,
        "statistical_data": trial.statistical_data,
        "publication_doi": trial.publication_doi,
        "is_verified": trial.is_verified,
    }


# ---------------------------------------------------------------------------
# Trials — list + create (before parameterised routes)
# ---------------------------------------------------------------------------

@router.get("/trials", response_model=List[TrialRead])
def list_trials(
    herb_id: Optional[int] = Query(None),
    status_filter: Optional[TrialStatus] = Query(None, alias="status"),
    min_effectiveness: Optional[Decimal] = Query(None, ge=0, le=100),
    verified_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(ClinicalTrial).options(*_TRIAL_OPTS)

    if herb_id is not None:
        query = query.filter(ClinicalTrial.herb_id == herb_id)
    if status_filter is not None:
        query = query.filter(ClinicalTrial.status == status_filter)
    if min_effectiveness is not None:
        query = query.filter(ClinicalTrial.effectiveness_score >= min_effectiveness)
    if verified_only:
        query = query.filter(ClinicalTrial.is_verified.is_(True))

    return query.order_by(ClinicalTrial.created_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/trials",
    response_model=TrialRead,
    status_code=status.HTTP_201_CREATED,
    summary="Researcher submits a clinical trial",
)
def create_trial(
    body: TrialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.researcher, UserRole.admin)
    ),
):
    if not db.get(Herb, body.herb_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")

    trial = ClinicalTrial(
        researcher_id=current_user.id,
        status=TrialStatus.submitted,
        **body.model_dump(),
    )
    db.add(trial)
    db.commit()
    db.refresh(trial)
    return _trial_with_herb(trial.id, db)


# ---------------------------------------------------------------------------
# Outcomes — list + create
# ---------------------------------------------------------------------------

@router.get("/outcomes", response_model=List[OutcomeRead])
def list_outcomes(
    herb_id: Optional[int] = Query(None),
    outcome_filter: Optional[str] = Query(None, alias="outcome"),
    condition: Optional[str] = Query(None, description="Partial match on condition_treated"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Returns anonymized patient outcomes — logged_by is never exposed."""
    query = db.query(PatientOutcome)

    if herb_id is not None:
        query = query.filter(PatientOutcome.herb_id == herb_id)
    if outcome_filter:
        query = query.filter(PatientOutcome.outcome == outcome_filter)
    if condition:
        query = query.filter(PatientOutcome.condition_treated.ilike(f"%{condition}%"))

    return query.order_by(PatientOutcome.created_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/outcomes",
    response_model=OutcomeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Doctor logs an anonymized patient outcome",
)
def log_outcome(
    body: OutcomeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.researcher, UserRole.admin)
    ),
):
    """
    Accepts anonymized clinical observations.
    logged_by is stored internally for audit but never returned in responses.
    Patient names, IDs, and birthdates must NOT be included in any field.
    """
    if not db.get(Herb, body.herb_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")

    if body.trial_id is not None and not db.get(ClinicalTrial, body.trial_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical trial not found",
        )

    outcome = PatientOutcome(logged_by=current_user.id, **body.model_dump())
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


# ---------------------------------------------------------------------------
# Evidence score — herb-level aggregation
# ---------------------------------------------------------------------------

@router.get(
    "/herbs/{herb_id}/evidence",
    response_model=EvidenceScoreResponse,
    summary="Aggregate AI evidence score for a herb across all its trials",
)
def herb_evidence(
    herb_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    herb = db.get(Herb, herb_id)
    if not herb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")

    trials = db.query(ClinicalTrial).filter(ClinicalTrial.herb_id == herb_id).all()
    trial_dicts = [
        {
            "id": t.id,
            "study_title": t.study_title,
            "study_phase": t.study_phase,
            "status": t.status.value,
            "patient_count": t.patient_count,
            "outcome_summary": t.outcome_summary,
            "effectiveness_score": float(t.effectiveness_score) if t.effectiveness_score else None,
            "is_verified": t.is_verified,
            "findings": t.findings,
        }
        for t in trials
    ]

    result = calculate_evidence_score(
        herb_name=herb.name_english,
        scientific_name=herb.scientific_name,
        trials=trial_dicts,
    )

    return EvidenceScoreResponse(
        herb_id=herb_id,
        herb_name=herb.name_english,
        evidence_score=result["evidence_score"],
        verdict=result["verdict"],
        key_findings=result.get("key_findings", []),
        safety_signals=result.get("safety_signals", []),
        trial_count=len(trials),
        verified_trial_count=sum(1 for t in trials if t.is_verified),
    )


# ---------------------------------------------------------------------------
# Trials — single-item operations (parameterised — registered LAST)
# ---------------------------------------------------------------------------

@router.get("/trials/{trial_id}", response_model=TrialRead)
def get_trial(
    trial_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Returns the trial with any cached AI summary. Call /ai-summary to generate fresh."""
    trial = _trial_with_herb(trial_id, db)
    if not trial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")
    return trial


@router.put("/trials/{trial_id}", response_model=TrialRead)
def update_trial(
    trial_id: int,
    body: TrialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trial = _get_trial_or_404(trial_id, db)

    if current_user.role != UserRole.admin and trial.researcher_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if trial.is_verified and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified trials cannot be edited by non-admins",
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(trial, field, value)

    # Invalidate cached AI summary when trial data changes
    trial.ai_summary = None

    db.commit()
    db.refresh(trial)
    return _trial_with_herb(trial.id, db)


@router.post(
    "/trials/{trial_id}/verify",
    response_model=TrialRead,
    summary="Admin marks a trial as peer-verified",
)
def verify_trial(
    trial_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    trial = _get_trial_or_404(trial_id, db)

    if trial.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial is already verified",
        )
    if trial.status not in (TrialStatus.active, TrialStatus.completed):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only active or completed trials can be verified",
        )

    trial.is_verified = True
    trial.ai_summary = None  # Invalidate summary so it reflects verified status next fetch
    db.commit()
    db.refresh(trial)
    return _trial_with_herb(trial.id, db)


@router.get(
    "/trials/{trial_id}/ai-summary",
    response_model=TrialSummaryResponse,
    summary="Generate (or regenerate) an AI research summary for a trial",
)
def ai_summary(
    trial_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Always calls Claude for a fresh analysis, then caches the result on the trial record.
    The cached version is returned in GET /trials/{id} without an extra API call.
    """
    trial = _trial_with_herb(trial_id, db)
    if not trial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trial not found")

    result = summarize_trial(_trial_to_ai_input(trial))

    # Persist the summary so future GET /trials/{id} requests are free
    raw_trial = _get_trial_or_404(trial_id, db)
    raw_trial.ai_summary = result
    db.commit()

    return TrialSummaryResponse(
        trial_id=trial_id,
        plain_language_summary=result.get("plain_language_summary", ""),
        statistical_significance=result.get("statistical_significance", ""),
        confidence_level=result.get("confidence_level", "low"),
        literature_comparison=result.get("literature_comparison", ""),
        recommended_next_steps=result.get("recommended_next_steps", []),
    )
