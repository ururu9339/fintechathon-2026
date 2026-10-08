# 🗺️ SME Finance Copilot — Team Learning Roadmap & Course Guide

> **Project Concept:**  
> **SME Finance Copilot** is an intelligent financial assistant for small-and-medium enterprises (SMEs). It provides:
> 1. **Cash-Flow Management & Alerts:** Real-time visibility, runway projections, and proactive deficit/anomaly alerts.
> 2. **Financing-Option Matching:** Eligibility assessment and intelligent recommendation engine matching SME financial health to loans, grants, and credit facilities.
> 3. **Business Financial Analysis:** Automated KPI extraction (liquidity, burn rate, margins) and an interactive LLM-powered financial advisory copilot.

---

## 🎯 Purpose of This Roadmap

This guide is designed for team members who are starting out in software development. Rather than overwhelming you with exhaustive theoretical textbooks, this roadmap breaks down **essential topics, milestones, and high-quality official resources** so everyone can acquire practical skills and contribute quickly to the hackathon project.

*Note: The tech stack below reflects our initial blueprint. Specific tools and libraries can be swapped as project requirements evolve.*

---

## 🧭 High-Level Architecture & Tech Stack Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        🖥️ Frontend (Web App)                           │
│      React / TypeScript · Tailwind CSS · Recharts / Chart.js           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP / JSON REST APIs
┌──────────────────────────────────▼─────────────────────────────────────┐
│                        ⚙️ Backend API Layer                            │
│           FastAPI (Python) · Pydantic · JWT Authentication             │
└──────┬───────────────────────────┬──────────────────────────────┬──────┘
       │                           │                              │
┌──────▼──────────────┐   ┌────────▼─────────────┐   ┌────────────▼──────┐
│  🗄️ Data & Storage  │   │ 📊 Financial Engine  │   │ 🤖 AI / Copilot   │
│ PostgreSQL / SQLite │   │ Pandas · NumPy       │   │ LLM API / RAG     │
│ SQLAlchemy ORM      │   │ Cash Flow & Ratio    │   │ LangChain /       │
│ Redis (optional)    │   │ Algorithms           │   │ LlamaIndex        │
└─────────────────────┘   └──────────────────────┘   └───────────────────┘
```

---

## 👥 Suggested Team Tracks & Roles

To work effectively without stepping on each other's toes, team members can specialize in one primary track while understanding the shared core:

| Track | Primary Responsibilities | Core Focus |
|---|---|---|
| **🎨 Frontend Track** | User dashboard, financial data visualization, chat interface | React, TypeScript, Tailwind, Charting |
| **⚙️ Backend Track** | REST APIs, database schemas, business logic, auth | FastAPI, PostgreSQL, SQLAlchemy |
| **📊 Data & Analytics Track** | Cash flow modeling, ratio calculations, alert logic | Python, Pandas, Financial Metrics |
| **🤖 AI & Copilot Track** | Financing matching logic, LLM prompt engineering, RAG | LLM APIs, LangChain, Embeddings |

---

## 📚 Step-by-Step Curriculum

### Phase 0: Foundations & Collaborative Workflow (All Members)
*Everyone must master these basics before writing project code.*

#### Topics & Skills
- **Git & GitHub Essentials:** Repositories, cloning, branching, committing, pull requests, resolving merge conflicts.
- **Development Environment:** Terminal/CLI navigation, VS Code setup, virtual environments (`venv` or `conda`), Node/npm setup.
- **Client-Server Basics:** How HTTP works (GET, POST, PUT, DELETE), status codes (200, 400, 401, 404, 500), JSON payload format.
- **Environment Configuration:** Managing secrets safely using `.env` files and `.gitignore`.

#### Learning Resources
- 🔗 [GitHub Git Handbook](https://docs.github.com/en/get-started/using-git/about-git) — Official Git guide
- 🔗 [Git Branching Tutorial (Interactive)](https://learngitbranching.js.org/) — Visual branch learning
- 🔗 [MDN: HTTP Overview & Methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview) — Web fundamentals
- 🔗 [VS Code Getting Started Guide](https://code.visualstudio.com/docs) — IDE tips & shortcuts

---

### Phase 1: Frontend Development Track
*Goal: Build responsive dashboards, financial data charts, and copilot interaction UI.*

#### Topics & Skills
- **HTML5 & CSS3 Basics:** Semantic structure, Flexbox, CSS Grid.
- **JavaScript & TypeScript Fundamentals:** Variables, arrow functions, async/await, promises, TypeScript interfaces/types.
- **React Core Concepts:** Component architecture, JSX, props, state (`useState`), side effects (`useEffect`), forms.
- **Styling:** Utility-first styling with Tailwind CSS for rapid modern UI development.
- **Financial Visualizations:** Rendering bar charts, line charts (cash burn rate, projections) using Recharts or Chart.js.
- **API Integration:** Fetching and posting data using `fetch` or `axios`, handling loading and error states.

#### Learning Resources
- 🔗 [React Official Documentation](https://react.dev/learn) — Interactive modern React tutorials
- 🔗 [TypeScript Official Handbook](https://www.typescriptlang.org/docs/handbook/intro.html) — Types and syntax
- 🔗 [Tailwind CSS Documentation](https://tailwindcss.com/docs) — Utility classes and components
- 🔗 [Recharts Documentation](https://recharts.org/en-US/) — Composable charting library for React
- 🔗 [MDN JavaScript Guide](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide) — Core language reference

---

### Phase 2: Backend & Database Track
*Goal: Build reliable APIs to ingest SME data, run financial rules, and serve clean responses.*

#### Topics & Skills
- **Python Modern Practices:** Type hinting, dictionaries, list comprehensions, modules and packages.
- **FastAPI Framework:** Path parameters, query parameters, request bodies with Pydantic validation, dependency injection.
- **RESTful API Design:** Designing endpoints for `/api/cashflow`, `/api/financing/match`, `/api/copilot/chat`.
- **Database Modeling:** Relational tables (Users, Companies, Invoices, Transactions, FinancingOptions).
- **ORM & Database Access:** SQLAlchemy or SQLModel for database queries, migrations with Alembic.
- **Authentication & Security:** JWT tokens, password hashing (bcrypt), CORS configuration.

#### Learning Resources
- 🔗 [FastAPI Official Tutorial](https://fastapi.tiangolo.com/tutorial/) — Step-by-step FastAPI handbook
- 🔗 [Pydantic Documentation](https://docs.pydantic.dev/latest/) — Data validation & settings
- 🔗 [PostgreSQL Official Tutorial](https://www.postgresql.org/docs/current/tutorial.html) — Relational DB concepts
- 🔗 [SQLAlchemy 2.0 Unified Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) — Python database toolkit

---

### Phase 3: Data Analytics & Financial Engine Track
*Goal: Process raw financial records, calculate SME health indicators, and trigger alert signals.*

#### Topics & Skills
- **Data Manipulation with Pandas & NumPy:** Loading CSV/Excel data, filtering transactions, handling missing data, grouping by month/category.
- **SME Financial Metrics & Formulas:**
  - Net Cash Flow = Cash Inflows − Cash Outflows
  - Runway (Months) = Current Cash Reserve ÷ Monthly Burn Rate
  - Quick Ratio & Current Ratio (Liquidity indicators)
  - Debt Service Coverage Ratio (DSCR) for loan viability
- **Alert & Anomaly Detection:** Rule-based triggers (e.g., runway < 3 months, sudden 30% drop in revenue, overdue invoices).
- **Time-Series Projection Basics:** Simple rolling averages, linear trend forecasting, or seasonal forecasting for expected revenue and expenses.

#### Learning Resources
- 🔗 [Pandas Official Getting Started](https://pandas.pydata.org/docs/getting_started/index.html) — 10-minute guide & tutorials
- 🔗 [NumPy Absolute Beginners Guide](https://numpy.org/doc/stable/user/absolute_beginners.html) — Array math & operations
- 🔗 [Investopedia Financial Ratios Guide](https://www.investopedia.com/financial-ratios-4689817) — SME financial metrics explained
- 🔗 [Scikit-Learn User Guide](https://scikit-learn.org/stable/user_guide.html) — Basic regression & anomaly detection algorithms

---

### Phase 4: AI & Financing Copilot Track
*Goal: Implement intelligent financing option matching and an conversational business advisor.*

#### Topics & Skills
- **Matching Engine Logic:** Multi-criteria filtering (company age, monthly revenue, credit score, industry sector) against a database of loans/grants.
- **LLM Prompt Engineering:** System prompts, few-shot examples, structured output generation (JSON mode) for financial summaries.
- **RAG (Retrieval-Augmented Generation):** Chunking loan/policy documents, generating embeddings, vector retrieval to provide grounded recommendations.
- **Agent / Copilot Orchestration:** Connecting user questions ("Can I afford a $50k equipment loan right now?") with database calculations and LLM interpretation.

#### Learning Resources
- 🔗 [OpenAI / LLM API Documentation & Prompt Guide](https://platform.openai.com/docs/guides/prompt-engineering) — Prompt engineering strategies
- 🔗 [LangChain Documentation](https://python.langchain.com/docs/introduction/) — Building LLM-driven applications
- 🔗 [LlamaIndex Documentation](https://docs.llamaindex.ai/en/stable/) — Data framework for RAG and LLMs
- 🔗 [Hugging Face NLP Course](https://huggingface.co/learn/nlp-course) — Embeddings and transformers fundamentals

---

### Phase 5: Containerization, Testing & Deployment
*Goal: Package the system so every teammate and judge can run it with a single command.*

#### Topics & Skills
- **Docker Fundamentals:** Dockerfile syntax, images, containers.
- **Docker Compose:** Orchestrating frontend, backend, and PostgreSQL database locally.
- **API Testing:** Writing unit tests with `pytest` for backend calculations and endpoints.
- **Mock Data Generation:** Creating realistic mock datasets (synthetic SME transactions, balance sheets, loan catalogs).

#### Learning Resources
- 🔗 [Docker Getting Started Guide](https://docs.docker.com/get-started/) — Container basics
- 🔗 [Docker Compose Overview](https://docs.docker.com/compose/) — Multi-container applications
- 🔗 [Pytest Official Documentation](https://docs.pytest.org/en/stable/) — Python automated testing
- 🔗 [Faker Documentation](https://faker.readthedocs.io/en/master/) — Generating fake financial test data

---

## 📅 Suggested 4-Week Hackathon Preparation Timeline

```
Week 1: Foundations & Architecture Alignment
├── Phase 0 (Git, Dev Environment, Basic Web Concepts)
└── Team alignment on data schema & API contracts

Week 2: Core Engine & Prototyping
├── Frontend: Scaffold Dashboard & Navigation
├── Backend: Scaffold FastAPI & Database models
└── Data: Financial ratio & runway calculation scripts

Week 3: Intelligence & Feature Integration
├── Cash-flow alert engine & chart visualizations
├── Financing-option matching algorithm
└── LLM Copilot prompt integration & chat endpoint

Week 4: Polish, Testing & Pitch Preparation
├── End-to-end integration & Docker Compose setup
├── Synthetic demo dataset preparation
└── Presentation slides, demo video, and documentation
```

---

## 💡 Quick Tips for Newbie Teams

1. **Agree on the API Contract First:** Before writing code, agree on sample JSON request/response formats. The frontend team can build UI with mock data while the backend team builds the real logic.
2. **Prioritize the "Golden Path":** Focus on completing one full, working end-to-end flow (e.g. Upload data ➔ View cash-flow alert ➔ See recommended loan ➔ Ask copilot about it) before adding extra features.
3. **Small, Frequent Commits:** Make small pull requests instead of working on a giant branch for days.
4. **Don't Reinvent the Wheel:** Use open-source UI component libraries, ready-made charting components, and battle-tested libraries.
