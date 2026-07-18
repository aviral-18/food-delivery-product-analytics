"""Product Decision Lab endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import decision_lab as dl
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User
from app.schemas.analytics import DecisionScenario

router = APIRouter()


@router.get("/levers")
def levers(_: User = Depends(get_current_user)):
    return {"levers": dl.available_levers()}


@router.post("/simulate")
def simulate(scenario: DecisionScenario, f: Filters = Depends(get_filters),
             db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    levers = [lever.model_dump() for lever in scenario.levers]
    return to_native(dl.simulate(db, f, levers))
