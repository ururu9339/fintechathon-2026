from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field as Pyfield
from sqlmodel import SQLModel , Field, JSON

class AuditEvent(SQLModel, tablename = "audit_events", table = True):
    __tablename__ = "audit_events"
    id : str | None = Field(default=None, primary_key=True)
    event_type: str
    payload: dict[str, str] = Field(default = {}, sa_type = JSON)
    created_at: datetime
    previous_hash: str
    event_hash: str


class Mandate(SQLModel, tablename="mandates", table = True):
    __tablename__ = "mandates"
    id: str = Field(primary_key=True)
    daily_limit: Decimal
    transaction_limit: Decimal
    allowed_suppliers: list[str] = Field(default=[], sa_type = JSON)
    purpose: str
    expires_at: date


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


class PaymentRequest(SQLModel, tablename="payment_requests", table = True):
    __tablename__ = "payment_requests"
    id: str | None = Field(default_factory=lambda: uuid4().hex, primary_key=True)
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
