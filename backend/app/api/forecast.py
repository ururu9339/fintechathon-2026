from fastapi import APIRouter

from ..db import treasurer

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast")
def get_forecast():
    return {"points": treasurer.forecast(), "currency": "MYR"}


@router.get("/envelopes")
def get_envelopes():
    return {
        "envelopes": [
            {"name": "SST & taxes", "target": 6000, "allocated": 5200},
            {"name": "EPF & salaries", "target": 12000, "allocated": 12000},
            {"name": "Suppliers", "target": 10000, "allocated": 6800},
        ]
    }


@router.get("/financing")
def get_financing():
    return {"recommendations": treasurer.financing()}
