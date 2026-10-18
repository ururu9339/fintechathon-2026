# AmanahPay workflow

## File map

- `backend/app/api/invoices.py` exposes payment endpoints and the draft-only invoice upload endpoint.
- `backend/app/api/accounting.py` exposes sales, receipts, ledger, and focused payroll endpoints.
- `backend/app/api/business.py` owns business profiles and the source records required for future metrics.
- `backend/app/api/mandates.py` manages explicit payment authorization policies; mandates are not business metrics.
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
     └── approved + selected mandate ──> PaymentRequest ──> Treasurer mandate checks

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

### Payment mandates

A mandate is an owner-defined authorization policy for money movement. It answers:

- which business the policy belongs to;
- which suppliers may be paid;
- the maximum amount per transaction;
- the maximum amount per day;
- the permitted payment purpose; and
- when the authorization expires;
- whether automatic payment is enabled; and
- whether the supplier must already be verified.

Mandates do not validate extracted data or create accounting metrics. They are reusable payment permissions, not a new mandate per invoice. The normal manual sequence is:

1. An invoice is collected as `draft` or `needs_review`.
2. The owner corrects review issues and approves the invoice.
3. The owner selects an existing active mandate on the expense invoice; the same mandate can authorize many matching supplier payments until it expires or is revoked.
4. Payment runs the mandate checks and writes an audit event.

Provider systems can submit structured bills to `POST /api/businesses/{business_id}/invoice-intake/webhook`. The payload includes a provider event ID and source invoice ID. The endpoint validates amounts and dates, links the bill to an existing supplier counterparty by business, and stores a provider-originated invoice. Repeated delivery of either identifier returns the existing invoice instead of creating a duplicate.

An active mandate with `auto_pay=true` can match a provider invoice by allowed supplier name or counterparty ID, transaction limit, and optional verified-supplier requirement. A matching invoice is approved and submitted through the mock payment rail; unmatched, unverified, expired, revoked, or over-limit invoices remain `needs_review` with an explanation. Automatic provider intake currently has no external signature verification and should be protected by authenticated provider credentials before production use.

Mandates are created under `POST /api/businesses/{business_id}/mandates`, listed with `GET` on the same path, and revoked with `POST /api/businesses/{business_id}/mandates/{mandate_id}/revoke`. There is no automatic `mandate-demo`; a payment without a selected real mandate is blocked. Revoked and expired mandates cannot authorize payments.

### Analyst/reporting boundary

`GET /api/accounting/reports/summary?business_id=...` provides a deterministic MVP summary of revenue, receipts, receivables, paid purchases, payables, payroll cost, and operating result. It filters by business and excludes unrelated rows. The source records and journal lines are the basis for future period-filtered cash-flow, profit-and-loss, payroll-liability, tax, and exception reports. Reports should read posted source records and balanced journals; they should not infer financial facts from LLM text.

### Credit dossier MVP

`POST /api/businesses/{business_id}/dossiers` creates a persisted draft dossier for an explicit reporting period. The snapshot is deterministic and contains the business profile, ownership references, revenue from issued/paid sales invoices, costs from approved/paid AP invoices, approved payroll runs, active credit facilities, cash balance, statutory-remittance counts, data gaps, limitations, and source record IDs. `GET /api/businesses/{business_id}/dossiers` lists drafts and the item route reads one draft.

Draft, cancelled, and `needs_review` financial records are excluded. A selected loan request is included only when its status is `approved`; otherwise it is excluded and recorded as a data gap. The dossier currently provides a transparent accounting analysis only. It does not determine scheme eligibility, recommend lenders, certify records, or submit anything externally. The route is not production-ready until authentication and per-owner access control are fully operational.

The dossier MVP now also supports `GET /api/businesses/{business_id}/dossiers/{dossier_id}/pdf`. This generates a professional PDF containing the applicant overview, LLM-generated neutral narrative, calculated metrics, ownership, statutory remittance summary, data gaps, limitations, declaration placeholder, traceability record IDs, and the input snapshot SHA-256 hash. If `OPENAI_API_KEY` is unavailable, the PDF remains available with an explicit narrative `needs_review` status instead of pretending that an LLM processed it.

Account endpoints are available at `/api/auth/register`, `/api/auth/login`, and `/api/auth/me`. Authenticated business creation creates an owner membership; dossier creation, reading, and PDF download require a membership for that business. `BusinessMembership` stores `owner`, `accountant`, or `viewer` roles. Existing legacy businesses without memberships must be explicitly linked before their dossiers can be accessed through the authenticated API. Authentication is still an MVP boundary: production deployment needs secure secret management, email verification, password reset, rate limiting, and a complete owner/admin membership-management UI.

For local development, copy `.env.example` to `.env` and set `AMANAH_JWT_SECRET` to a stable private value. The API loads `.env` before issuing or validating tokens; changing this value invalidates previously issued tokens, but does not delete user accounts or passwords. Docker receives the same value through the Compose `env_file`.

### Account security implementation

- **Registration and login:** passwords are bcrypt-hashed; email addresses are normalized; access tokens expire after 30 minutes; refresh sessions last 30 days.
- **Email verification:** registration creates a single-use, expiring hashed token and attempts delivery through SMTP. The response reports `verification_email_sent`; production must configure SMTP and `APP_PUBLIC_URL`.
- **Password reset:** reset requests always return the same generic response, then create a single-use token for an existing account. Confirmation changes the password and revokes all existing refresh sessions.
- **Refresh tokens:** refresh tokens are opaque, stored only as SHA-256 hashes, rotated on every use, and invalidated on logout. Access tokens reference the refresh session, so revoking the session invalidates the access token.
- **Account deletion:** `DELETE /api/auth/me` requires the current password, anonymizes the email, disables the account, and revokes sessions while preserving financial records and audit history.
- **Rate limiting:** login, registration, and reset requests use persistent database buckets. Rate limiting means restricting repeated requests per client within a time window; it reduces password guessing, reset-email abuse, and denial-of-service pressure. A shared Redis limiter should replace the database buckets when deploying multiple API replicas.

Account endpoints are now `/api/auth/register`, `/api/auth/login`, `/api/auth/verify-email`, `/api/auth/password-reset/request`, `/api/auth/password-reset/confirm`, `/api/auth/refresh`, `/api/auth/logout`, `/api/auth/me`, and `DELETE /api/auth/me`. Owner-level access remains separate from authentication: every business-scoped route must check `BusinessMembership`.

Before production deployment, configure a stable 32-character-or-longer `AMANAH_JWT_SECRET`, `APP_PUBLIC_URL`, SMTP credentials, HTTPS, a shared rate-limit store, and a versioned database migration process. Add email provider monitoring, password-reset UI, refresh-token storage in the frontend, and owner/member administration before opening account creation publicly.

SMTP configuration uses the mailbox/provider account that sends transactional messages, not the application's users:

- `SMTP_HOST`: provider hostname, such as the SMTP server supplied by the email provider.
- `SMTP_PORT`: normally `587` for STARTTLS, which is what the current sender uses.
- `SMTP_USERNAME`: the SMTP login, commonly the full sending mailbox address or provider-issued username.
- `SMTP_PASSWORD`: the SMTP password or provider app-specific password/API-generated SMTP credential; never commit it.
- `SMTP_FROM`: the verified sender address shown to recipients, for example `no-reply@your-domain.example`.
- `APP_PUBLIC_URL`: the public frontend URL where verification and password-reset pages exist, not the API URL.

All financial, accounting, invoice, mandate, business, forecast, agent, and dossier API routers now require a valid bearer token. Business-path routes additionally require a matching `BusinessMembership`; owner-only actions remain role-restricted. The remaining deployment step is to add membership filtering to legacy unscoped records and complete per-route role policies for the frontend.

### Predictions, alerts, and assistant

Business-scoped prediction endpoints are:

- `POST /api/businesses/{business_id}/predictions/forecast?horizon_days=30|60|90`
- `GET /api/businesses/{business_id}/predictions/forecasts`
- `GET /api/businesses/{business_id}/predictions/alerts`
- `GET /api/businesses/{business_id}/predictions/notifications`

Forecasts use the latest recorded cash balance, issued/partially-paid/paid sales invoices, approved/paid purchase invoices, approved payroll runs, and active credit facilities. They project a simple recent daily average and explicitly expose limitations. A negative projected balance creates a high-severity cash-shortfall alert; a small projected buffer creates a medium alert. Notifications are stored for all business members. These are indicators, not guaranteed predictions.

The in-app assistant is available at:

- `POST /api/businesses/{business_id}/assistant/text`
- `POST /api/businesses/{business_id}/assistant/voice`

Text requests are answered from a generated business context containing the forecast and open alerts. Voice uploads are transcribed first, then passed through the same text assistant path. The assistant must not approve payments, invent figures, promise financing, or provide legal advice. Without `OPENAI_API_KEY`, text returns an explicit `needs_review` response and voice returns configuration failure; raw audio is not stored.

## Failure paths and open risks

- Invalid files, unavailable OpenAI configuration, parser failures, and extraction failures return `failed`.
- Missing or non-numeric money and failed reconciliation return `needs_review` rather than raising during draft creation.
- `PII_ENCRYPTION_KEY` is required when encryption helpers are used. Decryption failures raise instead of returning ciphertext.
- Startup creates new tables and applies only the additive business-link and review/e-invoice columns needed by this foundation. A versioned migration tool is still required before production deployment.
- The upload endpoint is still unauthenticated and has no spend/rate cap.
- Payroll rates, lender thresholds, and Malaysian regulatory figures are deliberately not calculated or changed until verified against official sources.

## Deployment steps still required

Set a stable `PII_ENCRYPTION_KEY`, choose and document a database migration procedure, and verify the individual e-invoice boundary and all cited LHDN/RMCD figures before production use.
