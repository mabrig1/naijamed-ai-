from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.drug_formulation import DrugFormulation, FormulationType
from app.models.herb import Herb
from app.models.user import User, UserRole
from app.schemas.formulations import (
    FormulationCompareRequest,
    FormulationCompareResponse,
    FormulationGenerateRequest,
    FormulationRead,
    FormulationUpdate,
)
from app.services.formulation_service import compare_formulations, generate_formulation

router = APIRouter()


def _get_formulation_or_404(formulation_id: int, db: Session) -> DrugFormulation:
    f = db.get(DrugFormulation, formulation_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulation not found")
    return f


def _get_herb_or_404(herb_id: int, db: Session) -> Herb:
    herb = db.get(Herb, herb_id)
    if not herb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")
    return herb


# ---------------------------------------------------------------------------
# IMPORTANT: literal sub-paths (/generate, /compare) must be registered
# before /{formulation_id} so FastAPI does not swallow them as parameters.
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=FormulationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI drug formulation for a herb",
)
def generate(
    body: FormulationGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.researcher, UserRole.pharma_company, UserRole.admin)),
):
    herb = _get_herb_or_404(body.herb_id, db)

    ai = generate_formulation(
        herb_name=herb.name_english,
        scientific_name=herb.scientific_name,
        target_disease=body.target_disease,
        compound_used=body.compound_used or "",
        formulation_type=body.formulation_type.value,
    )

    formulation = DrugFormulation(
        herb_id=herb.id,
        created_by=current_user.id,
        formulation_type=body.formulation_type,
        target_disease=body.target_disease,
        compound_used=body.compound_used,
        # Map AI response fields → model columns
        dosage_suggestion=ai.get("recommended_dosage"),
        stability_prediction=(
            str(ai["estimated_stability_months"]) + " months"
            if ai.get("estimated_stability_months") is not None
            else None
        ),
        side_effects_prediction=(
            "; ".join(ai["predicted_side_effects"])
            if ai.get("predicted_side_effects")
            else None
        ),
        ai_notes=ai.get("ai_notes"),
        excipients_needed=ai.get("excipients_needed"),
        manufacturing_process_summary=ai.get("manufacturing_process_summary"),
        estimated_cost_savings_usd=ai.get("estimated_cost_savings_usd"),
        next_steps=ai.get("next_steps"),
        disclaimer=ai.get("disclaimer"),
        is_published=False,
    )
    db.add(formulation)
    db.commit()
    db.refresh(formulation)
    return formulation


@router.post(
    "/compare",
    response_model=FormulationCompareResponse,
    summary="AI comparison of two formulations",
)
def compare(
    body: FormulationCompareRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(UserRole.researcher, UserRole.pharma_company, UserRole.admin)),
):
    if body.formulation_id_1 == body.formulation_id_2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="formulation_id_1 and formulation_id_2 must be different",
        )

    f1_obj = _get_formulation_or_404(body.formulation_id_1, db)
    f2_obj = _get_formulation_or_404(body.formulation_id_2, db)

    def _to_dict(f: DrugFormulation) -> dict:
        return {
            "id": f.id,
            "herb_name": f.herb.name_english if f.herb else "Unknown",
            "formulation_type": f.formulation_type.value,
            "target_disease": f.target_disease,
            "dosage_suggestion": f.dosage_suggestion,
            "stability_prediction": f.stability_prediction,
            "excipients_needed": f.excipients_needed or [],
            "manufacturing_process_summary": f.manufacturing_process_summary,
            "side_effects_prediction": (
                f.side_effects_prediction.split("; ") if f.side_effects_prediction else []
            ),
            "estimated_cost_savings_usd": str(f.estimated_cost_savings_usd) if f.estimated_cost_savings_usd is not None else None,
            "ai_notes": f.ai_notes,
        }

    # Eagerly load herb for both objects
    from sqlalchemy.orm import selectinload as sil
    f1_obj = (
        db.query(DrugFormulation)
        .options(sil(DrugFormulation.herb))
        .filter(DrugFormulation.id == f1_obj.id)
        .first()
    )
    f2_obj = (
        db.query(DrugFormulation)
        .options(sil(DrugFormulation.herb))
        .filter(DrugFormulation.id == f2_obj.id)
        .first()
    )

    result = compare_formulations(_to_dict(f1_obj), _to_dict(f2_obj))

    # Ensure recommended_id is a valid integer pointing to one of the two IDs
    rec_id = result.get("recommended_id")
    if rec_id not in (body.formulation_id_1, body.formulation_id_2):
        rec_id = body.formulation_id_1

    return FormulationCompareResponse(
        formulation_id_1=body.formulation_id_1,
        formulation_id_2=body.formulation_id_2,
        recommended_id=rec_id,
        reasoning=result.get("reasoning", ""),
        trade_offs=result.get("trade_offs", []),
        combined_next_steps=result.get("combined_next_steps", []),
    )


# ---------------------------------------------------------------------------
# List / filter
# ---------------------------------------------------------------------------

@router.get("", response_model=List[FormulationRead])
def list_formulations(
    herb_id: Optional[int] = Query(None, description="Filter by herb"),
    formulation_type: Optional[FormulationType] = Query(None),
    user_id: Optional[int] = Query(None, description="Filter by creator (admin only)"),
    published_only: bool = Query(False, description="Return only published formulations"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DrugFormulation)

    if herb_id is not None:
        query = query.filter(DrugFormulation.herb_id == herb_id)
    if formulation_type is not None:
        query = query.filter(DrugFormulation.formulation_type == formulation_type)
    if published_only:
        query = query.filter(DrugFormulation.is_published.is_(True))

    # Non-admins can only see their own formulations or published ones
    if current_user.role != UserRole.admin:
        if user_id is not None and user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only filter by your own user_id",
            )
        query = query.filter(
            (DrugFormulation.created_by == current_user.id)
            | (DrugFormulation.is_published.is_(True))
        )
    elif user_id is not None:
        query = query.filter(DrugFormulation.created_by == user_id)

    return query.order_by(DrugFormulation.created_at.desc()).offset(skip).limit(limit).all()


# ---------------------------------------------------------------------------
# Single formulation CRUD
# ---------------------------------------------------------------------------

@router.get("/{formulation_id}", response_model=FormulationRead)
def get_formulation(
    formulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = _get_formulation_or_404(formulation_id, db)
    if (
        not f.is_published
        and current_user.role != UserRole.admin
        and f.created_by != current_user.id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return f


@router.put("/{formulation_id}", response_model=FormulationRead)
def update_formulation(
    formulation_id: int,
    body: FormulationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = _get_formulation_or_404(formulation_id, db)
    if current_user.role != UserRole.admin and f.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(f, field, value)
    db.commit()
    db.refresh(f)
    return f


@router.delete("/{formulation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_formulation(
    formulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    f = _get_formulation_or_404(formulation_id, db)
    if current_user.role != UserRole.admin and f.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    db.delete(f)
    db.commit()


@router.post(
    "/{formulation_id}/publish",
    response_model=FormulationRead,
    summary="Publish a formulation so pharma buyers can see it",
)
def publish_formulation(
    formulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.researcher, UserRole.pharma_company, UserRole.admin)),
):
    f = _get_formulation_or_404(formulation_id, db)
    if current_user.role != UserRole.admin and f.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if f.is_published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Formulation is already published"
        )
    f.is_published = True
    db.commit()
    db.refresh(f)
    return f
