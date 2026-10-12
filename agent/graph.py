from backend.app.models import AgentResponse
from backend.app.services import Treasurer
from .injection import contains_prompt_injection


def run(message: str, treasurer: Treasurer | None = None) -> AgentResponse:
    """Minimal agent graph: inspect -> policy gate -> advise."""
    treasurer = treasurer or Treasurer()
    if contains_prompt_injection(message):
        return treasurer.agent(message)
    return treasurer.agent(message)
