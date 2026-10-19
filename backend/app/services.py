"""
services.py: the business logic of the Qyze Ai treasurer.

Read this file top to bottom. It has five parts:

1. SETTINGS: dataclasses that hold the numbers and text you may want to change.
2. PAYMENT RULES: a list of checks every payment must pass, in order.
3. PAYMENT EXTRACTION: turns a chat message into structured payment fields.
4. AuditChain: an append-only list of events, each linked to the previous one by hash.
5. Treasurer: the main service. It uses the parts above and exposes
   payment and agent operations.

Every value that used to be hard-coded is a named field in a settings object.
Pass your own settings into Treasurer(...) to change behaviour, or pass
different values into a single method call. With no arguments, the defaults
reproduce the demo.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable
from sqlmodel import Session
from uuid import uuid4

from .models import (
    AgentResponse,
    AuditEvent,
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

    def append(self, event_type: str, payload: dict, business_id: str | None = None) -> AuditEvent:
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
            business_id=business_id,
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
        payment_rules: list[PaymentRule] | None = None,
        payment_extractor: Callable[[str], ExtractedPayment] = extract_payment,
        injection_patterns: list[str] | None = None,
        payment_keywords: tuple[str, ...] = DEFAULT_PAYMENT_KEYWORDS,
        default_mandate_id: str | None = None,
    ) -> None:
        """Every argument is optional. None means "use the default described above"."""
        self.audit = AuditChain()

        self.mandates: dict[str, Mandate] = mandates or {}

        # Money already paid today, per mandate. Starts empty.
        self.daily_spend: dict[str, Decimal] = {}

        self.payment_rules = payment_rules if payment_rules is not None else default_payment_rules()
        self.payment_extractor = payment_extractor
        self.injection_patterns = (
            injection_patterns if injection_patterns is not None else list(DEFAULT_INJECTION_PATTERNS)
        )
        self.payment_keywords = payment_keywords
        self.default_mandate_id = default_mandate_id

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
        event = self.audit.append(
            "payment.approved", request.model_dump(mode="json"), mandate.business_id
        )
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
        business_id = None
        if session is not None and request.mandate_id:
            mandate = session.get(Mandate, request.mandate_id)
            business_id = mandate.business_id if mandate else None
        event = self.audit.append(
            "payment.blocked",
            {"request": request.model_dump(mode="json"), "reason": reason},
            business_id,
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
            invoice.business_id,
        )
        session.add(invoice)
        session.add(event)
        session.commit()

    def pay_invoice(self, invoice: "APInvoice", session: Session) -> PaymentResult:
        if invoice.status != "approved":
            event = self.audit.append(
                "invoice.payment_blocked",
                {"invoice_id": invoice.id, "reason": "Invoice is not approved."},
                invoice.business_id,
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
                invoice.business_id,
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
                message="I can help with payments, mandates, invoices, and business finance requests.",
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
# Replacing the extractor with your own (for example an LLM-based one):
#     treasurer = Treasurer(payment_extractor=my_llm_extractor)