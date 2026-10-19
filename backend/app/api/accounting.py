from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from agent.extract import llm_multimodal_extractor

from ..db import get_session
from ..auth import get_current_business_id, get_current_user, require_business_access
from ..models import (
    APInvoice,
    BusinessProfile,
    Counterparty,
    CreditFacility,
    CreditPayment,
    Employee,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    PayrollRun,
    SalesInvoice,
    SalesInvoiceLineItem,
    User,
)

router = APIRouter(
    prefix="/api/accounting",
    tags=["accounting"],
    dependencies=[Depends(get_current_user)],
)


class SalesLineInput(BaseModel):
    description: str = Field(min_length=1)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    total_amount: Decimal = Field(default=Decimal("0.00"), gt=0)


class SalesInvoiceCreate(BaseModel):
    business_id: str | None = None
    invoice_number: str
    customer_name: str
    subtotal: Decimal
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    issue_date: date
    due_date: date | None = None
    line_items: list[SalesLineInput] = []


class CreditFacilityCreate(BaseModel):
    business_id: str | None = None
    lender_name: str
    facility_type: str
    requested_amount: Decimal
    monthly_payment: Decimal = Decimal("0.00")
    term_months: int = 0
    next_payment_date: date | None = None


class ReceiptCreate(BaseModel):
    amount: Decimal


class EmployeeCreate(BaseModel):
    business_id: str | None = None
    employee_name: str = Field(min_length=1)
    encrypted_mykad: str = Field(min_length=1)
    gross_salary: Decimal = Field(gt=0)


class EmployeeUpdate(BaseModel):
    employee_name: str | None = Field(default=None, min_length=1)
    gross_salary: Decimal | None = Field(default=None, gt=0)


class JournalLineInput(BaseModel):
    account_code: str = Field(min_length=1)
    debit: Decimal = Field(default=Decimal("0.00"), ge=0)
    credit: Decimal = Field(default=Decimal("0.00"), ge=0)
    description: str | None = None


class JournalCreate(BaseModel):
    business_id: str | None = None
    source_type: str
    source_id: str
    description: str
    lines: list[JournalLineInput]


class LedgerAccountCreate(BaseModel):
    business_id: str | None = None
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    account_type: str = Field(min_length=1)
    is_active: bool = True


def _validate_sales_amounts(subtotal: Decimal, tax: Decimal, total: Decimal) -> None:
    if subtotal < 0 or tax < 0 or total <= 0:
        raise HTTPException(status_code=422, detail="Invoice amounts are invalid.")
    if abs(subtotal + tax - total) > Decimal("0.05"):
        raise HTTPException(status_code=422, detail="Subtotal plus tax must equal total.")


def _require_business(business_id: str, session: Session) -> None:
    if session.get(BusinessProfile, business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")


def _set_current_business(request, user: User, session: Session) -> str:
    if not isinstance(user, User):
        if request.business_id is None:
            raise HTTPException(status_code=403, detail="Business context is required.")
        return request.business_id
    current_id = get_current_business_id(user, session)
    if request.business_id is not None and request.business_id != current_id:
        raise HTTPException(status_code=403, detail="Business must match the current business.")
    request.business_id = current_id
    return current_id


def _counterparty(
    business_id: str,
    name: str,
    party_type: str,
    session: Session,
) -> Counterparty:
    existing = session.exec(
        select(Counterparty).where(
            Counterparty.business_id == business_id,
            Counterparty.name == name,
            Counterparty.party_type == party_type,
        )
    ).first()
    if existing:
        return existing
    counterparty = Counterparty(
        business_id=business_id,
        name=name,
        party_type=party_type,
    )
    session.add(counterparty)
    session.flush()
    return counterparty


def _save_sales_invoice(
    invoice: SalesInvoice,
    line_items: list[SalesLineInput],
    session: Session,
) -> SalesInvoice:
    if invoice.business_id is None:
        raise HTTPException(status_code=422, detail="Business ID is required.")
    _require_business(invoice.business_id, session)
    if invoice.counterparty_id is None:
        invoice.counterparty_id = _counterparty(
            invoice.business_id,
            invoice.customer_name,
            "customer",
            session,
        ).id
    if session.exec(
        select(SalesInvoice).where(
            SalesInvoice.business_id == invoice.business_id,
            SalesInvoice.invoice_number == invoice.invoice_number,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Invoice number already exists for this business.")
    if line_items and abs(
        sum((item.total_amount for item in line_items), Decimal("0.00")) - invoice.total_amount
    ) > Decimal("0.05"):
        raise HTTPException(status_code=422, detail="Invoice line items must equal invoice total.")
    session.add(invoice)
    session.flush()
    for item in line_items:
        session.add(SalesInvoiceLineItem(invoice_id=invoice.id, **item.model_dump()))
    session.commit()
    session.refresh(invoice)
    return invoice


@router.post("/sales/invoices", response_model=SalesInvoice)
def create_sales_invoice(
    request: SalesInvoiceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _set_current_business(request, user, session)
    _require_business(request.business_id, session)
    _validate_sales_amounts(request.subtotal, request.tax_amount, request.total_amount)
    if request.issue_date and request.due_date and request.due_date < request.issue_date:
        raise HTTPException(status_code=422, detail="Due date is before issue date.")
    line_items = request.line_items
    return _save_sales_invoice(
        SalesInvoice(**request.model_dump(exclude={"line_items"})),
        line_items,
        session,
    )


@router.post("/sales/invoices/upload", response_model=SalesInvoice)
async def upload_sales_invoice(
    business_id: str | None = None,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    current_business_id = get_current_business_id(user, session)
    if business_id is not None and business_id != current_business_id:
        raise HTTPException(status_code=403, detail="Business must match the current business.")
    business_id = current_business_id
    _require_business(business_id, session)
    result = llm_multimodal_extractor(
        file.filename or "upload.pdf",
        await file.read(),
        counterparty_label="customer",
    )
    if result.status == "failed" or result.invoice is None:
        raise HTTPException(
            status_code=422,
            detail=result.error_message or result.review_reasons,
        )
    data = result.invoice
    try:
        subtotal = Decimal(data.subtotal)
        tax = Decimal(data.tax_amount)
        total = Decimal(data.total_amount)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Extracted invoice amounts are invalid.",
        ) from exc
    _validate_sales_amounts(subtotal, tax, total)
    try:
        issue_date = date.fromisoformat(data.issue_date) if data.issue_date else None
        due_date = date.fromisoformat(data.due_date) if data.due_date else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Extracted invoice dates are invalid.") from exc
    if issue_date and due_date and due_date < issue_date:
        raise HTTPException(status_code=422, detail="Due date is before issue date.")
    return _save_sales_invoice(
        SalesInvoice(
            invoice_number=data.invoice_number or "UNNUMBERED",
            business_id=business_id,
            customer_name=data.supplier_name or "UNKNOWN CUSTOMER",
            counterparty_id=_counterparty(
                business_id,
                data.supplier_name or "UNKNOWN CUSTOMER",
                "customer",
                session,
            ).id,
            subtotal=subtotal,
            tax_amount=tax,
            total_amount=total,
            issue_date=issue_date or date.today(),
            due_date=due_date,
            status="draft" if result.status == "ok" else "needs_review",
            review_notes="; ".join(result.review_reasons) if result.review_reasons else None,
        ),
        [
            SalesLineInput(
                description=item.description,
                quantity=Decimal(item.quantity),
                unit_price=Decimal(item.unit_price),
                tax_amount=Decimal(item.tax_amount),
                total_amount=Decimal(item.total_amount),
            )
            for item in data.line_items
        ],
        session,
    )


@router.get("/sales/invoices", response_model=list[SalesInvoice])
def list_sales_invoices(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_id = get_current_business_id(user, session)
    return session.exec(select(SalesInvoice).where(SalesInvoice.business_id == business_id)).all()


@router.post("/sales/invoices/{invoice_id}/issue", response_model=SalesInvoice)
def issue_sales_invoice(
    invoice_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    invoice = session.get(SalesInvoice, invoice_id)
    if invoice is None or invoice.business_id != get_current_business_id(user, session):
        raise HTTPException(status_code=404, detail="Sales invoice not found.")
    require_business_access(invoice.business_id, user, session, minimum_role="accountant")
    if invoice.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sales invoices can be issued.")
    if invoice.review_notes:
        raise HTTPException(status_code=409, detail="Sales invoice requires correction before issue.")
    _validate_sales_amounts(invoice.subtotal, invoice.tax_amount, invoice.total_amount)
    invoice.status = "issued"
    session.add(invoice)
    session.commit()
    return invoice


@router.put("/sales/invoices/{invoice_id}", response_model=SalesInvoice)
def correct_sales_invoice(
    invoice_id: str,
    request: SalesInvoiceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    invoice = session.get(SalesInvoice, invoice_id)
    if invoice is None or invoice.business_id != get_current_business_id(user, session):
        raise HTTPException(status_code=404, detail="Sales invoice not found.")
    require_business_access(invoice.business_id, user, session, minimum_role="accountant")
    request.business_id = invoice.business_id
    _validate_sales_amounts(request.subtotal, request.tax_amount, request.total_amount)
    if request.due_date < request.issue_date if request.due_date else False:
        raise HTTPException(status_code=422, detail="Due date is before issue date.")
    duplicate = session.exec(
        select(SalesInvoice).where(
            SalesInvoice.business_id == request.business_id,
            SalesInvoice.invoice_number == request.invoice_number,
            SalesInvoice.id != invoice_id,
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Invoice number already exists for this business.")
    invoice.invoice_number = request.invoice_number
    invoice.customer_name = request.customer_name
    invoice.subtotal = request.subtotal
    invoice.tax_amount = request.tax_amount
    invoice.total_amount = request.total_amount
    invoice.issue_date = request.issue_date
    invoice.due_date = request.due_date
    invoice.status = "draft"
    invoice.review_notes = None
    invoice.counterparty_id = _counterparty(
        request.business_id,
        request.customer_name,
        "customer",
        session,
    ).id
    for item in session.exec(
        select(SalesInvoiceLineItem).where(SalesInvoiceLineItem.invoice_id == invoice.id)
    ).all():
        session.delete(item)
    session.add(invoice)
    session.flush()
    if request.line_items and abs(
        sum((item.total_amount for item in request.line_items), Decimal("0.00"))
        - request.total_amount
    ) > Decimal("0.05"):
        raise HTTPException(status_code=422, detail="Invoice line items must equal invoice total.")
    for item in request.line_items:
        session.add(SalesInvoiceLineItem(invoice_id=invoice.id, **item.model_dump()))
    session.commit()
    session.refresh(invoice)
    return invoice


@router.post("/sales/invoices/{invoice_id}/receipts", response_model=SalesInvoice)
def record_receipt(
    invoice_id: str,
    request: ReceiptCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    invoice = session.get(SalesInvoice, invoice_id)
    if invoice is None or invoice.business_id != get_current_business_id(user, session):
        raise HTTPException(status_code=404, detail="Sales invoice not found.")
    require_business_access(invoice.business_id, user, session, minimum_role="accountant")
    if invoice.status not in {"issued", "partially_paid"}:
        raise HTTPException(status_code=409, detail="Sales invoice is not receivable.")
    if request.amount <= 0 or invoice.amount_received + request.amount > invoice.total_amount:
        raise HTTPException(status_code=422, detail="Receipt exceeds the outstanding balance.")
    invoice.amount_received += request.amount
    invoice.status = "paid" if invoice.amount_received == invoice.total_amount else "partially_paid"
    session.add(invoice)
    session.commit()
    return invoice


@router.post("/ledger/accounts", response_model=LedgerAccount)
def create_ledger_account(
    account: LedgerAccountCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _set_current_business(account, user, session)
    if session.exec(
        select(LedgerAccount).where(
            LedgerAccount.business_id == account.business_id,
            LedgerAccount.code == account.code,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Ledger account code already exists.")
    account = LedgerAccount(**account.model_dump())
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@router.get("/ledger/accounts", response_model=list[LedgerAccount])
def list_ledger_accounts(
    business_id: str | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    current_business_id = get_current_business_id(user, session)
    if business_id is not None and business_id != current_business_id:
        raise HTTPException(status_code=403, detail="Business must match the current business.")
    business_id = current_business_id
    _require_business(business_id, session)
    return session.exec(
        select(LedgerAccount).where(LedgerAccount.business_id == business_id)
    ).all()


@router.post("/ledger/journals", response_model=JournalEntry)
def post_journal(
    request: JournalCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _set_current_business(request, user, session)
    if not request.lines or any(line.debit < 0 or line.credit < 0 for line in request.lines):
        raise HTTPException(status_code=422, detail="Journal lines must have non-negative amounts.")
    debits = sum((line.debit for line in request.lines), Decimal("0.00"))
    credits = sum((line.credit for line in request.lines), Decimal("0.00"))
    if debits <= 0 or debits != credits:
        raise HTTPException(status_code=422, detail="Journal debits and credits must balance.")
    account_codes = {line.account_code for line in request.lines}
    active_accounts = {
        account.code
        for account in session.exec(
            select(LedgerAccount).where(
                LedgerAccount.code.in_(account_codes),
                LedgerAccount.is_active == True,
            )
        ).all()
    }
    if active_accounts != account_codes:
        raise HTTPException(status_code=422, detail="Journal contains an unknown or inactive account.")
    entry = JournalEntry(
        business_id=request.business_id,
        source_type=request.source_type,
        source_id=request.source_id,
        description=request.description,
    )
    session.add(entry)
    session.flush()
    for line in request.lines:
        session.add(JournalLine(journal_entry_id=entry.id, **line.model_dump()))
    session.commit()
    session.refresh(entry)
    return entry


@router.get("/ledger/journals", response_model=list[JournalEntry])
def list_journals(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_id = get_current_business_id(user, session)
    return session.exec(select(JournalEntry).where(JournalEntry.business_id == business_id)).all()


@router.get("/reports/summary")
def accounting_summary(
    business_id: str | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_id = business_id or get_current_business_id(user, session)
    if business_id != get_current_business_id(user, session):
        raise HTTPException(status_code=403, detail="Business must match the current business.")
    _require_business(business_id, session)
    require_business_access(business_id, user, session)
    sales = session.exec(select(SalesInvoice).where(SalesInvoice.business_id == business_id)).all()
    purchases = session.exec(select(APInvoice).where(APInvoice.business_id == business_id)).all()
    payroll = session.exec(select(PayrollRun).where(PayrollRun.business_id == business_id)).all()

    revenue = sum(
        (invoice.total_amount for invoice in sales if invoice.status in {"issued", "partially_paid", "paid"}),
        Decimal("0.00"),
    )
    received = sum((invoice.amount_received for invoice in sales), Decimal("0.00"))
    payables = sum(
        (invoice.total_amount for invoice in purchases if invoice.status != "paid"),
        Decimal("0.00"),
    )
    paid_purchases = sum(
        (invoice.total_amount for invoice in purchases if invoice.status == "paid"),
        Decimal("0.00"),
    )
    payroll_cost = sum((run.total_employer_cost for run in payroll), Decimal("0.00"))
    return {
        "currency": "MYR",
        "revenue": revenue,
        "received": received,
        "receivables": revenue - received,
        "paid_purchases": paid_purchases,
        "payables": payables,
        "payroll_cost": payroll_cost,
        "operating_result": revenue - paid_purchases - payroll_cost,
    }


@router.post("/payroll/employees", response_model=Employee)
def create_employee(
    request: EmployeeCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _set_current_business(request, user, session)
    employee = Employee(**request.model_dump())
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.get("/payroll/employees", response_model=list[Employee])
def list_employees(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_id = get_current_business_id(user, session)
    return session.exec(select(Employee).where(Employee.business_id == business_id)).all()


@router.delete("/payroll/employees/{employee_id}", response_model=Employee)
def deactivate_employee(
    employee_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if isinstance(user, User):
        if employee.business_id != get_current_business_id(user, session):
            raise HTTPException(status_code=404, detail="Employee not found.")
        require_business_access(employee.business_id, user, session, minimum_role="accountant")
    employee.status = "inactive"
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.post("/payroll/employees/{employee_id}/reactivate", response_model=Employee)
def reactivate_employee(
    employee_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if isinstance(user, User):
        if employee.business_id != get_current_business_id(user, session):
            raise HTTPException(status_code=404, detail="Employee not found.")
        require_business_access(employee.business_id, user, session, minimum_role="accountant")
    if employee.status == "active":
        raise HTTPException(status_code=409, detail="Employee is already active.")
    employee.status = "active"
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.patch("/payroll/employees/{employee_id}", response_model=Employee)
def update_employee(
    employee_id: str,
    request: EmployeeUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if isinstance(user, User):
        if employee.business_id != get_current_business_id(user, session):
            raise HTTPException(status_code=404, detail="Employee not found.")
        require_business_access(employee.business_id, user, session, minimum_role="accountant")
    if request.employee_name is None and request.gross_salary is None:
        raise HTTPException(status_code=422, detail="At least one employee field is required.")
    if request.employee_name is not None:
        employee.employee_name = request.employee_name
    if request.gross_salary is not None:
        employee.gross_salary = request.gross_salary
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.post("/payroll/runs", response_model=PayrollRun)
def create_payroll_run(
    payroll_month: date,
    business_id: str | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_id = business_id or get_current_business_id(user, session)
    if business_id != get_current_business_id(user, session):
        raise HTTPException(status_code=403, detail="Business must match the current business.")
    _require_business(business_id, session)
    employees = session.exec(
        select(Employee).where(
            Employee.status == "active",
            Employee.business_id == business_id,
        )
    ).all()
    total_gross = sum((employee.gross_salary for employee in employees), Decimal("0.00"))
    run = PayrollRun(
        payroll_month=payroll_month,
        business_id=business_id,
        total_gross=total_gross,
        total_net=total_gross,
        total_employer_cost=total_gross,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


@router.post("/credit/facilities", response_model=CreditFacility)
def create_credit_facility(
    request: CreditFacilityCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _set_current_business(request, user, session)
    if request.requested_amount <= 0 or request.monthly_payment < 0 or request.term_months < 0:
        raise HTTPException(status_code=422, detail="Credit facility terms are invalid.")
    facility = CreditFacility(**request.model_dump())
    session.add(facility)
    session.commit()
    session.refresh(facility)
    return facility


@router.get("/credit/facilities", response_model=list[CreditFacility])
def list_credit_facilities(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    business_id = get_current_business_id(user, session)
    return session.exec(select(CreditFacility).where(CreditFacility.business_id == business_id)).all()


@router.post("/credit/facilities/{facility_id}/approve", response_model=CreditFacility)
def approve_credit_facility(
    facility_id: str,
    approved_amount: Decimal,
    session: Session = Depends(get_session),
):
    facility = session.get(CreditFacility, facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail="Credit facility not found.")
    if facility.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending facilities can be approved.")
    if approved_amount <= 0 or approved_amount > facility.requested_amount:
        raise HTTPException(status_code=422, detail="Approved amount is invalid.")
    facility.approved_amount = approved_amount
    facility.outstanding_amount = approved_amount
    facility.status = "active"
    session.add(facility)
    session.commit()
    session.refresh(facility)
    return facility


@router.post("/credit/facilities/{facility_id}/deny", response_model=CreditFacility)
def deny_credit_facility(facility_id: str, session: Session = Depends(get_session)):
    facility = session.get(CreditFacility, facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail="Credit facility not found.")
    if facility.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending facilities can be denied.")
    facility.status = "denied"
    session.add(facility)
    session.commit()
    session.refresh(facility)
    return facility


@router.post("/credit/facilities/{facility_id}/payments", response_model=CreditFacility)
def record_credit_payment(
    facility_id: str,
    request: ReceiptCreate,
    session: Session = Depends(get_session),
):
    facility = session.get(CreditFacility, facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail="Credit facility not found.")
    if facility.status != "active":
        raise HTTPException(status_code=409, detail="Credit facility is not active.")
    if request.amount <= 0 or request.amount > facility.outstanding_amount:
        raise HTTPException(status_code=422, detail="Payment exceeds outstanding credit.")
    session.add(CreditPayment(facility_id=facility.id, amount=request.amount))
    facility.outstanding_amount -= request.amount
    if facility.outstanding_amount == 0:
        facility.status = "paid_off"
    session.add(facility)
    session.commit()
    session.refresh(facility)
    return facility
