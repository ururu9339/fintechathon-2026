# Architecture and data flow

```mermaid
flowchart LR
  UI[Next.js dashboard] --> API[FastAPI]
  API --> Agent[Agent policy graph]
  API --> Core[Mandate + forecast core]
  Core --> Audit[Hash-chain audit]
  Core --> Rail[Mock payment rail]
  Core --> DB[(PostgreSQL seam)]
  Data[Synthetic data + MyInvois templates] --> Core
```

The frontend calls JSON endpoints for forecast, envelopes, financing, agent
messages, payments, and audit events. The backend is the policy boundary:
agent text is checked before any action, mandates validate supplier/purpose/
limits/expiry, and every approval or block is appended to the audit chain.
The current MVP keeps state in process memory so the demo starts without
infrastructure; `backend/app/db.py` is the replacement seam for PostgreSQL.
