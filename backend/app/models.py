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


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True
    email_verified_at: datetime | None = None
    deleted_at: datetime | None = None
    password_changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RefreshSession(SQLModel, table=True):
    __tablename__ = "refresh_sessions"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    expires_at: datetime
    revoked_at: datetime | None = None
    replaced_by_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmailActionToken(SQLModel, table=True):
    __tablename__ = "email_action_tokens"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    purpose: str = Field(index=True)
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RateLimitBucket(SQLModel, table=True):
    __tablename__ = "rate_limit_buckets"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    bucket_key: str = Field(index=True, unique=True)
    window_start: datetime
    request_count: int = 0


class ForecastSnapshot(SQLModel, table=True):
    __tablename__ = "forecast_snapshots"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    horizon_days: int
    snapshot: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FinancialAlert(SQLModel, table=True):
    __tablename__ = "financial_alerts"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    severity: str
    alert_type: str
    title: str
    message: str
    suggested_action: str | None = None
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserNotification(SQLModel, table=True):
    __tablename__ = "user_notifications"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    alert_id: str | None = Field(default=None, foreign_key="financial_alerts.id")
    title: str
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AssistantMessage(SQLModel, table=True):
    __tablename__ = "assistant_messages"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    direction: str
    input_kind: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BusinessMembership(SQLModel, table=True):
    __tablename__ = "business_memberships"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    role: str = "owner"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Mandate(SQLModel, tablename="mandates", table = True):
    __tablename__ = "mandates"
    id: str = Field(primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    daily_limit: Decimal = Field(gt=0)
    transaction_limit: Decimal = Field(gt=0)
    allowed_suppliers: list[str] = Field(default_factory=list, sa_type=JSON)
    allowed_counterparty_ids: list[str] = Field(default_factory=list, sa_type=JSON)
    purpose: str
    expires_at: date
    status: str = "active"
    auto_pay: bool = False
    require_verified_supplier: bool = True


class BusinessProfile(SQLModel, table=True):
    __tablename__ = "business_profiles"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    legal_name: str
    registration_type: str
    registration_number: str
    registration_status: str
    incorporation_date: date | None = None
    msic_code: str
    sector_category: str
    currency: str = "MYR"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OwnershipRecord(SQLModel, table=True):
    __tablename__ = "ownership_records"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    owner_reference: str
    share_percentage: Decimal = Field(ge=0, le=100)
    is_malaysian_citizen: bool
    evidence_reference: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LoanRequest(SQLModel, table=True):
    __tablename__ = "loan_requests"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    requested_amount: Decimal = Field(gt=0)
    tenor_months: int = Field(gt=0)
    annual_rate: Decimal = Field(ge=0)
    purpose: str
    scheme_code: str | None = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreditDossier(SQLModel, table=True):
    __tablename__ = "credit_dossiers"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    period_start: date
    period_end: date
    loan_request_id: str | None = Field(default=None, foreign_key="loan_requests.id")
    status: str = "draft"
    snapshot: dict = Field(default_factory=dict, sa_type=JSON)
    input_hash: str
    narrative_status: str = "not_generated"
    narrative_text: str | None = None
    narrative_model: str | None = None
    narrative_prompt_version: str | None = None
    pdf_generated_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CashBalance(SQLModel, table=True):
    __tablename__ = "cash_balances"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    as_of_date: date
    amount: Decimal = Field(ge=0)
    currency: str = "MYR"


class StatutoryRemittance(SQLModel, table=True):
    __tablename__ = "statutory_remittances"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    payroll_month: date
    statutory_type: str
    amount: Decimal = Field(ge=0)
    due_date: date
    paid_date: date | None = None
    status: str = "missing"


class Counterparty(SQLModel, table=True):
    __tablename__ = "counterparties"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str = Field(foreign_key="business_profiles.id", index=True)
    name: str
    party_type: str
    tax_id: str | None = None
    registration_number: str | None = None
    is_verified: bool = False
    provider_reference: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaymentRequest(SQLModel, tablename="payment_requests", table = True):
    __tablename__ = "payment_requests"
    id: str | None = Field(default_factory=new_id, primary_key=True)
    supplier: str = ""
    amount: Decimal = Field(gt=0)
    purpose: str
    invoice_id: str = ""
    mandate_id: str
    ap_invoice_id: str | None = Field(default=None, foreign_key="ap_invoices.id")
    counterparty_id: str | None = Field(default=None, foreign_key="counterparties.id")
    supplier_verified: bool = False
    supplier_name: str | None = None
    invoice_number: str | None = None
    status: str = "pending"


class PaymentResult(BaseModel):
    status: Literal["approved", "blocked"]
    reason: str
    payment_id: str | None = None
    audit_hash: str


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
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    counterparty_id: str | None = Field(default=None, foreign_key="counterparties.id", index=True)
    mandate_id: str | None = Field(default=None, index=True)
    source_system: str | None = None
    source_event_id: str | None = Field(default=None, index=True)
    source_invoice_id: str | None = Field(default=None, index=True)
    invoice_number: str = Field(index=True)
    myinvois_uuid: str | None = None
    myinvois_validation_status: str = "missing"
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
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
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


class SalesInvoiceLineItem(SQLModel, table=True):
    __tablename__ = "sales_invoice_line_items"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    invoice_id: str = Field(foreign_key="sales_invoices.id", index=True)
    description: str
    quantity: Decimal = Decimal("1.00")
    unit_price: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")


class SalesInvoice(SQLModel, table=True):
    __tablename__ = "sales_invoices"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    counterparty_id: str | None = Field(default=None, foreign_key="counterparties.id", index=True)
    invoice_number: str = Field(index=True)
    customer_name: str = Field(index=True)
    customer_tin: str | None = None
    myinvois_uuid: str | None = None
    myinvois_validation_status: str = "missing"
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    currency: str = "MYR"
    issue_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    status: str = "draft"
    review_notes: str | None = None
    amount_received: Decimal = Decimal("0.00")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LedgerAccount(SQLModel, table=True):
    __tablename__ = "ledger_accounts"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    code: str = Field(index=True, unique=True)
    name: str
    account_type: str
    is_active: bool = True


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    source_type: str
    source_id: str
    description: str
    entry_date: date = Field(default_factory=date.today)
    status: str = "posted"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JournalLine(SQLModel, table=True):
    __tablename__ = "journal_lines"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    journal_entry_id: str = Field(foreign_key="journal_entries.id", index=True)
    account_code: str = Field(index=True)
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    description: str | None = None


class Employee(SQLModel, table=True):
    __tablename__ = "employees"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    employee_name: str
    encrypted_mykad: str
    gross_salary: Decimal
    status: str = "active"


class PayrollRun(SQLModel, table=True):
    __tablename__ = "payroll_runs"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    payroll_month: date
    status: str = "draft"
    total_gross: Decimal = Decimal("0.00")
    total_net: Decimal = Decimal("0.00")
    total_employer_cost: Decimal = Decimal("0.00")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreditFacility(SQLModel, table=True):
    __tablename__ = "credit_facilities"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    business_id: str | None = Field(default=None, foreign_key="business_profiles.id", index=True)
    lender_name: str
    facility_type: str
    requested_amount: Decimal = Field(gt=0)
    approved_amount: Decimal = Decimal("0.00")
    outstanding_amount: Decimal = Decimal("0.00")
    monthly_payment: Decimal = Decimal("0.00")
    term_months: int = 0
    status: str = "pending"
    next_payment_date: date | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreditPayment(SQLModel, table=True):
    __tablename__ = "credit_payments"

    id: str | None = Field(default_factory=new_id, primary_key=True)
    facility_id: str = Field(foreign_key="credit_facilities.id", index=True)
    amount: Decimal = Field(gt=0)
    payment_date: date = Field(default_factory=date.today)
    status: str = "posted"


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
    invoice_id: str | None = None
    error_message: str | None = None
    reconciliation_ok: bool = False
    review_reasons: list[str] = []
