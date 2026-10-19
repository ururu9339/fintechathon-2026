# Qyze Ai

Qyze Ai is an authenticated FastAPI business-finance backend for SME accounting, invoice review, payment mandates, credit dossiers, forecasting, and an AI finance assistant. The frontend is being rebuilt separately; the current repository contains its Expo configuration, but no finished frontend screens.

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
QYZEAI_JWT_SECRET=replace-with-at-least-32-random-characters
DATABASE_URL=postgresql+psycopg://qyzeai:qyzeai@localhost:5432/qyzeai
```

`OPENAI_API_KEY` is optional. It enables LLM invoice extraction fallback, dossier narrative generation, and the assistant. SMTP variables are required only for real verification and password-reset email delivery. `PII_ENCRYPTION_KEY` is required only by code paths that encrypt PII.

Start PostgreSQL and the API:

```bash
docker compose up -d db
PYTHONPATH=. uvicorn backend.app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive documentation is at `http://localhost:8000/docs`.

## Docker

The Compose database uses the Qyze Ai defaults:

```text
database: qyzeai
user: qyzeai
password: qyzeai
```

For an existing PostgreSQL volume created with the previous database name, do not delete the volume. Create or migrate the `qyzeai` role/database while preserving the existing data, as described in `docs/workflow.md`.

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
PYTHONPATH=. .venv/bin/pytest -q backend/tests
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
