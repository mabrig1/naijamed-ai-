from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.compliance_document import ComplianceDocument, ComplianceStatus
from app.models.drug_formulation import DrugFormulation
from app.models.herb import Herb
from app.models.user import User, UserRole
from app.schemas.compliance import (
    ChecklistItem,
    ComplianceChatRequest,
    ComplianceChatResponse,
    ComplianceChecklistResponse,
    DocumentCreate,
    DocumentGenerateRequest,
    DocumentRead,
    DocumentSubmitResponse,
    DocumentUpdate,
    NafdacStage,
    NafdacStagesResponse,
)
from app.services.compliance_service import (
    NAFDAC_GENERAL_NOTES,
    NAFDAC_STAGES,
    _DISCLAIMER,
    answer_compliance_question,
    generate_nafdac_document,
    get_approval_checklist,
)

router = APIRouter()

_DOC_OPTS = [
    selectinload(ComplianceDocument.herb),
    selectinload(ComplianceDocument.formulation),
]


def _get_doc_or_404(doc_id: int, db: Session) -> ComplianceDocument:
    doc = db.get(ComplianceDocument, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance document not found"
        )
    return doc


def _require_owner_or_admin(doc: ComplianceDocument, current_user: User) -> None:
    if current_user.role != UserRole.admin and doc.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _doc_with_relations(doc_id: int, db: Session) -> ComplianceDocument:
    return (
        db.query(ComplianceDocument)
        .options(*_DOC_OPTS)
        .filter(ComplianceDocument.id == doc_id)
        .first()
    )


# ---------------------------------------------------------------------------
# Non-parameterised routes — MUST be registered before /documents/{id}
# ---------------------------------------------------------------------------

@router.get("/checklist", response_model=ComplianceChecklistResponse)
def compliance_checklist(
    product_type: str = Query(
        "herbal medicine",
        description=(
            "Product regulatory category — e.g. 'herbal medicine', "
            "'food supplement', 'pharmaceutical', 'cosmetic'"
        ),
    ),
    _: User = Depends(get_current_user),
):
    """AI-generated step-by-step NAFDAC approval checklist for a product type."""
    items_raw = get_approval_checklist(product_type)
    items = [ChecklistItem(**item) for item in items_raw]
    return ComplianceChecklistResponse(
        product_type=product_type,
        total_steps=len(items),
        items=items,
    )


@router.get("/stages", response_model=NafdacStagesResponse)
def nafdac_stages(_: User = Depends(get_current_user)):
    """Return all 8 NAFDAC product registration stages with requirements and fees."""
    stages = [NafdacStage(**s) for s in NAFDAC_STAGES]
    return NafdacStagesResponse(
        total_stages=len(stages),
        stages=stages,
        general_notes=NAFDAC_GENERAL_NOTES,
    )


@router.post("/chat", response_model=ComplianceChatResponse)
def compliance_chat(
    body: ComplianceChatRequest,
    _: User = Depends(get_current_user),
):
    """Chat with the NAFDAC regulatory AI assistant."""
    result = answer_compliance_question(body.question, body.context)
    return ComplianceChatResponse(
        answer=result["answer"],
        disclaimer=_DISCLAIMER,
        suggested_next_questions=result.get("suggested_next_questions", []),
    )


# ---------------------------------------------------------------------------
# Documents — list + create
# ---------------------------------------------------------------------------

@router.get("/documents", response_model=List[DocumentRead])
def list_documents(
    herb_id: Optional[int] = Query(None),
    doc_status: Optional[ComplianceStatus] = Query(None, alias="status"),
    document_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns only the current user's documents (admins see all)."""
    query = db.query(ComplianceDocument).options(*_DOC_OPTS)

    if current_user.role != UserRole.admin:
        query = query.filter(ComplianceDocument.user_id == current_user.id)

    if herb_id is not None:
        query = query.filter(ComplianceDocument.herb_id == herb_id)
    if doc_status is not None:
        query = query.filter(ComplianceDocument.status == doc_status)
    if document_type:
        query = query.filter(ComplianceDocument.document_type.ilike(f"%{document_type}%"))

    return query.order_by(ComplianceDocument.updated_at.desc()).offset(skip).limit(limit).all()


@router.post(
    "/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    body: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.get(Herb, body.herb_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Herb not found")
    if body.formulation_id and not db.get(DrugFormulation, body.formulation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Formulation not found"
        )

    doc = ComplianceDocument(user_id=current_user.id, **body.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_with_relations(doc.id, db)


# ---------------------------------------------------------------------------
# Documents — single-item operations (parameterised)
# ---------------------------------------------------------------------------

@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _doc_with_relations(document_id, db)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance document not found"
        )
    _require_owner_or_admin(doc, current_user)
    return doc


@router.put("/documents/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int,
    body: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_doc_or_404(document_id, db)
    _require_owner_or_admin(doc, current_user)

    if doc.status == ComplianceStatus.submitted and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Submitted documents cannot be edited. Contact NAFDAC or an admin.",
        )

    if body.formulation_id is not None and not db.get(DrugFormulation, body.formulation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Formulation not found"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)

    db.commit()
    db.refresh(doc)
    return _doc_with_relations(doc.id, db)


@router.post(
    "/documents/{document_id}/generate",
    response_model=DocumentRead,
    summary="AI auto-fills the document using herb and formulation data",
)
def generate_document(
    document_id: int,
    body: DocumentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calls Claude to generate a complete NAFDAC document draft.
    Merges the AI response into content_json and updates product_name.
    """
    doc = _doc_with_relations(document_id, db)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Compliance document not found"
        )
    _require_owner_or_admin(doc, current_user)

    if doc.status == ComplianceStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot regenerate a submitted document.",
        )

    # Resolve product_type: body override → doc field → sensible default
    product_type = body.product_type or doc.product_type or "herbal medicine"

    # Resolve formulation: body override → doc FK → empty dict
    formulation_id = body.formulation_id or doc.formulation_id
    formulation_obj: DrugFormulation | None = (
        db.get(DrugFormulation, formulation_id) if formulation_id else None
    )
    formulation_data: dict = {}
    if formulation_obj:
        formulation_data = {
            "formulation_type": formulation_obj.formulation_type.value,
            "target_disease": formulation_obj.target_disease,
            "compound_used": formulation_obj.compound_used,
            "dosage_suggestion": formulation_obj.dosage_suggestion,
            "excipients_needed": formulation_obj.excipients_needed,
            "manufacturing_process_summary": formulation_obj.manufacturing_process_summary,
            "side_effects_prediction": formulation_obj.side_effects_prediction,
            "disclaimer": formulation_obj.disclaimer,
        }

    herb = doc.herb
    herb_data = {
        "name_english": herb.name_english if herb else "Unknown",
        "scientific_name": herb.scientific_name if herb else None,
        "region_found": herb.region_found if herb else None,
        "description": herb.description if herb else None,
    }

    ai_content = generate_nafdac_document(herb_data, formulation_data, product_type)

    # Persist AI output
    raw_doc = _get_doc_or_404(document_id, db)
    raw_doc.content_json = ai_content
    raw_doc.product_type = product_type
    if ai_content.get("product_name"):
        raw_doc.product_name = ai_content["product_name"]
    if formulation_id:
        raw_doc.formulation_id = formulation_id

    db.commit()
    db.refresh(raw_doc)
    return _doc_with_relations(raw_doc.id, db)


@router.post(
    "/documents/{document_id}/submit",
    response_model=DocumentSubmitResponse,
    summary="Mark a compliance document as submitted to NAFDAC",
)
def submit_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_doc_or_404(document_id, db)
    _require_owner_or_admin(doc, current_user)

    if doc.status == ComplianceStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already marked as submitted.",
        )
    if doc.status in (ComplianceStatus.approved, ComplianceStatus.rejected):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot submit a document with status '{doc.status.value}'.",
        )
    if not doc.content_json:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document has no content. Use /generate to auto-fill before submitting.",
        )

    doc.status = ComplianceStatus.submitted
    doc.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    return doc
