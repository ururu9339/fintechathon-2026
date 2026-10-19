import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..auth import get_current_user, require_business_access
from ..core.llm import get_openai_client
from ..db import get_session
from ..models import AssistantMessage, User
from ..prediction_service import build_forecast

router = APIRouter(
    prefix="/api/businesses/{business_id}/assistant",
    tags=["assistant"],
    dependencies=[Depends(get_current_user)],
)


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AssistantResponse(BaseModel):
    answer: str
    input_kind: str
    status: str


def _context(business_id: str, session: Session) -> dict:
    forecast = build_forecast(business_id, session, 90, persist=False)
    return {
        "forecast": forecast.snapshot,
        "alerts": forecast.snapshot.get("alerts", []),
    }


def _answer(message: str, context: dict) -> tuple[str, str]:
    client = get_openai_client()
    if client is None:
        return (
            "AI assistant is not configured. Review the forecast and open alerts in the dashboard.",
            "needs_review",
        )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a finance assistant. Answer only from the supplied business context. "
                    "Do not invent figures, approve payments, promise financing, or provide legal advice. "
                    "Explain uncertainty and suggest review actions."
                ),
            },
            {"role": "user", "content": f"Context: {context}\nQuestion: {message}"},
        ],
    )
    answer = response.choices[0].message.content
    if not answer:
        return "The assistant returned no answer. Review the dashboard data.", "needs_review"
    return answer.strip(), "ok"


def _run(
    business_id: str,
    text: str,
    input_kind: str,
    user: User,
    session: Session,
) -> AssistantResponse:
    require_business_access(business_id, user, session)
    session.add(AssistantMessage(
        user_id=user.id,
        business_id=business_id,
        direction="user",
        input_kind=input_kind,
        content=text,
    ))
    answer, status = _answer(text, _context(business_id, session))
    session.add(AssistantMessage(
        user_id=user.id,
        business_id=business_id,
        direction="assistant",
        input_kind=input_kind,
        content=answer,
    ))
    session.commit()
    return AssistantResponse(answer=answer, input_kind=input_kind, status=status)


@router.post("/text", response_model=AssistantResponse)
def assistant_text(
    business_id: str,
    request: AssistantRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return _run(business_id, request.message, "text", user, session)


@router.post("/voice", response_model=AssistantResponse)
async def assistant_voice(
    business_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_business_access(business_id, user, session)
    client = get_openai_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Voice transcription is not configured.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Voice file is too large.")
    try:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(file.filename or "voice.webm", content, file.content_type or "audio/webm"),
        )
        text = transcription.text.strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Voice transcription failed.") from exc
    if not text:
        raise HTTPException(status_code=422, detail="Voice message contained no transcribable text.")
    return _run(business_id, text, "voice", user, session)
