from ..models import PaymentRequest, PaymentResult
from ..services import Treasurer


def authorize_payment(treasurer: Treasurer, request: PaymentRequest) -> PaymentResult:
    return treasurer.pay(request)
