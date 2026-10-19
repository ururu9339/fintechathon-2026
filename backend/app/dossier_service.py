import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import Session, select

from .models import (
    APInvoice,
    BusinessProfile,
    CashBalance,
    CreditFacility,
    CreditDossier,
    LoanRequest,
    OwnershipRecord,
    PayrollRun,
    SalesInvoice,
    StatutoryRemittance,
)

CENT = Decimal("0.01")


def money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def proposed_installment(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    monthly_rate = annual_rate / Decimal("100") / Decimal("12")
    if monthly_rate == 0:
        return principal / Decimal(months)
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-months))


def _ratio(numerator: Decimal, denominator: Decimal) -> str | None:
    if denominator == 0:
        return None
    return money(numerator / denominator)


def build_dossier_snapshot(
    business_id: str,
    period_start: date,
    period_end: date,
    session: Session,
    loan_request_id: str | None = None,
) -> tuple[dict, str]:
    business = session.get(BusinessProfile, business_id)
    if business is None:
        raise ValueError("Business profile not found.")
    if period_end < period_start:
        raise ValueError("Dossier period end must not precede period start.")

    sales = session.exec(select(SalesInvoice).where(
        SalesInvoice.business_id == business_id,
        SalesInvoice.issue_date >= period_start,
        SalesInvoice.issue_date <= period_end,
        SalesInvoice.status.in_(["issued", "partially_paid", "paid"]),
    )).all()
    purchases = session.exec(select(APInvoice).where(
        APInvoice.business_id == business_id,
        APInvoice.issue_date >= period_start,
        APInvoice.issue_date <= period_end,
        APInvoice.status.in_(["approved", "paid"]),
    )).all()
    payroll = session.exec(select(PayrollRun).where(
        PayrollRun.business_id == business_id,
        PayrollRun.payroll_month >= period_start,
        PayrollRun.payroll_month <= period_end,
        PayrollRun.status.in_(["approved", "posted", "paid"]),
    )).all()
    facilities = session.exec(select(CreditFacility).where(
        CreditFacility.business_id == business_id,
        CreditFacility.status == "active",
    )).all()
    remittances = session.exec(select(StatutoryRemittance).where(
        StatutoryRemittance.business_id == business_id,
        StatutoryRemittance.payroll_month >= period_start,
        StatutoryRemittance.payroll_month <= period_end,
    )).all()
    ownership = session.exec(select(OwnershipRecord).where(
        OwnershipRecord.business_id == business_id
    )).all()
    cash = session.exec(select(CashBalance).where(
        CashBalance.business_id == business_id,
        CashBalance.as_of_date <= period_end,
    ).order_by(CashBalance.as_of_date.desc())).first()

    loan = session.get(LoanRequest, loan_request_id) if loan_request_id else None
    gaps: list[str] = []
    if not payroll:
        gaps.append("No approved payroll run exists for the reporting period.")
    if cash is None:
        gaps.append("No cash balance exists on or before the reporting period end.")
    if not ownership:
        gaps.append("No ownership records exist.")
    if loan_request_id and (loan is None or loan.business_id != business_id):
        raise ValueError("Loan request does not belong to this business.")
    if loan_request_id and loan.status != "approved":
        gaps.append("The selected loan request is not approved and was excluded.")
        loan = None

    revenue = sum((item.subtotal for item in sales), Decimal("0"))
    purchase_cost = sum((item.subtotal for item in purchases), Decimal("0"))
    payroll_cost = sum((item.total_employer_cost for item in payroll), Decimal("0"))
    operating_costs = purchase_cost + payroll_cost
    months = max(1, (period_end.year - period_start.year) * 12 + period_end.month - period_start.month + 1)
    operating_surplus = (revenue - operating_costs) / Decimal(months)
    existing_debt = sum((item.monthly_payment for item in facilities), Decimal("0"))
    installment = Decimal("0")
    if loan:
        installment = proposed_installment(loan.requested_amount, loan.annual_rate, loan.tenor_months)
    debt_after = existing_debt + installment

    customer_totals: dict[str, Decimal] = {}
    for item in sales:
        customer_totals[item.customer_name] = customer_totals.get(item.customer_name, Decimal("0")) + item.subtotal
    supplier_totals: dict[str, Decimal] = {}
    for item in purchases:
        supplier_totals[item.supplier_name] = supplier_totals.get(item.supplier_name, Decimal("0")) + item.subtotal

    statutory: dict[str, dict[str, int]] = {}
    for item in remittances:
        bucket = statutory.setdefault(item.statutory_type, {"on_time": 0, "late": 0, "missing": 0})
        bucket["missing" if item.paid_date is None else ("on_time" if item.paid_date <= item.due_date else "late")] += 1

    snapshot = {
        "applicant": {
            "business_id": business.id,
            "legal_name": business.legal_name,
            "registration_type": business.registration_type,
            "registration_number": business.registration_number,
            "registration_status": business.registration_status,
            "msic_code": business.msic_code,
            "sector_category": business.sector_category,
            "ownership": [
                {"owner_reference": item.owner_reference, "share_percentage": money(item.share_percentage),
                 "is_malaysian_citizen": item.is_malaysian_citizen}
                for item in ownership
            ],
        },
        "period": {"start": period_start.isoformat(), "end": period_end.isoformat()},
        "metrics": {
            "revenue_excluding_tax": money(revenue),
            "approved_purchase_cost_excluding_tax": money(purchase_cost),
            "approved_payroll_employer_cost": money(payroll_cost),
            "operating_surplus_proxy_monthly": money(operating_surplus),
            "existing_monthly_debt_service": money(existing_debt),
            "proposed_monthly_installment": money(installment),
            "dscr_baseline": _ratio(operating_surplus, existing_debt),
            "dscr_stressed": _ratio(operating_surplus, debt_after),
            "headroom_after_proposed_debt": money(operating_surplus - debt_after),
            "latest_cash_balance": money(cash.amount) if cash else None,
            "customer_concentration": _ratio(max(customer_totals.values(), default=Decimal("0")), revenue),
            "supplier_concentration": _ratio(max(supplier_totals.values(), default=Decimal("0")), purchase_cost),
        },
        "statutory_remittances": statutory,
        "data_gaps": gaps,
        "limitations": [
            "This is a draft analysis of recorded data, not an audit, certification, approval, or lender decision.",
            "Operating surplus is a proxy and excludes working-capital changes, capital expenditure, and non-cash items.",
            "Only approved or issued source records were included; draft and review-needed records were excluded.",
        ],
        "traceability": {
            "sales_invoice_ids": sorted(item.id for item in sales),
            "ap_invoice_ids": sorted(item.id for item in purchases),
            "payroll_run_ids": sorted(item.id for item in payroll),
            "credit_facility_ids": sorted(item.id for item in facilities),
            "statutory_remittance_ids": sorted(item.id for item in remittances),
            "cash_balance_id": cash.id if cash else None,
            "loan_request_id": loan.id if loan else None,
        },
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return snapshot, hashlib.sha256(canonical.encode()).hexdigest()


def create_dossier(business_id: str, period_start: date, period_end: date, session: Session,
                   loan_request_id: str | None = None) -> CreditDossier:
    snapshot, input_hash = build_dossier_snapshot(
        business_id, period_start, period_end, session, loan_request_id
    )
    dossier = CreditDossier(
        business_id=business_id, period_start=period_start, period_end=period_end,
        loan_request_id=loan_request_id, snapshot=snapshot, input_hash=input_hash,
    )
    session.add(dossier)
    session.commit()
    session.refresh(dossier)
    return dossier
