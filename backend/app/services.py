import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from .models import (
    AgentResponse,
    AuditEvent,
    CashFlowPoint,
    FinancingRecommendation,
    Mandate,
    PaymentRequest,
    PaymentResult,
)


class AuditChain:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event_type: str, payload: dict) -> AuditEvent:
        previous_hash = self.events[-1].event_hash if self.events else "GENESIS"
        created_at = datetime.now(timezone.utc)
        body = {
            "event_type": event_type,
            "payload": payload,
            "created_at": created_at.isoformat(),
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(
            (previous_hash + json.dumps(body, sort_keys=True, default=str)).encode()
        ).hexdigest()
        event = AuditEvent(
            event_type=event_type,
            payload=payload,
            created_at=created_at,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self.events.append(event)
        return event


class Treasurer:
    def __init__(self) -> None:
        self.audit = AuditChain()
        self.mandates = {
            "mandate-demo": Mandate(
                id="mandate-demo",
                daily_limit=Decimal("5000"),
                transaction_limit=Decimal("2500"),
                allowed_suppliers=["Acme Supplies", "MyInvois Demo Supplier"],
                purpose="supplier invoice",
                expires_at=date.today() + timedelta(days=30),
            )
        }
        self.daily_spend = Decimal("0")

    def forecast(self) -> list[CashFlowPoint]:
        balance = Decimal("18000")
        today = date.today()
        points = []
        for week in range(1, 14):
            inflows = Decimal("4200") if week % 3 else Decimal("1800")
            outflows = Decimal("3600") + (Decimal("5000") if week in (4, 9) else Decimal("0"))
            closing = balance + inflows - outflows
            points.append(
                CashFlowPoint(
                    week=week,
                    date=today + timedelta(days=7 * (week - 1)),
                    opening_balance=balance,
                    inflows=inflows,
                    outflows=outflows,
                    closing_balance=closing,
                    lower_bound=closing - Decimal("1200"),
                    upper_bound=closing + Decimal("1200"),
                )
            )
            balance = closing
        return points

    def pay(self, request: PaymentRequest) -> PaymentResult:
        mandate = self.mandates.get(request.mandate_id)
        if not mandate:
            return self._blocked(request, "Mandate not found")
        if date.today() > mandate.expires_at:
            return self._blocked(request, "Mandate has expired")
        if request.supplier not in mandate.allowed_suppliers:
            return self._blocked(request, "Supplier is not on the mandate allowlist")
        if request.amount > mandate.transaction_limit:
            return self._blocked(request, "Amount exceeds the per-transaction limit")
        if self.daily_spend + request.amount > mandate.daily_limit:
            return self._blocked(request, "Amount exceeds the daily limit")
        if request.purpose.lower() != mandate.purpose.lower():
            return self._blocked(request, "Payment purpose does not match the mandate")

        self.daily_spend += request.amount
        event = self.audit.append("payment.approved", request.model_dump(mode="json"))
        return PaymentResult(
            status="approved",
            reason="Payment approved by owner mandate",
            payment_id=f"pay_{uuid4().hex[:10]}",
            audit_hash=event.event_hash,
        )

    def _blocked(self, request: PaymentRequest, reason: str) -> PaymentResult:
        event = self.audit.append(
            "payment.blocked", {"request": request.model_dump(mode="json"), "reason": reason}
        )
        return PaymentResult(status="blocked", reason=reason, audit_hash=event.event_hash)

    def financing(self) -> list[FinancingRecommendation]:
        lowest = min(self.forecast(), key=lambda point: point.closing_balance)
        if lowest.closing_balance >= 0:
            return []
        amount = abs(lowest.closing_balance) + Decimal("2500")
        return [
            FinancingRecommendation(
                provider="CGC Demo",
                product="SME working capital facility",
                amount=amount,
                effective_apr=Decimal("8.90"),
                reason=f"Projected week {lowest.week} cash gap of {abs(lowest.closing_balance)} MYR",
            )
        ]

    def agent(self, message: str) -> AgentResponse:
        injection = re.search(
            r"ignore (all|previous|prior)|reveal (system|hidden) prompt|bypass (the )?mandate",
            message,
            flags=re.IGNORECASE,
        )
        if injection:
            self.audit.append("agent.injection_blocked", {"message": message})
            return AgentResponse(
                status="blocked",
                message="I blocked that instruction because it attempts to override the treasurer's safety rules.",
            )
        if "pay" in message.lower() or "invoice" in message.lower():
            return AgentResponse(
                status="advisory",
                message="I can prepare the invoice payment, but an owner mandate must approve the exact supplier, amount, and purpose.",
                action="request_payment_details",
            )
        return AgentResponse(
            status="advisory",
            message="I can explain your 13-week forecast, envelopes, mandates, or financing options.",
        )

