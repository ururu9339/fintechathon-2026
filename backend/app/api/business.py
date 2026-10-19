from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from ..auth import get_optional_user, get_current_user, require_business_access
from ..db import get_session
from ..models import (
    BusinessMembership,
    BusinessProfile,
    CashBalance,
    Counterparty,
    LoanRequest,
    OwnershipRecord,
    StatutoryRemittance,
    User,
)

router = APIRouter(
    prefix="/api/businesses",
    tags=["business"],
    dependencies=[Depends(get_current_user)],
)


class BusinessCreate(BaseModel):
    legal_name: str = Field(min_length=1)
    registration_type: str = Field(min_length=1)
    registration_number: str = Field(min_length=1)
    registration_status: str = Field(min_length=1)
    incorporation_date: date | None = None
    msic_code: str = Field(pattern=r"^\d{5}$")
    sector_category: str = Field(min_length=1)
    currency: str = Field(default="MYR", min_length=3, max_length=3)


class OwnershipCreate(BaseModel):
    owner_reference: str = Field(min_length=1)
    share_percentage: Decimal = Field(ge=0, le=100)
    is_malaysian_citizen: bool
    evidence_reference: str = Field(min_length=1)


class LoanRequestCreate(BaseModel):
    requested_amount: Decimal = Field(gt=0)
    tenor_months: int = Field(gt=0)
    annual_rate: Decimal = Field(ge=0)
    purpose: str = Field(min_length=1)
    scheme_code: str | None = None


class CashBalanceCreate(BaseModel):
    as_of_date: date
    amount: Decimal = Field(ge=0)
    currency: str = Field(default="MYR", min_length=3, max_length=3)


class RemittanceCreate(BaseModel):
    payroll_month: date
    statutory_type: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    due_date: date
    paid_date: date | None = None

    @field_validator("payroll_month")
    @classmethod
    def require_month_start(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("Payroll month must be the first day of the month.")
        return value

    @field_validator("paid_date")
    @classmethod
    def require_paid_date_order(cls, value: date | None) -> date | None:
        return value


class CounterpartyCreate(BaseModel):
    name: str = Field(min_length=1)
    party_type: str = Field(min_length=1)
    tax_id: str | None = None
    registration_number: str | None = None
    provider_reference: str | None = None
    is_verified: bool = False


def _business(business_id: str, session: Session) -> BusinessProfile:
    business = session.get(BusinessProfile, business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    return business


@router.post("", response_model=BusinessProfile)
def create_business(
    request: BusinessCreate,
    session: Session = Depends(get_session),
    user: User | None = Depends(get_optional_user),
):
    business = BusinessProfile(**request.model_dump())
    session.add(business)
    session.commit()
    session.refresh(business)
    if isinstance(user, User):
        session.add(BusinessMembership(business_id=business.id, user_id=user.id, role="owner"))
        session.commit()
    return business


@router.post("/{business_id}/members/{user_id}", response_model=BusinessMembership)
def add_business_member(
    business_id: str,
    user_id: str,
    role: str = "viewer",
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _business(business_id, session)
    require_business_access(business_id, user, session, minimum_role="owner")
    if session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if role not in {"owner", "viewer", "accountant"}:
        raise HTTPException(status_code=422, detail="Unsupported business role.")
    membership = BusinessMembership(business_id=business_id, user_id=user_id, role=role)
    session.add(membership)
    session.commit()
    session.refresh(membership)
    return membership


@router.get("", response_model=list[BusinessProfile])
def list_businesses(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_ids = session.exec(
        select(BusinessMembership.business_id).where(
            BusinessMembership.user_id == user.id
        )
    ).all()
    return session.exec(
        select(BusinessProfile).where(BusinessProfile.id.in_(business_ids))
    ).all()


@router.post("/{business_id}/counterparties", response_model=Counterparty)
def create_counterparty(
    business_id: str,
    request: CounterpartyCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _business(business_id, session)
    require_business_access(business_id, user, session, minimum_role="accountant")
    counterparty = Counterparty(business_id=business_id, **request.model_dump())
    session.add(counterparty)
    session.commit()
    session.refresh(counterparty)
    return counterparty


@router.get("/{business_id}/counterparties", response_model=list[Counterparty])
def list_counterparties(business_id: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    _business(business_id, session)
    require_business_access(business_id, user, session)
    return session.exec(
        select(Counterparty).where(Counterparty.business_id == business_id)
    ).all()


@router.post("/{business_id}/ownership", response_model=OwnershipRecord)
def add_ownership(
    business_id: str,
    request: OwnershipCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _business(business_id, session)
    require_business_access(business_id, user, session, minimum_role="owner")
    current = session.exec(
        select(OwnershipRecord).where(OwnershipRecord.business_id == business_id)
    ).all()
    if sum((row.share_percentage for row in current), Decimal("0")) + request.share_percentage > 100:
        raise HTTPException(status_code=422, detail="Ownership percentages cannot exceed 100.")
    record = OwnershipRecord(business_id=business_id, **request.model_dump())
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.get("/{business_id}/ownership", response_model=list[OwnershipRecord])
def list_ownership(business_id: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    _business(business_id, session)
    require_business_access(business_id, user, session)
    return session.exec(
        select(OwnershipRecord).where(OwnershipRecord.business_id == business_id)
    ).all()


@router.post("/{business_id}/loan-requests", response_model=LoanRequest)
def create_loan_request(
    business_id: str,
    request: LoanRequestCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _business(business_id, session)
    require_business_access(business_id, user, session, minimum_role="accountant")
    loan = LoanRequest(business_id=business_id, **request.model_dump())
    session.add(loan)
    session.commit()
    session.refresh(loan)
    return loan


@router.get("/{business_id}/loan-requests", response_model=list[LoanRequest])
def list_loan_requests(business_id: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    _business(business_id, session)
    require_business_access(business_id, user, session)
    return session.exec(
        select(LoanRequest).where(LoanRequest.business_id == business_id)
    ).all()


@router.post("/{business_id}/cash-balances", response_model=CashBalance)
def record_cash_balance(
    business_id: str,
    request: CashBalanceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _business(business_id, session)
    require_business_access(business_id, user, session, minimum_role="accountant")
    balance = CashBalance(business_id=business_id, **request.model_dump())
    session.add(balance)
    session.commit()
    session.refresh(balance)
    return balance


@router.get("/{business_id}/cash-balances", response_model=list[CashBalance])
def list_cash_balances(business_id: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    _business(business_id, session)
    require_business_access(business_id, user, session)
    return session.exec(
        select(CashBalance).where(CashBalance.business_id == business_id)
    ).all()


@router.post("/{business_id}/statutory-remittances", response_model=StatutoryRemittance)
def record_remittance(
    business_id: str,
    request: RemittanceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _business(business_id, session)
    require_business_access(business_id, user, session, minimum_role="accountant")
    if request.paid_date and request.paid_date < request.payroll_month:
        raise HTTPException(status_code=422, detail="Paid date is before payroll month.")
    status = "missing"
    if request.paid_date:
        status = "on_time" if request.paid_date <= request.due_date else "late"
    remittance = StatutoryRemittance(
        business_id=business_id,
        status=status,
        **request.model_dump(),
    )
    session.add(remittance)
    session.commit()
    session.refresh(remittance)
    return remittance


@router.get("/{business_id}/statutory-remittances", response_model=list[StatutoryRemittance])
def list_remittances(business_id: str, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    _business(business_id, session)
    require_business_access(business_id, user, session)
    return session.exec(
        select(StatutoryRemittance).where(StatutoryRemittance.business_id == business_id)
    ).all()
