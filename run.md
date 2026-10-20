# Running the App Locally

This guide covers two ways to run the webapp: **Docker** (recommended, zero setup) and **manual** (run each service separately).

---

## Required Technologies

| Technology | Version | Purpose |
|---|---|---|
| [Git](https://git-scm.com/) | any | Clone the repository |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime |
| [Node.js](https://nodejs.org/) | 20+ | Frontend runtime |
| [npm](https://www.npmjs.com/) | 10+ | Frontend package manager (bundled with Node.js) |
| [PostgreSQL](https://www.postgresql.org/download/) | 16 | Database |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | any | Document parsing / OCR |
| [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/) | any | Required for the Docker path only |

---

## Option A — Docker (Recommended)

Runs everything (database + backend API + frontend) in one command. No manual installs of Python, Node, or PostgreSQL needed beyond Docker itself.

### Step 1 — Install Docker Desktop

Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). This includes both Docker and Docker Compose.

Verify installation:

```bash
docker --version
docker compose version
```

### Step 2 — Clone the repository

```bash
git clone <your-repo-url>
cd fintechathon-2026
```

### Step 3 — Create the environment file

```bash
cp .env.example .env
```

Open `.env` and fill in the values:

```env
# Required — use any long random string (e.g. generate with: openssl rand -hex 32)
AMANAH_PAY_JWT_SECRET=replace-with-a-long-random-secret

# Optional — enables AI-powered dossier narrative generation
OPENAI_API_KEY=

# Leave as-is for local Docker use
APP_PUBLIC_URL=http://localhost:3000
```

> The `DATABASE_URL` and `SMTP_*` fields can be left blank for local development. Docker manages the database automatically.

### Step 4 — Start all services

```bash
docker compose up --build
```

This will:
1. Start a PostgreSQL 16 database on port `5432`
2. Build and start the FastAPI backend on port `8000`
3. Build and start the Expo/React Native web frontend on port `3000`

Wait until you see the backend log line: `Application startup complete.`

### Step 5 — Open the app

Visit **[http://localhost:3000](http://localhost:3000)** in your browser.

The API is also accessible at **[http://localhost:8000](http://localhost:8000)** (e.g. `http://localhost:8000/health`).

### Stopping

```bash
docker compose down
```

To also delete the database volume (fresh start):

```bash
docker compose down -v
```

---

## Option B — Manual (Run Services Separately)

Use this if you prefer to run each service directly on your machine.

### Step 1 — Install prerequisites

#### Python 3.12+
Download from [python.org](https://www.python.org/downloads/) or use a version manager like `pyenv`.

```bash
python3 --version   # must be 3.12 or higher
```

#### Node.js 20+ and npm
Download from [nodejs.org](https://nodejs.org/) (LTS recommended).

```bash
node --version   # must be 20 or higher
npm --version
```

#### PostgreSQL 16
Download from [postgresql.org](https://www.postgresql.org/download/) or use Homebrew on macOS:

```bash
brew install postgresql@16
brew services start postgresql@16
```

#### Tesseract OCR
Required by the backend for document parsing.

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download the installer from the [Tesseract GitHub releases](https://github.com/tesseract-ocr/tesseract/releases).

---

### Step 2 — Clone the repository

```bash
git clone <your-repo-url>
cd fintechathon-2026
```

### Step 3 — Set up the database

Create the PostgreSQL user and database:

```bash
psql -U postgres
```

Inside the `psql` shell:

```sql
CREATE USER amanahpay WITH PASSWORD 'amanahpay';
CREATE DATABASE amanahpay OWNER amanahpay;
\q
```

### Step 4 — Create the environment file

```bash
cp .env.example .env
```

Open `.env` and set:

```env
# Required
AMANAH_PAY_JWT_SECRET=replace-with-a-long-random-secret

# Optional
OPENAI_API_KEY=

APP_PUBLIC_URL=http://localhost:3000

# Use this exact URL when running locally (not inside Docker)
DATABASE_URL=postgresql+psycopg://amanahpay:amanahpay@localhost:5432/amanahpay
```

### Step 5 — Install and start the backend

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at **[http://localhost:8000](http://localhost:8000)**.
Database tables are created automatically on first startup.

Verify it is running:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Step 6 — Install and start the frontend

Open a **new terminal** (keep the backend running):

```bash
cd frontend

# Install dependencies
npm install

# Start the web dev server
npm run web
```

The frontend will be available at **[http://localhost:8081](http://localhost:8081)** (Expo default) or **[http://localhost:3000](http://localhost:3000)** if you build and serve the static bundle instead:

```bash
# Alternative: build and serve the production bundle
npm run build:web
npx serve dist -l 3000
```

---

## Seed Demo Data (Optional)

To populate the database with realistic demo data for testing:

```bash
# With the backend running and .venv active
source .venv/bin/activate
python scripts/seed_demo_business.py
```

---

## Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `AMANAH_PAY_JWT_SECRET` | **Yes** | — | Secret key used to sign JWT tokens. Use a long random value. |
| `OPENAI_API_KEY` | No | — | Enables AI-powered dossier narrative generation. |
| `APP_PUBLIC_URL` | No | `http://localhost:3000` | Public URL of the frontend (used in emails). |
| `DATABASE_URL` | No | `postgresql+psycopg://amanahpay:amanahpay@localhost:5432/amanahpay` | PostgreSQL connection string. |
| `SMTP_HOST` | No | — | SMTP server hostname for sending emails. |
| `SMTP_PORT` | No | `587` | SMTP server port. |
| `SMTP_USERNAME` | No | — | SMTP login username. |
| `SMTP_PASSWORD` | No | — | SMTP login password. |
| `SMTP_FROM` | No | — | From address used in outgoing emails. |
| `EXPO_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API URL consumed by the frontend. |

---

## Port Summary

| Service | Port | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
| PostgreSQL | 5432 | `postgresql://localhost:5432/amanahpay` |
| Expo dev server (manual) | 8081 | http://localhost:8081 |

---

## Troubleshooting

**`psycopg` connection error on startup**
Make sure PostgreSQL is running and the `DATABASE_URL` in `.env` is correct. On macOS: `brew services start postgresql@16`.

**`tesseract: command not found`**
Tesseract is not installed. Follow the install step for your OS above.

**Frontend can't reach the backend (CORS / network error)**
Ensure the backend is running on port `8000` before opening the frontend. If you changed the port, update `EXPO_PUBLIC_API_URL` in `.env`.

**Port already in use**
Kill the process on the conflicting port:
```bash
lsof -ti:8000 | xargs kill   # replace 8000 with the occupied port
```
