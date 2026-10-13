from fastapi import APIRouter

from ..models import PaymentRequest, PaymentResult

router = APIRouter(prefix="/api", tags=["invoices"])


@router.post("/payments", response_model=PaymentResult)
def create_payment(request: PaymentRequest):
    from ..db import get_treasurer

    return get_treasurer().pay(request)
