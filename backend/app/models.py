from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class CashFlowPoint(BaseModel):
    week: int
    date: date
    opening_balance: Decimal
    inflows: Decimal
    outflows: Decimal
    closing_balance: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


class Envelope(BaseModel):
    name: str
    target: Decimal
    allocated: Decimal
    currency: str = "MYR"


class Mandate(BaseModel):
    id: str
    daily_limit: Decimal
    transaction_limit: Decimal
    allowed_suppliers: list[str]
    purpose: str
    expires_at: date


class PaymentRequest(BaseModel):
    supplier: str
    amount: Decimal = Field(gt=0)
    purpose: str
    invoice_id: str
    mandate_id: str


class PaymentResult(BaseModel):
    status: Literal["approved", "blocked"]
    reason: str
    payment_id: str | None = None
    audit_hash: str


class FinancingRecommendation(BaseModel):
    provider: str
    product: str
    amount: Decimal
    effective_apr: Decimal
    reason: str


class AgentRequest(BaseModel):
    message: str


class AgentResponse(BaseModel):
    status: Literal["approved", "blocked", "advisory"]
    message: str
    action: str | None = None


class AuditEvent(BaseModel):
    event_type: str
    payload: dict
    created_at: datetime
    previous_hash: str
    event_hash: str
