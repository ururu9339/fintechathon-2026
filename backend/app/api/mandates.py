from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_session
from ..models import BusinessProfile, Mandate

router = APIRouter(prefix="/api/businesses/{business_id}/mandates", tags=["mandates"])


class MandateCreate(BaseModel):
    id: str = Field(min_length=1)
    daily_limit: Decimal = Field(gt=0)
    transaction_limit: Decimal = Field(gt=0)
    allowed_suppliers: list[str] = []
    allowed_counterparty_ids: list[str] = []
    purpose: str = Field(min_length=1)
    expires_at: date
    auto_pay: bool = False
    require_verified_supplier: bool = True


def _business(business_id: str, session: Session) -> None:
    if session.get(BusinessProfile, business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")


@router.post("", response_model=Mandate)
def create_mandate(
    business_id: str,
    request: MandateCreate,
    session: Session = Depends(get_session),
):
    _business(business_id, session)
    if request.transaction_limit > request.daily_limit:
        raise HTTPException(
            status_code=422,
            detail="Transaction limit cannot exceed daily limit.",
        )
    if not request.allowed_suppliers and not request.allowed_counterparty_ids:
        raise HTTPException(
            status_code=422,
            detail="At least one supplier or verified counterparty is required.",
        )
    if request.expires_at < date.today():
        raise HTTPException(status_code=422, detail="Mandate expiry date is in the past.")
    if session.get(Mandate, request.id) is not None:
        raise HTTPException(status_code=409, detail="Mandate ID already exists.")
    mandate = Mandate(business_id=business_id, **request.model_dump())
    session.add(mandate)
    session.commit()
    session.refresh(mandate)
    return mandate


@router.get("", response_model=list[Mandate])
def list_mandates(
    business_id: str,
    session: Session = Depends(get_session),
):
    _business(business_id, session)
    return session.exec(
        select(Mandate).where(Mandate.business_id == business_id)
    ).all()


@router.post("/{mandate_id}/revoke", response_model=Mandate)
def revoke_mandate(
    business_id: str,
    mandate_id: str,
    session: Session = Depends(get_session),
):
    _business(business_id, session)
    mandate = session.get(Mandate, mandate_id)
    if mandate is None or mandate.business_id != business_id:
        raise HTTPException(status_code=404, detail="Mandate not found.")
    if mandate.status != "active":
        raise HTTPException(status_code=409, detail="Mandate is not active.")
    mandate.status = "revoked"
    session.add(mandate)
    session.commit()
    session.refresh(mandate)
    return mandate
