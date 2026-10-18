# AmanahPay workflow

## File map

- `backend/app/api/invoices.py` exposes payment endpoints and the draft-only invoice upload endpoint.
- `backend/app/api/accounting.py` exposes sales, receipts, ledger, and focused payroll endpoints.
- `backend/app/api/business.py` owns business profiles and the source records required for future metrics.
- `agent/document_parser.py` validates file signatures, size, DOCX archive expansion, and PDF text layers.
- `agent/extract.py` calls the configured LLM for structured extraction, then reconciles monetary totals locally.
- `backend/app/models.py` contains invoice drafts, line items, payment records, payroll storage, and response schemas.
- `backend/app/services.py` is the policy boundary. `Treasurer.pay()` checks mandates and records every payment decision.
- `backend/app/core/llm.py` owns the OpenAI client and PII encryption helpers.
- `backend/app/db.py` creates tables and supplies SQLModel sessions.

## Upload to payment decision

1. `POST /api/invoices/upload?business_id=...` reads the upload and validates its size, extension, and magic bytes.
2. DOCX text is extracted locally, native PDF text is extracted locally, and scanned PDFs are returned as `needs_review`. Images use local OCR first and fall back to a downscaled vision request when OCR is insufficient.
3. The LLM returns the strict named-field invoice schema. Python converts amounts to `Decimal`, checks subtotal plus tax, checks line-item totals, and verifies a source snippet against extracted document text or local OCR.
4. The route stores an `APInvoice` with `draft` or `needs_review` status and stores its line items in one transaction. It never calls `Treasurer.pay()`. The response includes the saved `invoice_id`.
5. The owner reviews the record with `GET /api/invoices/{invoice_id}`. Records in `needs_review` must be corrected with `PUT /api/invoices/{invoice_id}` before `POST /api/invoices/{invoice_id}/approve` is accepted. Approval is audited.
6. `POST /api/invoices/{invoice_id}/pay` creates a linked `PaymentRequest`, requires invoice status `approved`, copies the supplier, invoice number, mandate, and total from the invoice, then calls `Treasurer.pay()`.
7. `Treasurer.pay()` checks expiry, supplier allowlist, invoice reference, transaction limit, daily limit, and purpose. It writes an approval or block to the audit chain. An approved invoice becomes `paid`.

## Accounting expansion roadmap

The current implementation is accounts-payable focused. The next bounded modules should use the same policy and audit boundary:

- `SalesInvoice` and customer receipts for income, with issued, partially paid, paid, void, and overdue states.
- A double-entry ledger with immutable journal entries connecting sales, purchases, payroll, bank movements, tax, and owner transactions.
- A focused payroll module for employee records, salary runs, statutory deductions, employer contributions, and payment batches; it is not intended to become a general HR system.
- Reconciliation and analyst reports for cash flow, profit and loss, receivables, payables, payroll liabilities, tax exposure, and exceptions.

These should be implemented as separate modules with explicit source records and deterministic calculations. LLM extraction may create drafts, but it must not post ledger entries or initiate payments without human approval and policy checks.

## Accounting module relations

```text
BusinessProfile ──< Counterparty ──< SalesInvoice
       │                         └──< APInvoice
       ├──< OwnershipRecord
       ├──< LoanRequest
       ├──< CashBalance
       └──< StatutoryRemittance

SalesInvoice ──< SalesInvoiceLineItem
     │
     └── receipts update amount_received and status

APInvoice ──< APInvoiceLineItem
     │
     └── approved ──> PaymentRequest ──> Treasurer mandate checks

JournalEntry ──< JournalLine ──> LedgerAccount
     │
     └── source_type/source_id points to the originating sale, purchase, payroll, or receipt

Employee ──> PayrollRun
              │
              └── summary totals are posted only after a future payroll approval step
```

### Sales and receivables

Create the root business record first with `POST /api/businesses`. Ownership, counterparties, loan requests, cash balances, and statutory remittances are then recorded under `/api/businesses/{business_id}/...`. Invoice, employee, payroll, credit, journal, ledger, and report workflows require the business ID, preventing cross-business aggregation.

Sales can be entered either as a form with `POST /api/accounting/sales/invoices` or uploaded with `POST /api/accounting/sales/invoices/upload?business_id=...`. The upload reuses the same local parser/OCR/LLM extraction path as expenses, then stores a `draft` or `needs_review` sales record. `needs_review` sales records must be corrected with `PUT /api/accounting/sales/invoices/{id}` before issue. `POST /api/accounting/sales/invoices/{id}/issue` makes it receivable. Receipts are recorded with `POST /api/accounting/sales/invoices/{id}/receipts`; the invoice becomes `partially_paid` or `paid` without allowing over-collection.

Expenses can be entered either as a form with `POST /api/invoices` or uploaded with `POST /api/invoices/upload`. Form submissions validate subtotal plus tax before saving a draft. Uploaded submissions remain subject to extraction and review.

### Double-entry ledger

Ledger accounts are created with `POST /api/accounting/ledger/accounts` using a business ID in the body. A journal is posted with `POST /api/accounting/ledger/journals`. The backend rejects negative lines, empty journals, unknown/inactive accounts, and unbalanced debit/credit totals. Every journal identifies its source record so reports can trace amounts back to an invoice, payment, receipt, or payroll run.

### Focused payroll

Employees are created with `POST /api/accounting/payroll/employees` and a business ID. `DELETE /api/accounting/payroll/employees/{id}` deactivates an employee instead of deleting historical data. An inactive employee can be restored with `POST /api/accounting/payroll/employees/{id}/reactivate`, and their name or gross salary can be changed with `PATCH /api/accounting/payroll/employees/{id}`. Salary changes affect future payroll runs only; existing payroll records remain unchanged. `POST /api/accounting/payroll/runs?business_id=...&payroll_month=YYYY-MM-DD` creates a draft payroll summary from active employees. The current MVP treats gross salary as net and employer cost because statutory rates are not yet verified; no remittance or payment is initiated. EPF, SOCSO, EIS, PCB, and HRDF calculations require verified rate tables and a separate approval step.

### Credit facilities

Credit facilities are created with `POST /api/accounting/credit/facilities` and a business ID, and start as `pending`. They can become `active` with `POST /api/accounting/credit/facilities/{id}/approve?approved_amount=...`, become `denied` with `/deny`, and track repayments with `/payments`. Approval sets the approved and outstanding amounts; repayments reduce the outstanding balance and set the status to `paid_off` at zero. The model also stores lender, facility type, term, monthly payment, and next payment date for future financing recommendations and cash-flow analysis.

Credit status values currently include `pending`, `active`, `denied`, and `paid_off`; future delinquency handling can add `overdue`, `defaulted`, or `suspended` with scheduled-payment and arrears rules.

### Analyst/reporting boundary

`GET /api/accounting/reports/summary?business_id=...` provides a deterministic MVP summary of revenue, receipts, receivables, paid purchases, payables, payroll cost, and operating result. It filters by business and excludes unrelated rows. The source records and journal lines are the basis for future period-filtered cash-flow, profit-and-loss, payroll-liability, tax, and exception reports. Reports should read posted source records and balanced journals; they should not infer financial facts from LLM text.

## Failure paths and open risks

- Invalid files, unavailable OpenAI configuration, parser failures, and extraction failures return `failed`.
- Missing or non-numeric money and failed reconciliation return `needs_review` rather than raising during draft creation.
- `PII_ENCRYPTION_KEY` is required when encryption helpers are used. Decryption failures raise instead of returning ciphertext.
- Startup creates new tables and applies only the additive business-link and review/e-invoice columns needed by this foundation. A versioned migration tool is still required before production deployment.
- The upload endpoint is still unauthenticated and has no spend/rate cap.
- Payroll rates, lender thresholds, and Malaysian regulatory figures are deliberately not calculated or changed until verified against official sources.

## Deployment steps still required

Set a stable `PII_ENCRYPTION_KEY`, choose and document a database migration procedure, and verify the individual e-invoice boundary and all cited LHDN/RMCD figures before production use.
