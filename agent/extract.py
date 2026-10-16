import base64
import io
import re
from decimal import Decimal, InvalidOperation

from PIL import Image

from backend.app.core.llm import get_openai_client
from backend.app.models import ExtractedInvoiceSchema, ExtractionResult

from .document_parser import extract_text_from_docx, parse_pdf, validate_upload_file

MAX_DOCUMENT_CHARS = 12_000


def reduce_document_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)

    compact: list[str] = []
    for line in lines:
        if not compact or compact[-1] != line:
            compact.append(line)

    text = "\n".join(compact)
    if len(text) <= MAX_DOCUMENT_CHARS:
        return text

    head_size = MAX_DOCUMENT_CHARS * 2 // 3
    tail_size = MAX_DOCUMENT_CHARS - head_size
    return text[:head_size] + "\n[document text truncated]\n" + text[-tail_size:]


def downscale_image(file_bytes: bytes) -> tuple[bytes, str]:
    with Image.open(io.BytesIO(file_bytes)) as image:
        image.thumbnail((640, 480), Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=80, optimize=True)
        return output.getvalue(), "image/jpeg"


def extract_invoice(text: str) -> dict[str, str | Decimal | None]:
    amount = re.search(r"(?:MYR|RM)\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
    invoice = re.search(r"\b(?:INV|INVOICE)[-\s#]?([A-Z0-9-]+)", text, re.IGNORECASE)
    return {
        "invoice_id": invoice.group(1) if invoice else None,
        "amount": Decimal(amount.group(1).replace(",", "")) if amount else None,
    }


def reconcile_totals(inv: ExtractedInvoiceSchema) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    try:
        subtotal = Decimal(inv.subtotal)
        tax = Decimal(inv.tax_amount)
        total = Decimal(inv.total_amount)
    except (InvalidOperation, ValueError):
        return False, ["Invalid non-numeric monetary format extracted."]

    if abs(subtotal + tax - total) > Decimal("0.05"):
        reasons.append("Subtotal plus tax does not equal total.")
    if inv.line_items:
        try:
            line_sum = sum((Decimal(item.total_amount) for item in inv.line_items), Decimal("0"))
        except (InvalidOperation, ValueError):
            reasons.append("A line item contains a non-numeric amount.")
        else:
            if abs(line_sum - total) > Decimal("0.05"):
                reasons.append("Line item sum does not equal total.")
    return not reasons, reasons


def llm_multimodal_extractor(filename: str, file_bytes: bytes) -> ExtractionResult:
    error = validate_upload_file(file_bytes, filename)
    if error:
        return ExtractionResult(status="failed", error_message=error)

    client = get_openai_client()
    if not client:
        return ExtractionResult(status="failed", error_message="OpenAI client is not configured.")

    ext = filename.lower().rsplit(".", 1)[-1]
    raw_text = ""
    content: list[dict] = []
    model = "gpt-4o-mini"
    if ext == "docx":
        raw_text = reduce_document_text(extract_text_from_docx(file_bytes))
        content.append({"type": "text", "text": raw_text})
    elif ext == "pdf":
        status, raw_text = parse_pdf(file_bytes)
        if status == "scanned_pdf_detected":
            return ExtractionResult(status="needs_review", error_message="Scanned PDF detected.")
        if status == "failed":
            return ExtractionResult(status="failed", error_message=raw_text)
        raw_text = reduce_document_text(raw_text)
        content.append({"type": "text", "text": raw_text})
    else:
        model = "gpt-4o"
        resized_bytes, mime = downscale_image(file_bytes)
        encoded = base64.b64encode(resized_bytes).decode()
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{encoded}",
                    "detail": "low",
                },
            }
        )

    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": "Extract invoice fields without guessing missing values."},
                {"role": "user", "content": content},
            ],
            response_format=ExtractedInvoiceSchema,
            max_tokens=1500,
        )
        invoice = response.choices[0].message.parsed
    except Exception as exc:
        return ExtractionResult(status="failed", error_message=f"OpenAI extraction failed: {exc}")
    if invoice is None:
        return ExtractionResult(status="failed", error_message="OpenAI returned no invoice.")

    reconciled, reasons = reconcile_totals(invoice)
    if not invoice.source_snippet:
        reasons.append("Source snippet is missing.")
    elif raw_text and invoice.source_snippet.lower() not in raw_text.lower():
        reasons.append("Source snippet could not be verified.")
    elif not raw_text:
        reasons.append("Image source snippet requires OCR verification.")
    return ExtractionResult(
        status="ok" if reconciled and not reasons else "needs_review",
        invoice=invoice,
        reconciliation_ok=reconciled and not reasons,
        review_reasons=reasons,
    )
