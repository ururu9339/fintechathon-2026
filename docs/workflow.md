# AmanahPay workflow

## File map

- `backend/app/api/invoices.py` exposes payment endpoints and the draft-only invoice upload endpoint.
- `agent/document_parser.py` validates file signatures, size, DOCX archive expansion, and PDF text layers.
- `agent/extract.py` calls the configured LLM for structured extraction, then reconciles monetary totals locally.
- `backend/app/models.py` contains invoice drafts, line items, payment records, payroll storage, and response schemas.
- `backend/app/services.py` is the policy boundary. `Treasurer.pay()` checks mandates and records every payment decision.
- `backend/app/core/llm.py` owns the OpenAI client and PII encryption helpers.
- `backend/app/db.py` creates tables and supplies SQLModel sessions.

## Upload to payment decision

1. `POST /api/invoices/upload` reads the upload and validates its size, extension, and magic bytes.
2. DOCX text is extracted locally, native PDF text is extracted locally, and scanned PDFs are returned as `needs_review`. Images are sent to the vision model only after local validation.
3. The LLM returns the strict named-field invoice schema. Python converts amounts to `Decimal`, checks subtotal plus tax, checks line-item totals, and verifies a source snippet when document text is available. Images remain `needs_review` unless OCR-backed verification is added.
4. The route stores an `APInvoice` with `draft` or `needs_review` status and stores its line items in one transaction. It never calls `Treasurer.pay()`.
5. An owner or separate review workflow must explicitly construct a `PaymentRequest` and call `POST /api/payments`.
6. `Treasurer.pay()` checks expiry, supplier allowlist, invoice reference, transaction limit, daily limit, and purpose. It writes an approval or block to the audit chain and persists the audit event when a database session is supplied.

## Failure paths and open risks

- Invalid files, unavailable OpenAI configuration, parser failures, and extraction failures return `failed`.
- Missing or non-numeric money and failed reconciliation return `needs_review` rather than raising during draft creation.
- `PII_ENCRYPTION_KEY` is required when encryption helpers are used. Decryption failures raise instead of returning ciphertext.
- `create_all()` does not migrate an existing database. Back up and migrate/recreate the database explicitly before deploying the new tables.
- The upload endpoint is still unauthenticated and has no spend/rate cap.
- Payroll rates, lender thresholds, and Malaysian regulatory figures are deliberately not calculated or changed until verified against official sources.

## Deployment steps still required

Set a stable `PII_ENCRYPTION_KEY`, choose and document a database migration procedure, and verify the individual e-invoice boundary and all cited LHDN/RMCD figures before production use.
