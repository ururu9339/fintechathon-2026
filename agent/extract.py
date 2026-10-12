import re
from decimal import Decimal


def extract_invoice(text: str) -> dict[str, str | Decimal | None]:
    """Extract the small, explicit invoice surface needed by the demo."""
    amount = re.search(r"(?:MYR|RM)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    invoice = re.search(r"\b(?:INV|INVOICE)[-\s#]?([A-Z0-9-]+)", text, re.IGNORECASE)
    return {
        "invoice_id": invoice.group(1) if invoice else None,
        "amount": Decimal(amount.group(1).replace(",", "")) if amount else None,
    }
