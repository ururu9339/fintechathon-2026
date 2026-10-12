from fastapi import APIRouter

from ..db import treasurer
from ..models import PaymentRequest, PaymentResult

router = APIRouter(prefix="/api", tags=["invoices"])


@router.post("/payments", response_model=PaymentResult)
def create_payment(request: PaymentRequest):
    return treasurer.pay(request)
