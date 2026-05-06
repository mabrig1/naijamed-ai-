from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.herb import Herb
from app.models.herb_compound import HerbCompound
from app.models.user import User, UserRole
from app.schemas.herb import (
    DrugSuggestionRequest,
    DrugSuggestionResponse,
    HerbCompoundCreate,
    HerbCompoundRead,
    HerbCreate,
    HerbDetail,
    HerbRead,
    HerbUpdate,
    ScanRequest,
    ScanResponse,
)
from app.services.ai_herb_service import analyze_herb, suggest_drug_possibility

router = APIRouter()


def _get_herb_or_404(herb_id: int, db: Session) -> Herb:
    herb = db.get(Herb, herb_id)
    if not herb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")
    return herb


# ---------------------------------------------------------------------------
# IMPORTANT: literal sub-paths (/scan) must be registered before /{herb_id}
# so FastAPI does not swallow them as path parameters.
# ---------------------------------------------------------------------------

@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="AI analysis of any herb by name and description",
)
def scan_herb(
    body: ScanRequest,
    _: User = Depends(get_current_user),
):
    result = analyze_herb(body.herb_name, body.user_description)
    return ScanResponse(herb_name=body.herb_name, **result)


# ---------------------------------------------------------------------------
# CRUD — list / create
# ---------------------------------------------------------------------------

@router.get("", response_model=List[HerbRead])
def list_herbs(
    search: Optional[str] = Query(None, description="Search across all name fields and scientific name"),
    region: Optional[str] = Query(None, description="Filter by region_found (case-insensitive)"),
    compound: Optional[str] = Query(None, description="Filter herbs that contain a compound by name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Herb)

    if search:
        like = f"%{search}%"
        query = query.filter(
            Herb.name_english.ilike(like)
            | Herb.scientific_name.ilike(like)
            | Herb.name_igbo.ilike(like)
            | Herb.name_yoruba.ilike(like)
            | Herb.name_hausa.ilike(like)
        )

    if region:
        query = query.filter(Herb.region_found.ilike(f"%{region}%"))

    if compound:
        query = query.join(Herb.compounds).filter(
            HerbCompound.compound_name.ilike(f"%{compound}%")
        ).distinct()

    return query.offset(skip).limit(limit).all()


@router.post("", response_model=HerbDetail, status_code=status.HTTP_201_CREATED)
def create_herb(
    body: HerbCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    herb = Herb(**body.model_dump())
    db.add(herb)
    db.commit()
    db.refresh(herb)
    return herb


# ---------------------------------------------------------------------------
# CRUD — single herb
# ---------------------------------------------------------------------------

@router.get("/{herb_id}", response_model=HerbDetail)
def get_herb(herb_id: int, db: Session = Depends(get_db)):
    herb = (
        db.query(Herb)
        .options(selectinload(Herb.compounds))
        .filter(Herb.id == herb_id)
        .first()
    )
    if not herb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")
    return herb


@router.put("/{herb_id}", response_model=HerbDetail)
def update_herb(
    herb_id: int,
    body: HerbUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    herb = _get_herb_or_404(herb_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(herb, field, value)
    db.commit()
    db.refresh(herb)
    return herb


@router.delete("/{herb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_herb(
    herb_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    herb = _get_herb_or_404(herb_id, db)
    db.delete(herb)
    db.commit()


# ---------------------------------------------------------------------------
# Compounds sub-resource
# ---------------------------------------------------------------------------

@router.get("/{herb_id}/compounds", response_model=List[HerbCompoundRead])
def list_compounds(herb_id: int, db: Session = Depends(get_db)):
    _get_herb_or_404(herb_id, db)
    return db.query(HerbCompound).filter(HerbCompound.herb_id == herb_id).all()


@router.post(
    "/{herb_id}/compounds",
    response_model=HerbCompoundRead,
    status_code=status.HTTP_201_CREATED,
)
def add_compound(
    herb_id: int,
    body: HerbCompoundCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.researcher)),
):
    _get_herb_or_404(herb_id, db)
    compound = HerbCompound(herb_id=herb_id, **body.model_dump())
    db.add(compound)
    db.commit()
    db.refresh(compound)
    return compound


# ---------------------------------------------------------------------------
# AI drug suggestion
# ---------------------------------------------------------------------------

@router.post("/{herb_id}/drug-suggestion", response_model=DrugSuggestionResponse)
def drug_suggestion(
    herb_id: int,
    body: DrugSuggestionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    herb = _get_herb_or_404(herb_id, db)
    result = suggest_drug_possibility(herb.name_english, herb.scientific_name, body.target_disease)
    return DrugSuggestionResponse(
        herb_name=herb.name_english,
        scientific_name=herb.scientific_name,
        target_disease=body.target_disease,
        **result,
    )
