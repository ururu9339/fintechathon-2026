# Project Outline & Technical Specifications

> **Overview**: Core project ideas, architecture roadmap, tech stack, and deliverable tracking for the hackathon.

---

## System Architecture

### **Hybrid Architecture (The Industry Standard)**

* **On-Device Processing (Privacy & Speed)**
  * Fast, sensitive processing stays directly on the device for privacy and zero-latency responsiveness.
  * **Components**: C++ calculation engine, local database (e.g., SQLite), transaction parsing.

* **Cloud Fallback (Heavy Computation & Reasoning)**
  * Complex reasoning and heavy workloads are routed via HTTPS to cloud services or commercial APIs.
  * **Components**: Complex LLM reasoning, heavy portfolio risk simulations.

---

## AI / ML Strategy

| Model Type | Purpose & Scope | Notes |
| :--- | :--- | :--- |
| **Fine-Tuned Small LLM** | User query processing & conversational financial advice | Handles natural language interaction and domain-specific guidance |
| **Classical ML (Non-LLM)** | Predictive modeling & quantitative calculations | Requires manual dataset preparation and training |

---

## Probable Tech Stack

* **`C++`** — High-performance computation & calculation engine (on-device)
* **`Python`** — Backend APIs, machine learning pipelines, and integrations
* **`React Native`** — Cross-platform client applications (Mobile apps & Web app)

---

## Infrastructure & Platforms

| Category | Provider / Service | Details & Links |
| :--- | :--- | :--- |
| **Database** | **MongoDB Atlas** | • Development: `M0` (Free tier)<br>• Pitching Day: Scale up to `M10`<br>[MongoDB Console & Billing](https://cloud.mongodb.com/v2#/org/68b4f252071a514fb7c181ca/billing/overview) |
| **Hosting** | **Microsoft Azure** | Cloud backend and API hosting |
| **Domain** | **Name.com** | • Via GitHub Student Pack<br>• *Action item: Finalize product name first*<br>[Name.com Student Offer](https://www.name.com/ru-ru/partner/github-students) |

---

## Documentation & Deliverables

> [!IMPORTANT]
> All documentation must be completed **one day before** pitch day.

- [ ] **Getting Started Guide**: Dedicated, clear walkthrough crafted specifically for the jury/judges.
- [ ] **Technical Documentation**: Complete system architecture diagrams, data flows, and component specs.

---

## Team Work Distribution

| Team Member | Assigned Responsibilities | Status |
| :--- | :--- | :---: |
| **Member 1** | *[To be assigned]* | Pending |
| **Member 2** | *[To be assigned]* | Pending |
| **Member 3** | *[To be assigned]* | Pending |
| **Member 4** | *[To be assigned]* | Pending |