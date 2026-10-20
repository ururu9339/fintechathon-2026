from datetime import date
from decimal import Decimal

import pytest

from backend.app.finance import (
    FinancingOffer,
    build_weekly_cash_forecast,
    nominal_annual_rate_to_ear,
    periodic_rate_to_ear,
    select_lowest_ear_offer,
)


def test_weekly_cash_forecast_buckets_transactions_and_rolls_balances():
    forecast = build_weekly_cash_forecast(
        [
            {
                "actual_paid_date": date(2026, 1, 1),
                "Inflow": "48000.00",
                "Outflow": "0.00",
            },
            {
                "actual_paid_date": date(2026, 1, 8),
                "Inflow": "0.00",
                "Outflow": "1250.00",
            },
        ],
        date(2026, 1, 1),
        Decimal("50000.00"),
        horizon_weeks=2,
    )

    assert forecast.weekly_inflows == (Decimal("48000.00"), Decimal("0"))
    assert forecast.weekly_outflows == (Decimal("0"), Decimal("1250.00"))
    assert forecast.balances == (
        Decimal("50000.00"),
        Decimal("98000.00"),
        Decimal("96750.00"),
    )


def test_weekly_cash_forecast_rejects_conflicting_cash_direction():
    with pytest.raises(ValueError, match="both Inflow and Outflow"):
        build_weekly_cash_forecast(
            [
                {
                    "actual_paid_date": date(2026, 1, 1),
                    "Inflow": "10",
                    "Outflow": "1",
                }
            ],
            date(2026, 1, 1),
            Decimal("100"),
        )


def test_financing_offers_compare_by_effective_annual_rate():
    assert periodic_rate_to_ear(Decimal("0.012")).quantize(
        Decimal("0.000001")
    ) == Decimal("0.153895")
    assert nominal_annual_rate_to_ear(Decimal("0.12")).quantize(
        Decimal("0.000001")
    ) == Decimal("0.126825")

    selected = select_lowest_ear_offer(
        [
            FinancingOffer("Monthly Fee Lender", Decimal("0.012"), "monthly_flat_fee"),
            FinancingOffer("Nominal 12% Lender", Decimal("0.12"), "nominal_annual"),
            FinancingOffer("Nominal 10% Lender", Decimal("0.10"), "nominal_annual"),
        ]
    )
    assert selected.lender == "Nominal 10% Lender"
