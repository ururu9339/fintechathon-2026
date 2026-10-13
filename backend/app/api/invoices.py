from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..models import PaymentRequest, PaymentResult
from ..db import get_session

router = APIRouter(prefix="/api", tags=["invoices"])


@router.post("/payments", response_model=PaymentResult)
def create_payment(
    request: PaymentRequest,
    session: Session = Depends(get_session),
):
    from ..db import get_treasurer

    result = get_treasurer().pay(request)
    session.add(request)
    session.commit()
    return result


@router.get("/payments", response_model=list[PaymentRequest])
def list_payments(session: Session = Depends(get_session)):
    return session.exec(select(PaymentRequest)).all()
