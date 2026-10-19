from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from .models import (
    APInvoice,
    BusinessProfile,
    CashBalance,
    CreditFacility,
    ForecastSnapshot,
    PayrollRun,
    SalesInvoice,
)


def build_forecast(
    business_id: str,
    session: Session,
    horizon_days: int = 90,
    persist: bool = True,
) -> ForecastSnapshot:
    if session.get(BusinessProfile, business_id) is None:
        raise ValueError("Business profile not found.")
    if horizon_days not in {30, 60, 90}:
        raise ValueError("Forecast horizon must be 30, 60, or 90 days.")

    today = date.today()
    latest_cash = session.exec(
        select(CashBalance).where(
            CashBalance.business_id == business_id,
            CashBalance.as_of_date <= today,
        ).order_by(CashBalance.as_of_date.desc())
    ).first()
    balance = latest_cash.amount if latest_cash else Decimal("0")
    sales = session.exec(select(SalesInvoice).where(
        SalesInvoice.business_id == business_id,
        SalesInvoice.status.in_(["issued", "partially_paid", "paid"]),
    )).all()
    purchases = session.exec(select(APInvoice).where(
        APInvoice.business_id == business_id,
        APInvoice.status.in_(["approved", "paid"]),
    )).all()
    payroll = session.exec(select(PayrollRun).where(
        PayrollRun.business_id == business_id,
        PayrollRun.status.in_(["approved", "posted", "paid"]),
    )).all()
    facilities = session.exec(select(CreditFacility).where(
        CreditFacility.business_id == business_id,
        CreditFacility.status == "active",
    )).all()

    recent_start = today - timedelta(days=90)
    recent_sales = [item for item in sales if item.issue_date >= recent_start]
    recent_purchases = [item for item in purchases if item.issue_date >= recent_start]
    avg_daily_inflow = sum((item.subtotal for item in recent_sales), Decimal("0")) / Decimal("90")
    avg_daily_outflow = (
        sum((item.subtotal for item in recent_purchases), Decimal("0"))
        + sum((item.total_employer_cost for item in payroll), Decimal("0")) / Decimal("12")
    ) / Decimal("90")
    daily_debt = sum((item.monthly_payment for item in facilities), Decimal("0")) / Decimal("30")

    points = []
    for day in range(1, horizon_days + 1):
        projected = balance + (avg_daily_inflow - avg_daily_outflow - daily_debt) * Decimal(day)
        points.append({"date": (today + timedelta(days=day)).isoformat(), "balance": str(projected.quantize(Decimal("0.01")))})
    minimum = min((Decimal(point["balance"]) for point in points), default=balance)
    alerts = []
    if minimum < 0:
        alerts.append({
            "severity": "high",
            "alert_type": "cash_shortfall",
            "title": "Projected cash shortfall",
            "message": f"Projected balance reaches {minimum.quantize(Decimal('0.01'))} MYR within {horizon_days} days.",
            "suggested_action": "Review unpaid receivables, upcoming supplier bills, and financing needs.",
        })
    elif minimum < Decimal("5000"):
        alerts.append({
            "severity": "medium",
            "alert_type": "low_cash_buffer",
            "title": "Projected low cash buffer",
            "message": f"Projected minimum balance is {minimum.quantize(Decimal('0.01'))} MYR.",
            "suggested_action": "Review payment timing and preserve a cash buffer.",
        })

    snapshot = ForecastSnapshot(
        business_id=business_id,
        horizon_days=horizon_days,
        snapshot={
            "currency": "MYR",
            "as_of": today.isoformat(),
            "starting_balance": str(balance.quantize(Decimal("0.01"))),
            "average_daily_inflow": str(avg_daily_inflow.quantize(Decimal("0.01"))),
            "average_daily_outflow": str(avg_daily_outflow.quantize(Decimal("0.01"))),
            "average_daily_debt_service": str(daily_debt.quantize(Decimal("0.01"))),
            "minimum_projected_balance": str(minimum.quantize(Decimal("0.01"))),
            "points": points,
            "alerts": alerts,
            "limitations": [
                "Projection uses recent recorded approved/issued activity and assumes the recent daily average continues.",
                "It does not model seasonality, one-off commitments, taxes not recorded, or unexpected events.",
            ],
        },
    )
    if persist:
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
    return snapshot
