"""Deterministic cash forecasting and financing-rate comparisons."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping


@dataclass(frozen=True)
class WeeklyCashForecast:
    weekly_inflows: tuple[Decimal, ...]
    weekly_outflows: tuple[Decimal, ...]
    balances: tuple[Decimal, ...]


@dataclass(frozen=True)
class FinancingOffer:
    lender: str
    rate: Decimal
    rate_basis: str
    periods_per_year: int = 12

    @property
    def effective_annual_rate(self) -> Decimal:
        rate = Decimal(str(self.rate))
        if self.rate_basis == "monthly_flat_fee":
            return periodic_rate_to_ear(rate, self.periods_per_year)
        if self.rate_basis == "nominal_annual":
            return nominal_annual_rate_to_ear(rate, self.periods_per_year)
        if self.rate_basis == "effective_annual":
            if not rate.is_finite() or rate <= Decimal("-1"):
                raise ValueError("Effective annual rate must be greater than -100%.")
            return rate
        raise ValueError(f"Unsupported financing rate basis: {self.rate_basis}")


def _decimal_amount(value: object, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite decimal amount.") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field_name} must be a finite, non-negative amount.")
    return amount


def build_weekly_cash_forecast(
    transactions: Iterable[Mapping[str, object]],
    forecast_start: date,
    opening_balance: Decimal,
    horizon_weeks: int = 13,
) -> WeeklyCashForecast:
    """Bucket dated cash transactions by actual payment date and roll balances."""
    if horizon_weeks < 1:
        raise ValueError("Forecast horizon must be at least one week.")
    try:
        opening = Decimal(str(opening_balance))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Opening balance must be a finite decimal amount.") from exc
    if not opening.is_finite():
        raise ValueError("Opening balance must be finite.")

    inflows = [Decimal("0")] * horizon_weeks
    outflows = [Decimal("0")] * horizon_weeks
    for index, transaction in enumerate(transactions):
        actual_date_value = transaction.get("actual_paid_date")
        if not actual_date_value:
            raise ValueError(f"Transaction {index} is missing actual_paid_date.")
        try:
            actual_date = (
                actual_date_value.date()
                if isinstance(actual_date_value, datetime)
                else actual_date_value
                if isinstance(actual_date_value, date)
                else date.fromisoformat(str(actual_date_value))
            )
        except ValueError as exc:
            raise ValueError(
                f"Transaction {index} has an invalid actual_paid_date."
            ) from exc

        week_index = (actual_date - forecast_start).days // 7
        if not 0 <= week_index < horizon_weeks:
            continue
        inflow = _decimal_amount(transaction.get("Inflow"), "Inflow")
        outflow = _decimal_amount(transaction.get("Outflow"), "Outflow")
        if inflow and outflow:
            raise ValueError(
                f"Transaction {index} cannot contain both Inflow and Outflow."
            )
        inflows[week_index] += inflow
        outflows[week_index] += outflow

    balances = [opening]
    for inflow, outflow in zip(inflows, outflows):
        balances.append(balances[-1] + inflow - outflow)
    return WeeklyCashForecast(tuple(inflows), tuple(outflows), tuple(balances))


def periodic_rate_to_ear(
    periodic_rate: Decimal,
    periods_per_year: int = 12,
) -> Decimal:
    """Compound a periodic rate into an effective annual rate."""
    periodic_rate = Decimal(str(periodic_rate))
    if not periodic_rate.is_finite() or periodic_rate <= Decimal("-1"):
        raise ValueError("Periodic rate must be finite and greater than -100%.")
    if periods_per_year < 1:
        raise ValueError("Compounding periods per year must be positive.")
    return (Decimal("1") + periodic_rate) ** periods_per_year - Decimal("1")


def nominal_annual_rate_to_ear(
    nominal_annual_rate: Decimal,
    periods_per_year: int = 12,
) -> Decimal:
    """Convert a nominal annual rate with periodic compounding to its EAR."""
    nominal_annual_rate = Decimal(str(nominal_annual_rate))
    if not nominal_annual_rate.is_finite() or nominal_annual_rate <= Decimal("-1"):
        raise ValueError("Nominal annual rate must be finite and greater than -100%.")
    if periods_per_year < 1:
        raise ValueError("Compounding periods per year must be positive.")
    return periodic_rate_to_ear(
        nominal_annual_rate / periods_per_year,
        periods_per_year,
    )


def select_lowest_ear_offer(
    offers: Iterable[FinancingOffer],
) -> FinancingOffer:
    """Select the lowest EAR offer, breaking exact ties by lender name."""
    candidates = list(offers)
    if not candidates:
        raise ValueError("At least one financing offer is required.")
    return min(
        candidates,
        key=lambda offer: (offer.effective_annual_rate, offer.lender),
    )
