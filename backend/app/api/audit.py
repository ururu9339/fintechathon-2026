from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import get_current_user, require_business_access
from ..db import get_session
from ..models import AuditEvent, User

router = APIRouter(
    prefix="/api/businesses/{business_id}/audit",
    tags=["audit"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
def list_audit_events(
    business_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    require_business_access(business_id, user, session)
    return session.exec(
        select(AuditEvent)
        .where(AuditEvent.business_id == business_id)
        .order_by(AuditEvent.created_at.desc())
    ).all()
