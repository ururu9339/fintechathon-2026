from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..db import get_session
from ..models import AgentRequest, AgentResponse

router = APIRouter(prefix="/api", tags=["agent"])

@router.post("/agent", response_model=AgentResponse)
def run_agent(request: AgentRequest, session: Session = Depends(get_session)):
    from ..db import get_treasurer
    return get_treasurer().agent(request.message, session)

@router.get("/audit")
def get_audit():
    from ..db import get_treasurer
    return {"events": get_treasurer().audit.events}