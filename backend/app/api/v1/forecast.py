"""Forecasting endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics import forecasting as fc
from app.analytics.filters import Filters
from app.analytics.util import to_native
from app.api.deps import get_current_user, get_filters
from app.core.database import get_db
from app.models import User

router = APIRouter()


@router.get("")
def forecast(metric: str = Query("net_revenue"), horizon: int = Query(3, ge=1, le=12),
             f: Filters = Depends(get_filters), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return to_native(fc.forecast(db, f, metric=metric, horizon=horizon))
