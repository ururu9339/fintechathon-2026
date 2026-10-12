from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import forecast, invoices, mandates
from .db import treasurer

app = FastAPI(title="AmanahPay Treasurer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(forecast.router)
app.include_router(invoices.router)
app.include_router(mandates.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

