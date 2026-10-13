import os
from decimal import Decimal
import traceback
from urllib import response
from openai import OpenAI

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.models import PaymentRequest

from .api import forecast, invoices, mandates
from .db import treasurer
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

@app.get("/agent")
def agent_test() -> str:
     try:
        print("Calling the agent")
        agent_response = treasurer.agent()
        return agent_response
     except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/testing_post")
def payment_request() -> dict[str, str]:
        try:
            print("Calling treasurer.pay()...")
            payment_request = PaymentRequest(
                mandate_id="mandate-demo",
                supplier="Acme Supplies",
                amount= 1,
                purpose="supplier invoice",
                invoice_id="invoice-123",
            )
            result = treasurer.pay(payment_request)
            print("Treasurer.pay() returned:", result)
            print("Calling your Treasurer AI Agent ...")
            response = client.chat.completions.create(
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
        print("Calling OpenAI API...")
        response = client.chat.completions.create(
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
