from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlmodel import Session, select

from agent.extract import llm_multimodal_extractor

from ..db import get_session
from ..auth import get_current_user, require_business_access
from ..models import (
    APInvoice,
    APInvoiceLineItem,
    BusinessProfile,
    Counterparty,
    ExtractionResult,
    Mandate,
    PaymentRequest,
    PaymentResult,
    User,
)

router = APIRouter(
    prefix="/api",
    tags=["invoices"],
    dependencies=[Depends(get_current_user)],
)


class InvoiceLineInput(BaseModel):
    description: str
    quantity: Decimal = Decimal("1.00")
    unit_price: Decimal = Decimal("0.00")
    subtotal: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")


class ExpenseInvoiceForm(BaseModel):
    business_id: str
    mandate_id: str | None = None
    invoice_number: str
    supplier_name: str
    subtotal: Decimal
    tax_amount: Decimal = Decimal("0.00")
    total_amount: Decimal
    issue_date: date
    due_date: date | None = None
    line_items: list[InvoiceLineInput] = []


class ProviderInvoiceWebhook(BaseModel):
    provider_event_id: str = Field(min_length=1)
    source_invoice_id: str = Field(min_length=1)
    supplier_name: str = Field(min_length=1)
    supplier_tin: str | None = None
    invoice_number: str = Field(min_length=1)
    subtotal: Decimal = Field(ge=0)
    tax_amount: Decimal = Field(ge=0)
    total_amount: Decimal = Field(gt=0)
    issue_date: date
    due_date: date | None = None
    currency: str = Field(default="MYR", min_length=3, max_length=3)


def _validate_invoice_amounts(subtotal: Decimal, tax: Decimal, total: Decimal) -> None:
    if subtotal < 0 or tax < 0 or total <= 0:
        raise HTTPException(status_code=422, detail="Invoice amounts are invalid.")
    if abs(subtotal + tax - total) > Decimal("0.05"):
        raise HTTPException(status_code=422, detail="Subtotal plus tax must equal total.")


def _validate_line_items(items: list[InvoiceLineInput], total: Decimal) -> None:
    if not items:
        return
    if any(
        item.quantity <= 0
        or item.unit_price < 0
        or item.subtotal < 0
        or item.tax_amount < 0
        or item.total_amount <= 0
        for item in items
    ):
        raise HTTPException(status_code=422, detail="Invoice line items contain invalid amounts.")
    if abs(sum((item.total_amount for item in items), Decimal("0.00")) - total) > Decimal("0.05"):
        raise HTTPException(status_code=422, detail="Invoice line items must equal invoice total.")


def _save_expense_invoice(
    data: ExpenseInvoiceForm,
    session: Session,
) -> APInvoice:
    if session.get(BusinessProfile, data.business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    _validate_invoice_amounts(data.subtotal, data.tax_amount, data.total_amount)
    _validate_line_items(data.line_items, data.total_amount)
    if data.due_date and data.due_date < data.issue_date:
        raise HTTPException(status_code=422, detail="Due date is before issue date.")
    if session.exec(
        select(APInvoice).where(
            APInvoice.business_id == data.business_id,
            APInvoice.invoice_number == data.invoice_number,
        )
    ).first():
        raise HTTPException(status_code=409, detail="Invoice number already exists for this business.")
    counterparty = session.exec(
        select(Counterparty).where(
            Counterparty.business_id == data.business_id,
            Counterparty.name == data.supplier_name,
            Counterparty.party_type == "supplier",
        )
    ).first()
    if counterparty is None:
        counterparty = Counterparty(
            business_id=data.business_id,
            mandate_id=data.mandate_id,
            name=data.supplier_name,
            party_type="supplier",
        )
        session.add(counterparty)
        session.flush()
    invoice = APInvoice(
        invoice_number=data.invoice_number,
        business_id=data.business_id,
        counterparty_id=counterparty.id,
        supplier_name=data.supplier_name,
        subtotal=data.subtotal,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        issue_date=data.issue_date or date.today(),
        due_date=data.due_date,
        status="draft",
    )
    session.add(invoice)
    session.flush()
    for item in data.line_items:
        session.add(
            APInvoiceLineItem(invoice_id=invoice.id, **item.model_dump())
        )
    session.commit()
    session.refresh(invoice)
    return invoice


def _decimal(value: str, label: str, reasons: list[str]) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        reasons.append(f"{label} is not numeric.")
        return Decimal("0")


def _date(value: str, label: str, reasons: list[str]) -> date | None:
    if not value.strip():
        reasons.append(f"{label} is missing.")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        reasons.append(f"{label} is not a valid ISO date.")
        return None


@router.post("/invoices/upload", response_model=ExtractionResult)
async def upload_invoice(
    business_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if session.get(BusinessProfile, business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    require_business_access(business_id, user, session, minimum_role="accountant")
    result = llm_multimodal_extractor(file.filename or "upload.pdf", await file.read())
    if result.status == "failed" or result.invoice is None:
        return result


    data = result.invoice
    reasons = list(result.review_reasons)
    subtotal = _decimal(data.subtotal, "Subtotal", reasons)
    tax = _decimal(data.tax_amount, "Tax", reasons)
    total = _decimal(data.total_amount, "Total", reasons)
    issue_date = _date(data.issue_date, "Issue date", reasons)
    due_date = _date(data.due_date, "Due date", reasons) if data.due_date else None
    if issue_date and due_date and due_date < issue_date:
        reasons.append("Due date is before issue date.")
    line_items = [
        InvoiceLineInput(
            description=item.description,
            quantity=_decimal(item.quantity, "Line quantity", reasons),
            unit_price=_decimal(item.unit_price, "Line unit price", reasons),
            subtotal=_decimal(item.subtotal, "Line subtotal", reasons),
            tax_amount=_decimal(item.tax_amount, "Line tax", reasons),
            total_amount=_decimal(item.total_amount, "Line total", reasons),
        )
        for item in data.line_items
    ]
    if not reasons:
        _validate_invoice_amounts(subtotal, tax, total)
        _validate_line_items(line_items, total)
    counterparty = session.exec(
        select(Counterparty).where(
            Counterparty.business_id == business_id,
            Counterparty.name == (data.supplier_name or "UNKNOWN SUPPLIER"),
            Counterparty.party_type == "supplier",
        )
    ).first()
    if counterparty is None:
        counterparty = Counterparty(
            business_id=business_id,
            name=data.supplier_name or "UNKNOWN SUPPLIER",
            party_type="supplier",
        )
        session.add(counterparty)
        session.flush()
    draft = APInvoice(
        invoice_number=data.invoice_number or "UNNUMBERED",
        business_id=business_id,
        counterparty_id=counterparty.id,
        supplier_name=data.supplier_name or "UNKNOWN SUPPLIER",
        supplier_tin=data.supplier_tin or None,
        supplier_brn=data.supplier_brn or None,
        supplier_sst_number=data.supplier_sst_number or None,
        supplier_msic_code=data.supplier_msic_code or None,
        subtotal=subtotal,
        tax_amount=tax,
        total_amount=total,
        currency=data.currency or "MYR",
        issue_date=issue_date or date.today(),
        due_date=due_date,
        requires_individual_einvoice=total >= Decimal("10000.00"),
        status="draft" if not reasons else "needs_review",
        review_notes="; ".join(reasons) if reasons else None,
    )
    session.add(draft)
    session.flush()
    for item in line_items:
        session.add(
            APInvoiceLineItem(
                invoice_id=draft.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                tax_amount=item.tax_amount,
                total_amount=item.total_amount,
            )
        )
    if reasons:
        draft.status = "needs_review"
        draft.review_notes = "; ".join(reasons)
        result.status = "needs_review"
        result.reconciliation_ok = False
        result.review_reasons = reasons
    session.commit()
    result.invoice_id = draft.id
    return result


@router.post(
    "/businesses/{business_id}/invoice-intake/webhook",
    response_model=APInvoice,
)
def receive_provider_invoice(
    business_id: str,
    request: ProviderInvoiceWebhook,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if session.get(BusinessProfile, business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    require_business_access(business_id, user, session, minimum_role="accountant")
    if request.due_date and request.due_date < request.issue_date:
        raise HTTPException(status_code=422, detail="Due date is before issue date.")
    _validate_invoice_amounts(request.subtotal, request.tax_amount, request.total_amount)
    existing = session.exec(
        select(APInvoice).where(
            APInvoice.business_id == business_id,
            APInvoice.source_system == "provider_webhook",
            or_(
                APInvoice.source_event_id == request.provider_event_id,
                APInvoice.source_invoice_id == request.source_invoice_id,
            ),
        )
    ).first()
    if existing:
        return existing
    counterparty = session.exec(
        select(Counterparty).where(
            Counterparty.business_id == business_id,
            Counterparty.name == request.supplier_name,
            Counterparty.party_type == "supplier",
        )
    ).first()
    if counterparty is None:
        counterparty = Counterparty(
            business_id=business_id,
            name=request.supplier_name,
            party_type="supplier",
            tax_id=request.supplier_tin,
        )
        session.add(counterparty)
        session.flush()
    mandates = session.exec(
        select(Mandate).where(
            Mandate.business_id == business_id,
            Mandate.status == "active",
            Mandate.auto_pay == True,
        )
    ).all()
    selected = next(
        (
            item for item in mandates
            if (
                counterparty.id in item.allowed_counterparty_ids
                or request.supplier_name in item.allowed_suppliers
            )
            and (not item.require_verified_supplier or counterparty.is_verified)
            and request.total_amount <= item.transaction_limit
        ),
        None,
    )
    invoice = APInvoice(
        business_id=business_id,
        counterparty_id=counterparty.id,
        mandate_id=selected.id if selected else None,
        source_system="provider_webhook",
        source_event_id=request.provider_event_id,
        source_invoice_id=request.source_invoice_id,
        invoice_number=request.invoice_number,
        supplier_name=request.supplier_name,
        supplier_tin=request.supplier_tin,
        subtotal=request.subtotal,
        tax_amount=request.tax_amount,
        total_amount=request.total_amount,
        currency=request.currency,
        issue_date=request.issue_date,
        due_date=request.due_date,
        status="draft" if selected else "needs_review",
        review_notes=None if selected else "No matching auto-payment mandate.",
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    if selected:
        from ..db import get_treasurer

        treasurer = get_treasurer()
        treasurer.approve_invoice(invoice, session)
        payment = treasurer.pay_invoice(invoice, session)
        if payment.status != "approved":
            invoice.review_notes = payment.reason
            invoice.status = "needs_review"
            session.add(invoice)
            session.commit()
        session.refresh(invoice)
    return invoice


@router.post("/invoices", response_model=APInvoice)
def create_expense_invoice(
    request: ExpenseInvoiceForm,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_business_access(request.business_id, user, session, minimum_role="accountant")
    return _save_expense_invoice(request, session)


@router.get("/invoices", response_model=list[APInvoice])
def list_invoices(session: Session = Depends(get_session)):
    return session.exec(select(APInvoice)).all()


@router.get("/invoices/{invoice_id}", response_model=APInvoice)
def get_invoice(invoice_id: str, session: Session = Depends(get_session)):
    invoice = session.get(APInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return invoice


@router.post("/invoices/{invoice_id}/approve", response_model=APInvoice)
def approve_invoice(invoice_id: str, session: Session = Depends(get_session)):
    from ..db import get_treasurer

    invoice = session.get(APInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    try:
        get_treasurer().approve_invoice(invoice, session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return invoice


@router.put("/invoices/{invoice_id}", response_model=APInvoice)
def correct_invoice(
    invoice_id: str,
    request: ExpenseInvoiceForm,
    session: Session = Depends(get_session),
):
    invoice = session.get(APInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.business_id != request.business_id:
        raise HTTPException(status_code=409, detail="Business ownership cannot be changed.")
    _validate_invoice_amounts(request.subtotal, request.tax_amount, request.total_amount)
    _validate_line_items(request.line_items, request.total_amount)
    if request.due_date and request.due_date < request.issue_date:
        raise HTTPException(status_code=422, detail="Due date is before issue date.")
    counterparty = session.exec(
        select(Counterparty).where(
            Counterparty.business_id == request.business_id,
            Counterparty.name == request.supplier_name,
            Counterparty.party_type == "supplier",
        )
    ).first()
    if counterparty is None:
        counterparty = Counterparty(
            business_id=request.business_id,
            name=request.supplier_name,
            party_type="supplier",
        )
        session.add(counterparty)
        session.flush()
    invoice.invoice_number = request.invoice_number
    invoice.supplier_name = request.supplier_name
    invoice.counterparty_id = counterparty.id
    invoice.subtotal = request.subtotal
    invoice.tax_amount = request.tax_amount
    invoice.total_amount = request.total_amount
    invoice.issue_date = request.issue_date
    invoice.due_date = request.due_date
    invoice.status = "draft"
    invoice.review_notes = None
    for item in session.exec(
        select(APInvoiceLineItem).where(APInvoiceLineItem.invoice_id == invoice.id)
    ).all():
        session.delete(item)
    session.add(invoice)
    session.flush()
    for item in request.line_items:
        session.add(APInvoiceLineItem(invoice_id=invoice.id, **item.model_dump()))
    session.commit()
    session.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/pay", response_model=PaymentResult)
def pay_invoice(
    invoice_id: str,
    session: Session = Depends(get_session),
):
    from ..db import get_treasurer

    invoice = session.get(APInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return get_treasurer().pay_invoice(invoice, session)


@router.post("/payments", response_model=PaymentResult)
def create_payment(
    request: PaymentRequest,
    session: Session = Depends(get_session),
):
    from ..db import get_treasurer

    result = get_treasurer().pay(request, session)
    request.status = result.status
    session.add(request)
    session.commit()
    return result


@router.get("/payments", response_model=list[PaymentRequest])
def list_payments(session: Session = Depends(get_session)):
    return session.exec(select(PaymentRequest)).all()
