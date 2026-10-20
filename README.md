# AmanahPay

AmanahPay is an authenticated FastAPI business-finance backend for SME accounting, invoice review, payment mandates, credit dossiers, forecasting, and an AI finance assistant. The frontend is being rebuilt separately; the current repository contains its Expo configuration, but no finished frontend screens.

## Current capabilities

- User registration, login, email verification, password reset, refresh-token rotation, logout, and soft account deletion.
- Business memberships with `owner`, `accountant`, and `viewer` roles.
- Business-scoped counterparties, ownership, cash balances, loan requests, statutory remittances, and credit facilities.
- Expense invoice form/upload intake with local PDF/DOCX/image processing, OCR, optional OpenAI extraction, validation, review, approval, and payment.
- Sales invoices, receipts, ledger accounts, journal entries, employees, and payroll summaries.
- Reusable payment mandates with supplier allowlists, transaction/daily limits, expiry, verification requirements, audit events, and a mock payment rail.
- Credit dossier snapshots and professional PDF generation. OpenAI is optional for the dossier narrative.
- Data-driven 30/60/90-day cash forecasts and transient presentation alerts.
- Authenticated text and voice assistant routes. Voice is transcribed before the text assistant is called.

AI output is advisory or extraction-only. The backend validates data and keeps approval/payment at the policy boundary.

## Demo video

https://github.com/user-attachments/assets/dd416b47-d9f5-4419-aa2a-ff649fbf3526


## System architecture

```mermaid
flowchart TB
    Client[API client or future frontend] --> API[FastAPI application]
    API --> Auth[JWT authentication and memberships]
    API --> Services[Policy and accounting services]
    API --> Extract[Document parser, OCR, and optional LLM extraction]
    API --> Dossier[Dossier and PDF generation]
    API --> Forecast[Forecast and assistant context]
    Services --> DB[(PostgreSQL via SQLModel)]
    Auth --> DB
    Dossier --> DB
    Forecast --> DB
    Services --> Audit[Persisted audit events]
    Services --> Rail[Mock payment rail]
```

The active application is the backend registered in `backend/app/main.py`. It exposes authentication, business, invoice, accounting, mandate, dossier, prediction, assistant, and audit routers. The old `/api/agent` router is not registered. PostgreSQL is the configured persistence layer, and startup currently performs SQLModel table creation plus additive compatibility changes.

## Core algorithms

### Invoice extraction and validation

1. Validate upload type and file structure.
2. Extract native PDF/DOCX text or run OCR for images/scanned content.
3. Use the optional OpenAI client for structured extraction when configured.
4. Normalize dates and monetary values into application types.
5. Reconcile subtotal, tax, total, and line-item amounts locally.
6. Store the result as `draft` or `needs_review`; extraction does not approve or pay an invoice.

### Mandate payment authorization

`Treasurer.pay()` evaluates payment rules in order and stops at the first failure:

1. Mandate exists and is active.
2. Mandate has not expired.
3. Supplier or counterparty is allowlisted.
4. Required supplier verification is present.
5. Invoice reference is present.
6. Transaction limit is respected.
7. Daily limit is respected.
8. Payment purpose matches the mandate.

Approved and blocked decisions are written to the audit chain and persisted when a database session is available.

### Forecasting

The forecast service uses the latest cash balance, recent issued/partially-paid/paid sales, approved/paid purchases, approved payroll runs, and active credit facilities. It computes recent average daily inflow, outflow, and debt service, then projects each day over a 30-, 60-, or 90-day horizon. Negative projected cash produces a high-severity alert; a projected minimum below MYR 5,000 produces a medium alert. These are deterministic recent-average projections, not trained predictions.

### Credit dossier

The dossier service builds a deterministic reporting-period snapshot from approved/issued source records, ownership, cash, credit, payroll, and statutory-remittance data. It records source IDs and a SHA-256 input hash. ReportLab renders the PDF; OpenAI is used only for the optional neutral narrative.

## Security design

- Passwords are hashed with bcrypt.
- Access tokens are JWTs signed with `AMANAH_PAY_JWT_SECRET`, expire after 30 minutes, and may reference a refresh session.
- Refresh tokens and email action tokens are stored only as SHA-256 hashes.
- Refresh tokens rotate on use; logout and password reset revoke refresh sessions.
- Email verification and password reset tokens expire and are single-use.
- Business records require a matching `BusinessMembership`.
- Roles are `owner`, `accountant`, and `viewer`; owner-only checks are enforced, while accountant-versus-viewer enforcement remains an identified risk below.
- Account deletion deactivates and anonymizes the account while preserving financial records.
- Login, registration, and password-reset requests use database-backed rate-limit buckets.
- Payment decisions are validated at the backend policy boundary and audited.

## Security self-assessment

### Permission-tier implementation

| Tier | Implemented behavior |
|---|---|
| `owner` | Can manage business members and perform owner-restricted ownership actions. |
| `accountant` | Intended to perform implemented invoice, mandate, accounting, payroll, credit, and financial-record mutations requiring accountant access; the shared helper does not yet fully distinguish this tier from `viewer`. |
| `viewer` | Can access authorized business-scoped read paths where the route permits viewer access. |
| Unauthenticated | Can use only public authentication flows and health/API discovery; protected business and finance routes require a bearer token. |

### Known-risk list

- Startup schema setup is not a versioned migration system.
- Provider invoice intake does not yet verify an external provider signature or credential.
- The payment rail is a mock implementation.
- Database-backed rate limiting is not a shared distributed limiter for multiple API replicas.
- SMTP, OpenAI, secret management, HTTPS, and production database operations require deployment configuration.
- `PII_ENCRYPTION_KEY` is required for encryption helper paths but is not supplied by the repository.
- The assistant and dossier narrative depend on optional OpenAI configuration and should remain advisory.
- The shared business-access helper currently checks membership and owner access, but does not fully enforce `minimum_role="accountant"`; accountant-only route claims need a focused authorization fix and tests.
- The frontend is unfinished and is excluded from this backend assessment.

## Deployment instructions

### Docker Compose

```bash
cp .env.example .env
# Set AMANAH_PAY_JWT_SECRET to a stable random value of at least 32 characters.
docker compose up -d --build db api
```

The API is exposed at `http://localhost:8000`. Swagger is available at `/docs`, and health is available at `/health`. Configure SMTP and `APP_PUBLIC_URL` for real email verification and password-reset delivery. Configure `OPENAI_API_KEY` only when LLM-backed features are needed.

### Existing database volume

Do not delete an existing PostgreSQL volume solely because the product was renamed. If it was initialized with the previous database/user names, create or migrate the `amanahpay` role and database while preserving the existing data, then set `DATABASE_URL` accordingly.

### Local API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d db
PYTHONPATH=. uvicorn backend.app.main:app --reload
```

The backend Dockerfile installs Tesseract and the packages declared in `backend/requirements.txt`. The root `requirements.txt` delegates to that same canonical list.

## Test cases

The pytest suite covers the backend, payment safety guardrails, and document-agent helpers:

### `backend/tests/test_services.py`

- SQLModel user serialization into the public response schema.
- Password hashing, password verification, refresh sessions, action tokens, and JWT creation.
- Zero-rate and regular dossier installment calculations.
- Data-driven forecast generation and transient cash alerts.
- Dossier inclusion of approved/issued records, exclusion of drafts, stable input hashes, and data gaps.
- Mandate blocking for an unknown supplier.
- Prompt-injection blocking in the legacy internal treasurer parser.
- Approved invoice payment linking to a `PaymentRequest`.
- Rejection of inconsistent invoice totals.
- Blocking invoice payment without a mandate.
- Audit-chain hash linkage.
- Reversible employee deactivation/reactivation and salary updates.
- Credit facility approval and repayment to `paid_off`.
- Business ownership and statutory-remittance creation.
- Invoice money/date normalization and local reconciliation behavior.

### `backend/tests/test_finance.py`

- Weekly cash-forecast transaction bucketing and rolling balances.
- Rejection of transactions with conflicting inflow and outflow values.
- Effective annual rate calculations and financing-offer selection.

### `backend/tests/test_injection_guardrails.py`

- Prompt-injection detection in both the agent and policy layers.
- Blocking prompt-injected and unallowlisted payment requests before the mock payment rail is called.

### `agent/tests/test_agent.py`

- Invoice amount extraction from document text.
- Prompt-injection detection.
- Document-text compaction and size limits.
- Image downscaling while preserving aspect ratio and returning the expected MIME type.

## Repository layout

```text
backend/app/       FastAPI application, models, auth, services, and routes
backend/tests/     Pytest regression suite
agent/             Document parsing, OCR, extraction, and prompt-safety helpers
rail/              Mock payment rail
frontend/          Expo configuration; frontend screens are being rebuilt
scripts/           Local demo-data seed script
docs/workflow.md   Current API workflow and deployment notes
docker-compose.yml Local PostgreSQL, API, and frontend orchestration
```

## Requirements

- Python 3.12+ for Docker; the local virtual environment used by this repository is Python 3.14.
- Node.js 20+ and npm for the frontend rebuild.
- Docker Desktop, if using PostgreSQL through Compose.
- Tesseract OCR for local non-Docker execution of image/scanned-document flows.

## Backend local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

Set a stable secret in `.env`:

```env
AMANAH_PAY_JWT_SECRET=replace-with-at-least-32-random-characters
DATABASE_URL=postgresql+psycopg://amanahpay:amanahpay@localhost:5432/amanahpay
```

`OPENAI_API_KEY` is optional. It enables LLM invoice extraction fallback, dossier narrative generation, and the assistant. SMTP variables are required only for real verification and password-reset email delivery. `PII_ENCRYPTION_KEY` is required only by code paths that encrypt PII.

Start PostgreSQL and the API:

```bash
docker compose up -d db
PYTHONPATH=. uvicorn backend.app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive documentation is at `http://localhost:8000/docs`.

## Docker

The Compose database uses the AmanahPay defaults:

```text
database: amanahpay
user: amanahpay
password: amanahpay
```

For an existing PostgreSQL volume created with the previous database name, do not delete the volume. Create or migrate the `amanahpay` role/database while preserving the existing data, as described in `docs/workflow.md`.

The API image installs backend dependencies and Tesseract. The frontend service is not a finished product yet and will not build until the frontend rebuild adds its application entrypoint.

## Demo data

After PostgreSQL is available:

```bash
PYTHONPATH=. .venv/bin/python scripts/seed_demo_business.py
```

The seed is idempotent and creates a fictional business with an owner, counterparties, invoices, sales, payroll, remittances, cash, credit, mandate, ledger records, and a dossier.

## Authentication and business context

Authorize Swagger requests with `Bearer <access-token>` after calling `/api/auth/login`. Call `GET /api/businesses` to list the authenticated user’s linked businesses. For a single-business account, business-scoped routes derive the business automatically. For a multi-business account, pass the selected `business_id` query parameter where supported; membership is always checked by the backend.

Example:

```text
GET /api/invoices?business_id=<selected-business-id>
```

## Validation

```bash
PYTHONPATH=. .venv/bin/pytest -q backend/tests agent/tests
PYTHONPATH=. .venv/bin/python -m compileall -q backend/app agent
git diff --check
docker compose config --quiet
```

The frontend build is intentionally not listed as a passing handoff check because the frontend is being rebuilt by the frontend owner.

## Important limitations

- Database startup uses SQLModel table creation and additive compatibility changes, not a versioned migration system.
- Provider invoice intake has no external provider-signature verification yet.
- Forecasts are recent-average projections, not trained financial models.
- The payment rail is a mock rail.
- SMTP, OpenAI, production secret management, shared rate limiting, and frontend owner/member administration require deployment configuration or additional implementation.
