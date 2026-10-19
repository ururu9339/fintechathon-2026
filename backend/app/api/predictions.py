from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import get_current_user, require_business_access
from ..db import get_session
from ..models import (
    ForecastSnapshot,
    User,
)
from ..prediction_service import build_forecast

router = APIRouter(
    prefix="/api/businesses/{business_id}/predictions",
    tags=["predictions"],
    dependencies=[Depends(get_current_user)],
)


def _access(business_id: str, user: User, session: Session) -> None:
    require_business_access(business_id, user, session)


@router.post("/forecast", response_model=ForecastSnapshot)
def create_forecast(
    business_id: str,
    horizon_days: int = 90,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _access(business_id, user, session)
    try:
        snapshot = build_forecast(business_id, session, horizon_days, persist=True)
        return snapshot
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/forecasts", response_model=list[ForecastSnapshot])
def list_forecasts(
    business_id: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _access(business_id, user, session)
    return session.exec(select(ForecastSnapshot).where(
        ForecastSnapshot.business_id == business_id
    ).order_by(ForecastSnapshot.created_at.desc())).all()
