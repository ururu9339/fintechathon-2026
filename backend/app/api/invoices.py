from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session, select

from agent.extract import llm_multimodal_extractor

from ..db import get_session
from ..models import (
    APInvoice,
    APInvoiceLineItem,
    ExtractionResult,
    PaymentRequest,
    PaymentResult,
)

router = APIRouter(prefix="/api", tags=["invoices"])


def _decimal(value: str, label: str, reasons: list[str]) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        reasons.append(f"{label} is not numeric.")
        return Decimal("0")


@router.post("/invoices/upload", response_model=ExtractionResult)
async def upload_invoice(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    result = llm_multimodal_extractor(file.filename or "upload.pdf", await file.read())
    if result.status == "failed" or result.invoice is None:
        return result

    data = result.invoice
    reasons = list(result.review_reasons)
    subtotal = _decimal(data.subtotal, "Subtotal", reasons)
    tax = _decimal(data.tax_amount, "Tax", reasons)
    total = _decimal(data.total_amount, "Total", reasons)
    draft = APInvoice(
        invoice_number=data.invoice_number or "UNNUMBERED",
        supplier_name=data.supplier_name or "UNKNOWN SUPPLIER",
        supplier_tin=data.supplier_tin or None,
        supplier_brn=data.supplier_brn or None,
        supplier_sst_number=data.supplier_sst_number or None,
        supplier_msic_code=data.supplier_msic_code or None,
        subtotal=subtotal,
        tax_amount=tax,
        total_amount=total,
        currency=data.currency or "MYR",
        requires_individual_einvoice=total >= Decimal("10000.00"),
        status="draft" if not reasons else "needs_review",
        review_notes="; ".join(reasons) if reasons else None,
    )
    session.add(draft)
    session.flush()
    for item in data.line_items:
        session.add(
            APInvoiceLineItem(
                invoice_id=draft.id,
                description=item.description,
                quantity=_decimal(item.quantity, "Line quantity", reasons),
                unit_price=_decimal(item.unit_price, "Line unit price", reasons),
                subtotal=_decimal(item.subtotal, "Line subtotal", reasons),
                sst_rate=_decimal(item.sst_rate, "Line SST rate", reasons),
                sst_type=item.sst_type,
                tax_amount=_decimal(item.tax_amount, "Line tax", reasons),
                total_amount=_decimal(item.total_amount, "Line total", reasons),
            )
        )
    if reasons:
        draft.status = "needs_review"
        draft.review_notes = "; ".join(reasons)
        result.status = "needs_review"
        result.reconciliation_ok = False
        result.review_reasons = reasons
    session.commit()
    return result


@router.post("/payments", response_model=PaymentResult)
def create_payment(
    request: PaymentRequest,
    session: Session = Depends(get_session),
):
    from ..db import get_treasurer

    result = get_treasurer().pay(request, session)
    session.add(request)
    session.commit()
    return result


@router.get("/payments", response_model=list[PaymentRequest])
def list_payments(session: Session = Depends(get_session)):
    return session.exec(select(PaymentRequest)).all()
