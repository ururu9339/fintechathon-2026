# Architecture decisions

| Decision | Why |
| --- | --- |
| Next.js for the first frontend | It matches the requested product stack and gives the team a deployable web demo. |
| Plain Python agent boundary first | The safety policy is deterministic and testable; LangGraph can wrap the same steps later without changing the API contract. |
| Process-local MVP storage | It keeps the hackathon skeleton runnable immediately; PostgreSQL migration belongs behind `backend/app/db.py`. |
| Hash-chain audit events | It makes every approval and block tamper-evident in the demo and is easy to persist later. |
