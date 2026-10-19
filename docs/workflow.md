# Qyze Ai workflow

This document describes the current backend, not planned features. The frontend is being rebuilt separately and should integrate with the authenticated API described here.

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
docker compose up -d db
PYTHONPATH=. uvicorn backend.app.main:app --reload
```

Use `http://localhost:8000/docs` for Swagger. The frontend can call the API at `http://localhost:8000` during local development. The current frontend directory is only an Expo scaffold and is not a completed UI.

Required local configuration:

```env
QYZEAI_JWT_SECRET=<stable random value with at least 32 characters>
DATABASE_URL=postgresql+psycopg://qyzeai:qyzeai@localhost:5432/qyzeai
```

Optional configuration:

- `OPENAI_API_KEY`: LLM extraction fallback, dossier narrative, assistant text, and voice transcription.
- `PII_ENCRYPTION_KEY`: required when PII encryption helpers are used.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`: transactional verification/reset email.
- `APP_PUBLIC_URL`: public frontend URL used in email links.

## Authentication and business selection

1. Register or log in through `/api/auth/register` or `/api/auth/login`.
2. Send the returned access token as `Authorization: Bearer <token>`.
3. Use `GET /api/businesses` to retrieve all businesses linked to the account.
4. If exactly one business is linked, business-scoped routes derive its ID automatically.
5. If multiple businesses are linked, select one in the frontend and send its ID through the route/query parameter supported by that endpoint.

The server checks `BusinessMembership` on every business-scoped request. A supplied ID cannot be used to access another user’s business.

## Main API areas

### Accounts

- `/api/auth/register`
- `/api/auth/login`
- `/api/auth/verify-email`
- `/api/auth/password-reset/request`
- `/api/auth/password-reset/confirm`
- `/api/auth/refresh`
- `/api/auth/logout`
- `/api/auth/me`

Access tokens expire after 30 minutes. Refresh tokens are opaque, hashed in the database, and rotated on use.

### Business records

Business profiles, memberships, counterparties, ownership, loan requests, cash balances, and statutory remittances are under `/api/businesses`.

### Expense invoices and payments

Expense invoices can be entered with `POST /api/invoices` or uploaded with `POST /api/invoices/upload`. The backend performs local file validation, PDF/DOCX text extraction, OCR, optional LLM extraction, Decimal normalization, and total reconciliation.

Records are stored as `draft` or `needs_review`. The normal flow is:

1. Review with `GET /api/invoices/{invoice_id}`.
2. Correct with `PUT /api/invoices/{invoice_id}` when needed.
3. Approve with `POST /api/invoices/{invoice_id}/approve`.
4. Pay with `POST /api/invoices/{invoice_id}/pay`.

Payment requires an approved invoice and an active matching mandate. The mandate checks supplier, counterparty verification, purpose, expiry, transaction limit, and daily limit. The payment rail is currently a mock.

List invoices for a single-business account:

```text
GET /api/invoices
```

For a multi-business account:

```text
GET /api/invoices?business_id=<selected-business-id>
```

### Sales, ledger, payroll, and credit

The accounting router exposes:

- Sales invoices and receipts under `/api/accounting/sales`.
- Ledger accounts and balanced journal entries under `/api/accounting/ledger`.
- Employees and payroll summaries under `/api/accounting/payroll`.
- Credit facilities and repayments under `/api/accounting/credit`.
- Deterministic summary reporting under `/api/accounting/reports/summary`.

Business IDs are derived for authenticated single-business create requests where supported. If an account has multiple businesses, the frontend must provide the selected context. Every record read or mutation is checked against membership.

### Mandates and audit

Mandates are reusable authorization policies under `/api/businesses/{business_id}/mandates`. They do not create accounting metrics or replace invoice review.

Persisted audit events for a business are available at:

```text
GET /api/businesses/{business_id}/audit
```

The legacy `/api/agent` API is no longer registered. The current AI assistant is the supported conversational module.

### Credit dossiers

`POST /api/businesses/{business_id}/dossiers` creates a deterministic dossier snapshot for an explicit period. It uses approved/issued source records, records data gaps and limitations, and stores source IDs plus an input hash.

`GET /api/businesses/{business_id}/dossiers/{dossier_id}/pdf` generates the professional PDF. ReportLab creates the document. OpenAI is used only for the neutral narrative; without an API key the PDF remains available with a `needs_review` narrative status.

### Forecasts and assistant

Forecast routes:

- `POST /api/businesses/{business_id}/predictions/forecast?horizon_days=30|60|90`
- `GET /api/businesses/{business_id}/predictions/forecasts`

Forecasts use recent sales, approved/paid purchases, payroll, cash, and active credit facilities. Alerts are transient data inside the forecast response for frontend banners or notifications; they are not persisted workflow objects.

Assistant routes:

- `POST /api/businesses/{business_id}/assistant/text`
- `POST /api/businesses/{business_id}/assistant/voice`

Voice input is transcribed first and then sent through the text assistant. The assistant is advisory and must not approve payments or invent financial facts.

## Demo dataset

```bash
PYTHONPATH=. .venv/bin/python scripts/seed_demo_business.py
```

The script is idempotent and creates a fictional business with an owner membership, counterparties, sales and expense invoices, payroll, remittances, cash, credit, mandate, ledger entries, and a dossier.

## Database and handoff

Compose starts PostgreSQL with the default Qyze Ai database:

```text
database: qyzeai
user: qyzeai
password: qyzeai
```

Existing PostgreSQL volumes created with the previous database name are not automatically renamed. Preserve them and migrate or clone the data before switching `DATABASE_URL`.

The backend image installs all packages listed in `backend/requirements.txt` and installs Tesseract OCR. No manual Python dependency installation beyond that file should be necessary.

Before pushing, run:

```bash
PYTHONPATH=. .venv/bin/pytest -q backend/tests
PYTHONPATH=. .venv/bin/python -m compileall -q backend/app agent
git diff --check
docker compose config --quiet
```

The frontend build is intentionally excluded from the backend handoff gate because the frontend owner is rebuilding the application screens and entrypoint.

## Current deployment limitations

- Startup schema setup is not a replacement for versioned migrations.
- Provider webhooks need authenticated provider credentials/signature verification before production.
- Database-backed rate limiting should use shared storage for multiple API replicas.
- SMTP and OpenAI are optional local integrations but must be configured for their production features.
- The payment rail is mock-only.
