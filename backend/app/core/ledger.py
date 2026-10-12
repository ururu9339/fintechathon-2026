from ..services import AuditChain


def append_event(audit: AuditChain, event_type: str, payload: dict):
    return audit.append(event_type, payload)
