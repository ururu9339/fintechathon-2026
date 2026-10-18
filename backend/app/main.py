from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import accounting, agent, assistant, auth, business, dossier, invoices, mandates, predictions
from .core.llm import get_openai_client
from .db import init_db

app = FastAPI(title="AmanahPay Treasurer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices.router)
app.include_router(mandates.router)
app.include_router(agent.router)
app.include_router(accounting.router)
app.include_router(business.router)
app.include_router(dossier.router)
app.include_router(auth.router)
app.include_router(predictions.router)
app.include_router(assistant.router)


@app.on_event("startup")
def create_database() -> None:
    init_db()

if __name__ == "__main__":
    init_db()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
