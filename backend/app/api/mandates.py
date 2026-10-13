from fastapi import APIRouter

from ..models import AgentRequest, AgentResponse

router = APIRouter(prefix="/api", tags=["mandates"])


@router.post("/agent", response_model=AgentResponse)
def run_agent(request: AgentRequest):
    from ..db import get_treasurer

    return get_treasurer().agent(request.message)


@router.get("/audit")
def get_audit():
    from ..db import get_treasurer

    return {"events": get_treasurer().audit.events}
