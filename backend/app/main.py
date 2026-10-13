from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import forecast, invoices, mandates

if TYPE_CHECKING:
    from openai import OpenAI


@lru_cache(maxsize=1)
def get_openai_client() -> "OpenAI":
    import os

    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="AmanahPay Treasurer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8081"],
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

@app.get("/testing_post")
def payment_request() -> dict[str, str]:
        try:
            import traceback

            from .db import get_treasurer
            from .models import PaymentRequest

            print("Calling treasurer.pay()...")
            payment_request = PaymentRequest(
                mandate_id="mandate-demo",
                supplier="Acme Supplies",
                amount= 1,
                purpose="supplier invoice",
                invoice_id="invoice-123",
            )
            result = get_treasurer().pay(payment_request)
            print("Treasurer.pay() returned:", result)
            print("Calling your Treasurer AI Agent ...")
            response = get_openai_client().chat.completions.create(
                model="gpt-4o-mini",
                messages = [ {"role": "system", "content": "You are a financial assistent."},
                            {"role": "user", "content": f"Payment summary"}],
                max_completion_tokens=1
            )
            print("OpenAI API responded successfully!")
            return {"reply": response.choices[0].message.content}
            # return {
            #     "status": result.status,
            #     "reason": result.reason,
            #     "payment_id": result.payment_id,
            #     "audit_hash": result.audit_hash,
            # }
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}
    
@app.get("/api/test-ai")
def test_ai() -> dict[str, str]:
    try:
        import traceback

        print("Calling OpenAI API...")
        response = get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Reply with a 1"}],
            max_completion_tokens=1
        )
        print("OpenAI API responded successfully!")
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        print("ERROR calling OpenAI:")
        traceback.print_exc()
        return {"error": str(e)}
