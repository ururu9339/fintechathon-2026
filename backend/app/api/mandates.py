from fastapi import APIRouter

from ..db import treasurer
from ..models import AgentRequest, AgentResponse

router = APIRouter(prefix="/api", tags=["mandates"])


@router.post("/agent", response_model=AgentResponse)
def run_agent(request: AgentRequest):
    return treasurer.agent(request.message)


@router.get("/audit")
def get_audit():
    return {"events": treasurer.audit.events}
