from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..auth import get_current_user, require_business_access
from ..dossier_document import render_dossier_pdf
from ..models import BusinessProfile, CreditDossier, User
from ..dossier_service import create_dossier

router = APIRouter(prefix="/api/businesses", tags=["dossier"])


class DossierCreate(BaseModel):
    period_start: date
    period_end: date
    loan_request_id: str | None = None


@router.post("/{business_id}/dossiers", response_model=CreditDossier)
def create_credit_dossier(
    business_id: str,
    request: DossierCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if session.get(BusinessProfile, business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    require_business_access(business_id, user, session)
    try:
        return create_dossier(
            business_id,
            request.period_start,
            request.period_end,
            session,
            request.loan_request_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{business_id}/dossiers", response_model=list[CreditDossier])
def list_credit_dossiers(
    business_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if session.get(BusinessProfile, business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    require_business_access(business_id, user, session)
    return session.exec(
        select(CreditDossier).where(CreditDossier.business_id == business_id)
    ).all()


@router.get("/{business_id}/dossiers/{dossier_id}/pdf")
def download_credit_dossier_pdf(
    business_id: str,
    dossier_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_business_access(business_id, user, session)
    dossier = session.get(CreditDossier, dossier_id)
    if dossier is None or dossier.business_id != business_id:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    pdf = render_dossier_pdf(dossier)
    session.add(dossier)
    session.commit()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="credit-passport-{dossier.id}.pdf"'},
    )


@router.get("/{business_id}/dossiers/{dossier_id}", response_model=CreditDossier)
def get_credit_dossier(
    business_id: str,
    dossier_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_business_access(business_id, user, session)
    dossier = session.get(CreditDossier, dossier_id)
    if dossier is None or dossier.business_id != business_id:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    return dossier
