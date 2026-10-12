from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4


@dataclass(frozen=True)
class RailPayment:
    payment_id: str
    supplier: str
    amount: Decimal
    status: str


def submit_payment(supplier: str, amount: Decimal) -> RailPayment:
    """Simulate a fast, idempotency-ready payment rail."""
    return RailPayment(
        payment_id=f"rail_{uuid4().hex[:10]}",
        supplier=supplier,
        amount=amount,
        status="settled",
    )
