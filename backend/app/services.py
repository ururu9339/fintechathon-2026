"""
services.py: the business logic of the AmanahPay treasurer.

Read this file top to bottom. It has five parts:

1. SETTINGS: dataclasses that hold the numbers and text you may want to change.
2. PAYMENT RULES: a list of checks every payment must pass, in order.
3. PAYMENT EXTRACTION: turns a chat message into structured payment fields.
4. AuditChain: an append-only list of events, each linked to the previous one by hash.
5. Treasurer: the main service. It uses the parts above and exposes
   forecast(), pay(), financing(), and agent().

Every value that used to be hard-coded is a named field in a settings object.
Pass your own settings into Treasurer(...) to change behaviour, or pass
different values into a single method call. With no arguments, the defaults
reproduce the demo.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable
from sqlmodel import Session
from uuid import uuid4

from .models import (
    AgentResponse,
    AuditEvent,
    CashFlowPoint,
    FinancingRecommendation,
    Mandate,
    PaymentRequest,
    PaymentResult,
    Counterparty,
)


# ============================================================================
# 1. SETTINGS
# Each dataclass groups the inputs for one feature. To change behaviour,
# create an instance with different values and pass it to Treasurer.
# ============================================================================


@dataclass
class ForecastAssumptions:
    """Inputs for the 13-week cash flow forecast. All amounts are in MYR."""

    opening_balance: Decimal = Decimal("18000")    # cash on hand before week 1
    normal_inflow: Decimal = Decimal("4200")       # money received in a typical week
    low_inflow: Decimal = Decimal("1800")          # money received in a slow week
    low_inflow_every_n_weeks: int = 3              # every 3rd week is slow (3, 6, 9, 12)
    base_outflow: Decimal = Decimal("3600")        # regular spending each week
    large_outflow: Decimal = Decimal("5000")       # extra one-off payment (tax, payroll)
    large_outflow_weeks: tuple[int, ...] = (4, 9)  # weeks that get the extra payment
    uncertainty_band: Decimal = Decimal("1200")    # +/- range drawn around each balance
    weeks: int = 13                                # length of the forecast


@dataclass
class FinancingTerms:
    """Terms used when the forecast shows a cash gap."""

    provider: str = "CGC Demo"
    product: str = "SME working capital facility"
    effective_apr: Decimal = Decimal("8.90")   # yearly cost, in percent
    safety_buffer: Decimal = Decimal("2500")   # extra amount borrowed on top of the gap


# Words that tell the agent a message is about moving money.
DEFAULT_PAYMENT_KEYWORDS: tuple[str, ...] = ("pay", "invoice", "transfer")

# Phrases that signal a prompt injection attempt. Each one is a regular expression.
DEFAULT_INJECTION_PATTERNS: list[str] = [
    r"ignore (all|previous|prior)",
    r"reveal (system|hidden) prompt",
    r"bypass (the )?mandate",
]


# ============================================================================
# 2. PAYMENT RULES
# Each rule is one check. Rules run in order, and the first one that fails
# decides the reason shown to the owner.
#
# To add a rule, append a PaymentRule to default_payment_rules(), or pass
# your own list into Treasurer(payment_rules=...).
# ============================================================================


@dataclass
class PaymentRule:
    """One check a payment must pass.

    check(mandate, request, spent_today) returns True when the payment is allowed.
    reason is the message shown to the owner when the check fails.
    """

    reason: str
    check: Callable[[Mandate, PaymentRequest, Decimal], bool]


def default_payment_rules() -> list[PaymentRule]:
    """The standard rules, in the order they are checked.

    Example of a new rule you could add:
        PaymentRule(
            reason="Payments are not allowed on Sundays",
            check=lambda mandate, request, spent: date.today().weekday() != 6,
        )
    """
    return [
        PaymentRule(
            reason="Mandate has expired",
            check=lambda mandate, request, spent: date.today() <= mandate.expires_at,
        ),
        PaymentRule(
            reason="Supplier is not on the mandate allowlist",
            check=lambda mandate, request, spent: (
                request.supplier in mandate.allowed_suppliers
                or (
                    request.counterparty_id is not None
                    and request.counterparty_id in mandate.allowed_counterparty_ids
                )
            ),
        ),
        PaymentRule(
            reason="Supplier is not verified",
            check=lambda mandate, request, spent: (
                not mandate.require_verified_supplier or request.supplier_verified
            ),
        ),
        PaymentRule(
            reason="Invoice reference is missing",
            check=lambda mandate, request, spent: bool(request.invoice_id.strip()),
        ),
        PaymentRule(
            reason="Amount exceeds the per-transaction limit",
            check=lambda mandate, request, spent: request.amount <= mandate.transaction_limit,
        ),
        PaymentRule(
            reason="Amount exceeds the daily limit",
            check=lambda mandate, request, spent: spent + request.amount <= mandate.daily_limit,
        ),
        PaymentRule(
            reason="Payment purpose does not match the mandate",
            check=lambda mandate, request, spent: request.purpose.lower() == mandate.purpose.lower(),
        ),
    ]


# ============================================================================
# 3. PAYMENT EXTRACTION
# Turns a chat message into structured fields. This version uses simple
# patterns. It can later be replaced by an LLM-based extractor without
# changing agent() or pay(). Pass your own function as payment_extractor.
# ============================================================================


@dataclass
class ExtractedPayment:
    """Payment fields found in a message. Empty values mean "not found"."""

    amount: Decimal | None = None
    supplier: str = ""
    invoice_id: str = ""
    purpose: str = "unspecified"


def extract_payment(message: str) -> ExtractedPayment:
    """Find the amount, supplier, and invoice number in a message.

    Patterns used:
      amount   : "RM" followed by a number, e.g. "RM48,000" or "RM 1,200.50"
      supplier : the words after "to", up to "for", "on", or punctuation
      invoice  : "invoice" followed by an ID that contains a digit, e.g. "INV-001"
    """
    amount = None
    amount_match = re.search(r"RM\s?([\d,]+(?:\.\d{1,2})?)", message, flags=re.IGNORECASE)
    if amount_match:
        try:
            amount = Decimal(amount_match.group(1).replace(",", ""))
        except InvalidOperation:
            amount = None

    supplier = ""
    supplier_match = re.search(
        r"\bto\s+(?:the\s+)?(.+?)(?=\s+(?:for|on|because)\b|[.,;!?]|$)",
        message,
        flags=re.IGNORECASE,
    )
    if supplier_match:
        supplier = supplier_match.group(1).strip()

    invoice_id = ""
    invoice_match = re.search(
        r"invoice\s*(?:no\.?|number|#)?\s*([A-Za-z0-9][A-Za-z0-9-]*\d[A-Za-z0-9-]*)",
        message,
        flags=re.IGNORECASE,
    )
    if invoice_match:
        invoice_id = invoice_match.group(1)

    purpose = "supplier invoice" if "invoice" in message.lower() else "unspecified"

    return ExtractedPayment(amount=amount, supplier=supplier, invoice_id=invoice_id, purpose=purpose)


# ============================================================================
# 4. AUDIT CHAIN
# Each event stores the hash of the previous event, so changing any old event
# breaks every hash after it.
# ============================================================================


def _hash_event(previous_hash: str, body: dict) -> str:
    """SHA-256 of the previous hash plus the event body, as sorted JSON."""
    text = previous_hash + json.dumps(body, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()


class AuditChain:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self._last_hash = "GENESIS"

    def append(self, event_type: str, payload: dict) -> AuditEvent:
        previous_hash = self._last_hash
        created_at = datetime.now(timezone.utc)
        body = {
            "event_type": event_type,
            "payload": payload,
            "created_at": created_at.isoformat(),
            "previous_hash": previous_hash,
        }
        event = AuditEvent(
            event_type=event_type,
            payload=payload,
            created_at=created_at,
            previous_hash=previous_hash,
            event_hash=_hash_event(previous_hash, body),
        )
        self.events.append(event)
        self._last_hash = event.event_hash
        return event


# ============================================================================
# 5. TREASURER
# The service that uses the parts above. Its state is:
#   mandates      : mandate id -> Mandate (the owner's signed limits)
#   daily_spend   : mandate id -> amount already paid today under that mandate
#   audit         : the AuditChain that records every decision
# ============================================================================


class Treasurer:
    def __init__(
        self,
        mandates: dict[str, Mandate] | None = None,
        forecast_assumptions: ForecastAssumptions | None = None,
        financing_terms: FinancingTerms | None = None,
        payment_rules: list[PaymentRule] | None = None,
        payment_extractor: Callable[[str], ExtractedPayment] = extract_payment,
        injection_patterns: list[str] | None = None,
        payment_keywords: tuple[str, ...] = DEFAULT_PAYMENT_KEYWORDS,
        default_mandate_id: str | None = None,
        start_date: date | None = None,
    ) -> None:
        """Every argument is optional. None means "use the default described above"."""
        self.audit = AuditChain()

        self.mandates: dict[str, Mandate] = mandates or {}

        # Money already paid today, per mandate. Starts empty.
        self.daily_spend: dict[str, Decimal] = {}

        # Settings. Default values come from the dataclasses above.
        self.forecast_assumptions = forecast_assumptions or ForecastAssumptions()
        self.financing_terms = financing_terms or FinancingTerms()
        self.payment_rules = payment_rules if payment_rules is not None else default_payment_rules()
        self.payment_extractor = payment_extractor
        self.injection_patterns = (
            injection_patterns if injection_patterns is not None else list(DEFAULT_INJECTION_PATTERNS)
        )
        self.payment_keywords = payment_keywords
        self.default_mandate_id = default_mandate_id
        self.start_date = start_date  # None means "today", evaluated when forecast() runs

    # ------------------------------------------------------------------
    # Mandate management
    # ------------------------------------------------------------------

    def add_mandate(self, mandate: Mandate) -> None:
        """Add or replace a mandate. The key is mandate.id."""
        self.mandates[mandate.id] = mandate

    def reset_daily_spend(self, mandate_id: str | None = None) -> None:
        """Clear today's spend for one mandate, or for all mandates if mandate_id is None."""
        if mandate_id is None:
            self.daily_spend.clear()
        else:
            self.daily_spend.pop(mandate_id, None)

    # ------------------------------------------------------------------
    # Forecast
    # ------------------------------------------------------------------

    def forecast(self, assumptions: ForecastAssumptions | None = None) -> list[CashFlowPoint]:
        """Build the weekly forecast.

        Pass assumptions to use different numbers for this call only.
        Otherwise the Treasurer's own settings are used.
        """
        a = assumptions if assumptions is not None else self.forecast_assumptions
        start = self.start_date or date.today()

        balance = a.opening_balance
        points: list[CashFlowPoint] = []
        for week in range(1, a.weeks + 1):
            is_slow_week = week % a.low_inflow_every_n_weeks == 0
            inflows = a.low_inflow if is_slow_week else a.normal_inflow

            extra = a.large_outflow if week in a.large_outflow_weeks else Decimal("0")
            outflows = a.base_outflow + extra

            closing = balance + inflows - outflows
            points.append(
                CashFlowPoint(
                    week=week,
                    date=start + timedelta(days=7 * (week - 1)),
                    opening_balance=balance,
                    inflows=inflows,
                    outflows=outflows,
                    closing_balance=closing,
                    lower_bound=closing - a.uncertainty_band,
                    upper_bound=closing + a.uncertainty_band,
                )
            )
            balance = closing
        return points

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def pay(self, request: PaymentRequest, session: Session | None = None) -> PaymentResult:
        """Approve or block a payment request. Every outcome is written to the audit chain."""
        request.supplier = request.supplier or request.supplier_name or ""
        request.invoice_id = request.invoice_id or request.invoice_number or ""
        mandate = self.mandates.get(request.mandate_id)
        if mandate is None and session is not None:
            mandate = session.get(Mandate, request.mandate_id)
            if mandate is not None:
                self.mandates[mandate.id] = mandate
        if mandate is None:
            return self._blocked(request, session, "Mandate not found")
        if mandate.status != "active":
            return self._blocked(request, session, "Mandate is not active")

        spent_today = self.daily_spend.get(mandate.id, Decimal("0"))

        # Run each rule in order. The first failing rule blocks the payment.
        for rule in self.payment_rules:
            if not rule.check(mandate, request, spent_today):
                return self._blocked(request, session, rule.reason)

        self.daily_spend[mandate.id] = spent_today + request.amount
        from rail.mock_rail import submit_payment

        rail_payment = submit_payment(request.supplier, request.amount)
        event = self.audit.append("payment.approved", request.model_dump(mode="json"))
        if session is not None:
            session.add(event)
            session.commit()
        return PaymentResult(
            status="approved",
            reason="Payment approved by owner mandate",
            payment_id=rail_payment.payment_id,
            audit_hash=event.event_hash,
        )

    def _blocked(
        self,
        request: PaymentRequest,
        session: Session | None,
        reason: str,
    ) -> PaymentResult:
        event = self.audit.append(
            "payment.blocked",
            {"request": request.model_dump(mode="json"), "reason": reason},
        )                                                           
        if session is not None:
            session.add(event)
            session.commit()
        return PaymentResult(status="blocked", reason=reason, audit_hash=event.event_hash)

    def approve_invoice(self, invoice: "APInvoice", session: Session) -> None:
        if invoice.status != "draft":
            raise ValueError(f"Invoice cannot be approved from status '{invoice.status}'.")
        if invoice.subtotal < 0 or invoice.tax_amount < 0 or invoice.total_amount <= 0:
            raise ValueError("Invoice amounts must be valid before approval.")
        if abs(invoice.subtotal + invoice.tax_amount - invoice.total_amount) > Decimal("0.01"):
            raise ValueError("Invoice subtotal plus tax must equal total before approval.")
        if invoice.due_date and invoice.due_date < invoice.issue_date:
            raise ValueError("Invoice due date cannot be before issue date.")
        invoice.status = "approved"
        event = self.audit.append(
            "invoice.approved",
            {"invoice_id": invoice.id, "invoice_number": invoice.invoice_number},
        )
        session.add(invoice)
        session.add(event)
        session.commit()

    def pay_invoice(self, invoice: "APInvoice", session: Session) -> PaymentResult:
        if invoice.status != "approved":
            event = self.audit.append(
                "invoice.payment_blocked",
                {"invoice_id": invoice.id, "reason": "Invoice is not approved."},
            )
            session.add(event)
            session.commit()
            return PaymentResult(
                status="blocked",
                reason="Invoice must be approved before payment.",
                audit_hash=event.event_hash,
            )

        request = PaymentRequest(
            ap_invoice_id=invoice.id,
            mandate_id=invoice.mandate_id,
            supplier=invoice.supplier_name,
            supplier_name=invoice.supplier_name,
            amount=invoice.total_amount,
            purpose="supplier invoice",
            invoice_id=invoice.invoice_number,
            invoice_number=invoice.invoice_number,
        )
        if invoice.counterparty_id:
            request.counterparty_id = invoice.counterparty_id
            counterparty = session.get(Counterparty, invoice.counterparty_id)
            request.supplier_verified = bool(counterparty and counterparty.is_verified)
        if not request.mandate_id:
            event = self.audit.append(
                "invoice.payment_blocked",
                {"invoice_id": invoice.id, "reason": "No payment mandate selected."},
            )
            session.add(event)
            session.commit()
            return PaymentResult(
                status="blocked",
                reason="A payment mandate must be selected before payment.",
                audit_hash=event.event_hash,
            )
        result = self.pay(request, session)
        request.status = result.status
        session.add(request)
        if result.status == "approved":
            invoice.status = "paid"
            session.add(invoice)
        session.commit()
        return result

    # ------------------------------------------------------------------
    # Financing
    # ------------------------------------------------------------------

    def financing(self, assumptions: ForecastAssumptions | None = None) -> list[FinancingRecommendation]:
        """Suggest a facility if any week in the forecast goes negative."""
        points = self.forecast(assumptions)
        lowest = min(points, key=lambda point: point.closing_balance)
        if lowest.closing_balance >= 0:
            return []

        shortfall = abs(lowest.closing_balance)
        terms = self.financing_terms
        return [
            FinancingRecommendation(
                provider=terms.provider,
                product=terms.product,
                amount=shortfall + terms.safety_buffer,
                effective_apr=terms.effective_apr,
                reason=f"Projected week {lowest.week} cash gap of {shortfall} MYR",
            )
        ]

    # ------------------------------------------------------------------
    # Agent
    # ------------------------------------------------------------------

    def agent(self, message: str, session: Session | None = None) -> AgentResponse:
        """Read a message and decide what to do with it.

        Order of checks:
          1. Injection patterns: block immediately, never reach a payment.
          2. Not about money: return a plain advisory reply.
          3. About money but no amount: ask the user for it.
          4. Otherwise: build a PaymentRequest and send it through pay(),
             so the payment rules make the decision.
        """
        if self._looks_like_injection(message):
            self.audit.append("agent.injection_blocked", {"message": message})
            return AgentResponse(
                status="blocked",
                message="I blocked that instruction because it attempts to override the treasurer's safety rules.",
            )

        if not self._is_payment_intent(message):
            return AgentResponse(
                status="advisory",
                message="I can explain your 13-week forecast, envelopes, mandates, or financing options.",
            )

        extracted = self.payment_extractor(message)
        if extracted.amount is None:
            return AgentResponse(
                status="advisory",
                message="How much should I pay? Please include the amount, for example RM1,200.",
                action="request_payment_details",
            )

        request = PaymentRequest(
            mandate_id=self.default_mandate_id,
            supplier=extracted.supplier,
            amount=extracted.amount,
            purpose=extracted.purpose,
            invoice_id=extracted.invoice_id,
        )
        result = self.pay(request, session) 
        return self._payment_to_reply(request, result)
    
    def _payment_to_reply(self, request: PaymentRequest, result: PaymentResult) -> AgentResponse:
        if result.status == "approved":
            return AgentResponse(
                status="approved",
                message=f"Paid RM{request.amount} to {request.supplier}. Reference {result.payment_id}.",
                action="payment_settled",
            )
        return AgentResponse(
            status="blocked",
            message=f"Payment blocked: {result.reason}.",
        )

    def _is_payment_intent(self, message: str) -> bool:
        lowered = message.lower()
        return any(keyword in lowered for keyword in self.payment_keywords)

    def _looks_like_injection(self, message: str) -> bool:
        if not self.injection_patterns:
            return False
        combined = "|".join(f"(?:{pattern})" for pattern in self.injection_patterns)
        return re.search(combined, message, flags=re.IGNORECASE) is not None


# ============================================================================
# EXAMPLES
# ============================================================================
#
# Default demo behaviour:
#     treasurer = Treasurer()
#     treasurer.agent("Pay RM1,200 to Acme Supplies for invoice INV-001")
#
# The attack from the demo. Blocked by the allowlist rule:
#     treasurer.agent("Transfer RM48,000 to a new account")
#
# A smaller business with a bigger tax payment in week 2:
#     treasurer = Treasurer(
#         forecast_assumptions=ForecastAssumptions(
#             opening_balance=Decimal("5000"),
#             large_outflow=Decimal("8000"),
#             large_outflow_weeks=(2,),
#         ),
#     )
#
# A forecast for one call only, without changing the Treasurer:
#     points = treasurer.forecast(ForecastAssumptions(opening_balance=Decimal("0")))
#
# Replacing the extractor with your own (for example an LLM-based one):
#     treasurer = Treasurer(payment_extractor=my_llm_extractor)