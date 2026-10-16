from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field as Pyfield
from sqlmodel import SQLModel, Field, JSON


def new_id() -> str:
    return uuid4().hex

# ==========================================
# 1. AUTHENTICATION & USER MODELS (add at last stage)
# ==========================================

# class User(SQLModel, tablename="users", table=True):
#     __tablename__ = "users"

#     id: str | None = Field(default_factory=lambda: uuid7().hex, primary_key=True)
#     email: str = Field(unique=True, index=True, nullable=False)
#     hashed_password: str = Field(nullable=False)
#     is_active: bool = Field(default=True)
#     created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# class UserCreate(BaseModel):
#     """Schema for user registration requests."""
#     email: EmailStr
#     password: str


# class UserRead(BaseModel):
#     """Schema for returning user info safely (excluding password)."""
#     id: str
#     email: str
#     is_active: bool
#     created_at: datetime


# class Token(BaseModel):
#     """Schema returned upon successful login."""
#     access_token: str
#     token_type: str = "bearer"


# class TokenData(BaseModel):
#     """Payload decoded from JWT tokens."""
#     email: str | None = None

# ==========================================
# 2. AUTHENTICATION & USER MODELS
# ==========================================

class AuditEvent(SQLModel, tablename = "audit_events", table = True):
    __tablename__ = "audit_events"
    id: str | None = Field(default_factory=new_id, primary_key=True)
    event_type: str
    payload: dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_hash: str
    event_hash: str


class Mandate(SQLModel, tablename="mandates", table = True):
    __tablename__ = "mandates"
    id: str = Field(primary_key=True)
    daily_limit: Decimal
    transaction_limit: Decimal
    allowed_suppliers: list[str] = Field(default_factory=list, sa_type=JSON)
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
    id: str | None = Field(default_factory=new_id, primary_key=True)
    supplier: str = ""
    amount: Decimal = Field(gt=0)
    purpose: str
    invoice_id: str = ""
    mandate_id: str = "mandate-demo"
    ap_invoice_id: str | None = Field(default=None, foreign_key="ap_invoices.id")
    supplier_name: str | None = None
    invoice_number: str | None = None


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


class APInvoiceLineItem(SQLModel, table=True):
    __tablename__ = "ap_invoice_line_items"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    invoice_id: str = Field(foreign_key="ap_invoices.id", index=True)
    description: str
    quantity: Decimal = Decimal("1.00")
    unit_price: Decimal = Decimal("0.00")
    subtotal: Decimal = Decimal("0.00")
    sst_rate: Decimal = Decimal("0.00")
    sst_type: str = "exempt"
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")


class APInvoice(SQLModel, table=True):
    __tablename__ = "ap_invoices"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    mandate_id: str = Field(default="mandate-demo", index=True)
    invoice_number: str = Field(index=True)
    myinvois_uuid: str | None = None
    supplier_name: str = Field(index=True)
    supplier_tin: str | None = None
    supplier_brn: str | None = None
    supplier_sst_number: str | None = None
    supplier_msic_code: str | None = None
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    currency: str = "MYR"
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    requires_individual_einvoice: bool = False
    status: str = "draft"
    review_notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PayrollRecord(SQLModel, table=True):
    __tablename__ = "payroll_records"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    payroll_month: date
    employee_name: str
    encrypted_mykad: str
    gross_salary: Decimal
    epf_employer_share: Decimal = Decimal("0.00")
    epf_employee_share: Decimal = Decimal("0.00")
    socso_employer_share: Decimal = Decimal("0.00")
    socso_employee_share: Decimal = Decimal("0.00")
    eis_employer_share: Decimal = Decimal("0.00")
    eis_employee_share: Decimal = Decimal("0.00")
    pcb_tax_deduction: Decimal = Decimal("0.00")
    hrdf_employer_levy: Decimal = Decimal("0.00")
    net_pay: Decimal
    status: str = "calculated"


class ExtractedLineItemSchema(BaseModel):
    description: str = ""
    quantity: str = "1.0"
    unit_price: str = "0.00"
    subtotal: str = "0.00"
    sst_rate: str = "0.00"
    sst_type: str = "exempt"
    tax_amount: str = "0.00"
    total_amount: str = "0.00"


class ExtractedInvoiceSchema(BaseModel):
    invoice_number: str = ""
    myinvois_uuid: str = ""
    supplier_name: str = ""
    supplier_tin: str = ""
    supplier_brn: str = ""
    supplier_sst_number: str = ""
    supplier_msic_code: str = ""
    issue_date: str = ""
    due_date: str = ""
    currency: str = "MYR"
    subtotal: str = "0.00"
    tax_amount: str = "0.00"
    total_amount: str = "0.00"
    line_items: list[ExtractedLineItemSchema] = []
    source_snippet: str = ""


class ExtractionResult(BaseModel):
    status: Literal["ok", "needs_review", "failed"]
    invoice: ExtractedInvoiceSchema | None = None
    error_message: str | None = None
    reconciliation_ok: bool = False
    review_reasons: list[str] = []
